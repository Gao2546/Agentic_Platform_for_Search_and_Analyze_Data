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
import sys
from urllib.parse import urlparse
from croniter import croniter


def load_requirements_file(requirements_path='/requirements.txt'):
    if not os.path.exists(requirements_path):
        return []

    requirements = []
    try:
        with open(requirements_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                requirements.append(line)
    except Exception as e:
        logging.warning(f"Failed to load requirements from {requirements_path}: {e}")

    return requirements


# ==========================================
# 1. Custom Spark Operator (Inject Dependencies)
# ==========================================
class MinIOSparkSubmitOperator(SparkSubmitOperator):
    def __init__(self, dependencies=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dependencies = dependencies or {}

    def execute(self, context):
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
            
            self.log.info(f"📥 Downloading Spark script from {script_url}")
            s3_client.download_file(bucket_name, object_key, local_script_path)
            
            # 💡 [SPARK INJECTION] ถ้ามี Dependencies ให้แทรกโค้ดติดตั้งไว้บนสุดของไฟล์
            if self.dependencies and script_filename.endswith('.py'):
                self.log.info(f"📦 Injecting dependencies install block for: {list(self.dependencies.values())}")
                
                install_block = "import subprocess, sys\n"
                for _, pip_name in self.dependencies.items():
                    install_block += f"subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', '{pip_name}'])\n"
                
                # Load and install packages from requirements.txt
                requirements = load_requirements_file()
                for pkg in requirements:
                    install_block += f"subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', '{pkg}'])\n"
                
                install_block += "\n# --- Original Script Below ---\n"

                with open(local_script_path, 'r') as original:
                    data = original.read()
                with open(local_script_path, 'w') as modified:
                    modified.write(install_block + data)

            self.application = local_script_path
            self._application = local_script_path
            
            self.log.info("🚀 Executing spark-submit...")
            return super().execute(context)

# ==========================================
# 2. Generic Python Executor (Temporary Virtualenv)
# ==========================================
def generic_python_executor(**kwargs):
    task_config = kwargs['task_config']
    
    dag_run_conf = kwargs.get('dag_run').conf if kwargs.get('dag_run') and kwargs.get('dag_run').conf else {}
    runtime_overrides = dag_run_conf.get('runtime_overrides', {})
    
    script_url = task_config['script_url']
    args_dict = task_config.get('arguments', {})
    args_dict.update(runtime_overrides)
    dependencies = task_config.get('dependencies', {}) # 👈 ดึง Dependencies มา
    
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
        
        logging.info(f"📥 Downloading: {bucket_name}/{object_key}")
        s3_client.download_file(bucket_name, object_key, local_script_path)

        if script_filename.endswith('.py'):
            # 💡 [VIRTUALENV STRATEGY] สร้าง venv ชั่วคราว
            
            venv_dir = os.path.join(tmpdir, "venv")
            python_exe = os.path.join(venv_dir, "bin", "python") if os.name != 'nt' else os.path.join(venv_dir, "Scripts", "python.exe")
            pip_exe = os.path.join(venv_dir, "bin", "pip") if os.name != 'nt' else os.path.join(venv_dir, "Scripts", "pip.exe")
            
            logging.info(f"🛠️ Creating isolated virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
            
            logging.info("loading requirements for virtualenv...")
            requirements = load_requirements_file()
            logging.info(f"Found requirements: {requirements}")
            packages = []

            if dependencies:
                packages.extend(dependencies.values())

            for pkg in requirements:
                if pkg not in packages:
                    packages.append(pkg)

            if packages:
                logging.info(f"📦 Installing dependencies in venv: {packages}")
                subprocess.run([pip_exe, "install", "-q", "--default-timeout=3600"] + packages, check=True)

            cmd = [python_exe, local_script_path]
            
        elif script_filename.endswith('.go'):
            os.chmod(local_script_path, 0o755)
            cmd = [local_script_path]
        else:
            cmd = ["python3", local_script_path]
        
        for k, v in args_dict.items():
            cmd.extend([f"--{k}", str(v)])

        logging.info(f"▶️ Running isolated task: {' '.join(cmd)}")
        process = subprocess.run(cmd, capture_output=True, text=True)

        if process.returncode != 0:
            raise Exception(f"Task Failed! Error: {process.stderr}")
            
        logging.info(f"✅ Success: {process.stdout}")

    return {"status": "success"}

# ==========================================
# 3. DAG Factory (ปรับแก้การเรียก Operator)
# ==========================================
CONFIG_PATH = os.getenv("AIRFLOW_DAGS_CONFIG_DIR", "/opt/airflow/config") + "/schedules.json"

def load_schedules_from_json():
    if not os.path.exists(CONFIG_PATH):
        return []
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to read schedules.json: {e}")
        return []

schedules = load_schedules_from_json()

for sch in schedules:
    cron_expr = sch.get('cron')
    
    if cron_expr and not croniter.is_valid(cron_expr):
        logging.error(f"❌ ข้ามการสร้าง DAG: รูปแบบ CRON '{cron_expr}' ไม่ถูกต้อง")
        continue

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
        task_mapping = {t['task_id']: f"{t['task_type'].lower()}_{t['task_id'][:8]}" for t in sch.get('tasks', [])}
        
        for task in sch.get('tasks', []):
            t_id = task_mapping[task['task_id']]
            
            if 'arguments' not in task or not isinstance(task['arguments'], dict):
                task['arguments'] = {}
                
            task['arguments'].setdefault('scope_id', sch.get('scope_id', 'unknown_scope'))
            task['arguments'].setdefault('schedule_id', sch.get('schedule_id', 'unknown_schedule'))
            task['arguments'].setdefault('task_id', task.get('task_id', 'unknown_task'))
            
            # ----------------------------------------------------
            
            if task['task_type'] in ['SEARCH', 'TRADITIONAL_LOGIC', 'AI_INFERENCE']:
                operator = PythonOperator(
                    task_id=t_id,
                    python_callable=generic_python_executor,
                    op_kwargs={'task_config': task},
                )
            
            elif task['task_type'] in ['ETL', 'VISUALIZE']:
                spark_args = [
                    '--scope_id', str(task['arguments']['scope_id']),
                    '--schedule_id', str(task['arguments']['schedule_id']),
                    '--task_id', str(task['arguments']['task_id'])
                ]

                for k, v in task['arguments'].items():
                    if k not in ['scope_id', 'schedule_id', 'task_id', 'custom_input_path']:
                        spark_args.extend([f"--{k}", str(v)])
                
                operator = MinIOSparkSubmitOperator(
                    task_id=t_id,
                    application=task['script_url'],
                    dependencies=task.get('dependencies', {}), # 👈 โยน dependencies เข้า Operator
                    conn_id='spark_default',
                    application_args=spark_args,
                    jars='/opt/airflow/jars/hadoop-aws-3.4.1.jar,/opt/airflow/jars/bundle-2.25.4.jar,/opt/airflow/jars/postgresql-42.6.0.jar'
                )
            
            operator_dict[task['task_id']] = (t_id, operator)

        for task in sch.get('tasks', []):
            dep_task_id = task.get('depends_on_task_id')
            if dep_task_id and dep_task_id in operator_dict:
                operator_dict[dep_task_id][1] >> operator_dict[task['task_id']][1]

    globals()[dag_id] = dag