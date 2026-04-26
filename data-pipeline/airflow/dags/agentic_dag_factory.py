from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from datetime import datetime
import json
import os
import boto3
import tempfile
import subprocess
import logging
from urllib.parse import urlparse
from croniter import croniter

# ==========================================
# 1. ฟังก์ชันโหลดไฟล์ JSON (หลีกเลี่ยงการต่อ DB ตรงๆ)
# ==========================================
CONFIG_PATH = os.getenv("AIRFLOW_DAGS_CONFIG_DIR", "/opt/airflow/config") + "/schedules.json"
CONFIG_FILE = os.path.join(CONFIG_PATH)

class MinIOSparkSubmitOperator(SparkSubmitOperator):
    def execute(self, context):
        # รองรับทั้งเวอร์ชันเก่าและใหม่ของ Airflow
        script_url = getattr(self, 'application', getattr(self, '_application', ''))
        
        parsed_url = urlparse(script_url.replace("s3a://", "http://"))
        bucket_name = parsed_url.netloc
        object_key = parsed_url.path.lstrip('/')
        
        s3_client = boto3.client(
            's3',
            endpoint_url=os.getenv('MINIO_ENDPOINT', 'http://minio:9000'),
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'admin'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'password123'),
            region_name='us-east-1'
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            script_filename = os.path.basename(object_key)
            local_script_path = os.path.join(tmpdir, script_filename)
            
            self.log.info(f"📥 Downloading Spark script from {script_url} to {local_script_path}")
            s3_client.download_file(bucket_name, object_key, local_script_path)
            
            # 💡 เขียนทับตัวแปรทั้งสองแบบ เพื่อบังคับให้ Hook มองเห็นไฟล์ Local
            self.application = local_script_path
            self._application = local_script_path
            
            self.log.info("🚀 Executing spark-submit...")
            return super().execute(context)

def load_schedules_from_json():
    if not os.path.exists(CONFIG_FILE):
        return []
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to read schedules.json: {e}")
        return []

# ==========================================
# 2. Generic Executor สำหรับ Python/Go Tools
# ==========================================
def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=os.getenv('MINIO_ENDPOINT', 'http://minio:9000'),
        aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'admin'),
        aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'password123'),
        region_name='us-east-1'
    )

def generic_python_executor(**kwargs):
    task_config = kwargs['task_config']
    
    # รองรับ Runtime Override กรณีถูกเรียกผ่าน API /trigger
    dag_run_conf = kwargs.get('dag_run').conf if kwargs.get('dag_run') and kwargs.get('dag_run').conf else {}
    runtime_overrides = dag_run_conf.get('runtime_overrides', {})
    
    script_url = task_config['script_url']
    args_dict = task_config.get('arguments', {})
    args_dict.update(runtime_overrides)
    
    parsed_url = urlparse(script_url.replace("s3a://", "http://"))
    bucket_name = parsed_url.netloc
    object_key = parsed_url.path.lstrip('/')
    
    schedule_id = kwargs.get('dag_run').run_id if kwargs.get('dag_run') else 'manual'
    task_id = task_config.get('task_id', 'unknown_task')
    output_path = f"s3a://processed-data/task_outputs/run={schedule_id}/task={task_id}/"
    
    if 'output_path' not in args_dict:
        args_dict['output_path'] = output_path

    s3_client = get_s3_client()

    with tempfile.TemporaryDirectory() as tmpdir:
        script_filename = os.path.basename(object_key)
        local_script_path = os.path.join(tmpdir, script_filename)
        
        logging.info(f"📥 Downloading: {bucket_name}/{object_key}")
        s3_client.download_file(bucket_name, object_key, local_script_path)

        if script_filename.endswith('.py'):
            cmd = ["python3", local_script_path]
        elif script_filename.endswith('.go'):
            os.chmod(local_script_path, 0o755)
            cmd = [local_script_path]
        else:
            cmd = ["python3", local_script_path]
        
        for k, v in args_dict.items():
            cmd.extend([f"--{k}", str(v)])

        logging.info(f"▶️ Running: {' '.join(cmd)}")
        process = subprocess.run(cmd, capture_output=True, text=True)

        if process.returncode != 0:
            raise Exception(f"Task Failed! Error: {process.stderr}")
            
        logging.info(f"✅ Success: {process.stdout}")

    return {"output_path": output_path, "status": "success"}

# ==========================================
# 3. DAG Factory (สร้าง DAG อัตโนมัติตาม JSON)
# ==========================================
schedules = load_schedules_from_json()

for sch in schedules:
    cron_expr = sch.get('cron')
    
    # 💡 เพิ่มระบบป้องกัน: ตรวจสอบว่ารูปแบบ CRON ถูกต้องหรือไม่
    # ถ้าพิมพ์มาผิด ให้ข้าม (continue) ไปสร้าง DAG ตัวถัดไปเลย ระบบจะได้ไม่พัง
    if cron_expr and not croniter.is_valid(cron_expr):
        logging.error(f"❌ ข้ามการสร้าง DAG: รูปแบบ CRON '{cron_expr}' ไม่ถูกต้อง สำหรับ Schedule {sch['schedule_id']}")
        continue

    # ถ้าถูกต้อง ก็สร้าง DAG ตามปกติ
    dag_id = f"dynamic_scope_{sch['scope_id'][:8]}_sch_{sch['schedule_id'][:8]}"
    
    dag = DAG(
        dag_id=dag_id,
        schedule=cron_expr, 
        start_date=datetime(2024, 1, 1),
        catchup=False,
        is_paused_upon_creation=False,
        tags=['dynamic', f"scope_{sch['scope_id'][:8]}"]
    )

    with dag:
        operator_dict = {}
        
        # 💡 1. สร้าง Map สำหรับแปลง task_id ของ DB ให้เป็น task_id ของ Airflow
        task_mapping = {t['task_id']: f"{t['task_type'].lower()}_{t['task_id'][:8]}" for t in sch.get('tasks', [])}
        
        # 3.1 สร้าง Operator ให้ครบทุก Task
        for task in sch.get('tasks', []):
            t_id = task_mapping[task['task_id']]
            
            if task['task_type'] in ['SEARCH', 'TRADITIONAL_LOGIC', 'AI_INFERENCE', 'VISUALIZE']:
                operator = PythonOperator(
                    task_id=t_id,
                    python_callable=generic_python_executor,
                    op_kwargs={'task_config': task},
                )
            
            elif task['task_type'] == 'ETL':
                dep_id = task.get('depends_on_task_id')
                if dep_id and dep_id in task_mapping:
                    parent_airflow_id = task_mapping[dep_id]
                    dynamic_input_path = f"{{{{ ti.xcom_pull(task_ids='{parent_airflow_id}')['output_path'] }}}}"
                else:
                    dynamic_input_path = task['arguments'].get('custom_input_path', 'default_path')

                spark_args = [
                    '--input_path', dynamic_input_path,
                    '--scope_id', sch['scope_id'],
                    '--schedule_id', sch['schedule_id'],
                ]
                
                operator = MinIOSparkSubmitOperator(
                    task_id=t_id,
                    application=task['script_url'],
                    conn_id='spark_default',
                    application_args=spark_args,
                    # packages='org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.6.0'
                    jars='/opt/airflow/jars/hadoop-aws-3.4.1.jar,/opt/airflow/jars/bundle-2.25.4.jar,/opt/airflow/jars/postgresql-42.6.0.jar'
                )
            
            
            # เก็บเข้า Dictionary ไว้โยงเส้นทีหลัง
            operator_dict[task['task_id']] = (t_id, operator)

        # 3.2 โยงเส้นความสัมพันธ์ (Dependencies A >> B)
        for task in sch.get('tasks', []):
            dep_task_id = task.get('depends_on_task_id')
            
            if dep_task_id and dep_task_id in operator_dict:
                parent_op = operator_dict[dep_task_id][1]
                child_op = operator_dict[task['task_id']][1]
                
                # โยงเส้น!
                parent_op >> child_op

    # 4. ยัด DAG ที่สมบูรณ์แล้วลงใน Global Namespace เพื่อให้ Airflow ตรวจเจอ
    globals()[dag_id] = dag