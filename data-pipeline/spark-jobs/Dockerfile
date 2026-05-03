FROM apache/spark:4.0.2

USER root

# 1. ติดตั้ง Python 3.12 
RUN apt-get update && \
    apt-get install -y software-properties-common wget && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.12 && \
    apt-get clean

# 2. 📌 ท่าไม้ตายสุดยอด: บังคับให้คำสั่ง python และ python3 ชี้ไปที่ python3.12 ของเราเสมอ!
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 100 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.12 100

# 3. ติดตั้ง pip
RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python3 get-pip.py && \
    rm get-pip.py

# 4. ติดตั้ง Libraries (🔥 อัปเกรด pyspark เป็น 4.0.2 ให้ตรงกับ Base Image)
RUN python3 -m pip install --no-cache-dir \
    pymongo \
    psycopg2-binary \
    asyncpg \
    pyspark==4.0.2 \
    pillow \
    boto3 \
    opencv-python

# 1. ก๊อปปี้และติดตั้ง Shared Library (utils)
COPY utils /app/utils
RUN pip install -e /app/utils

# 5. ดาวน์โหลด JAR files ที่จำเป็น 
# (หมายเหตุ: Spark 4.0.x ถูกคอมไพล์มาพร้อม Hadoop 3.4.x ดังนั้นใช้ hadoop-aws-3.4.1.jar ตัวนี้ได้เลย ถูกต้องแล้วครับ)
RUN wget https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.4.1/hadoop-aws-3.4.1.jar -P /opt/spark/jars/ && \
    wget https://repo1.maven.org/maven2/software/amazon/awssdk/bundle/2.25.4/bundle-2.25.4.jar -P /opt/spark/jars/ && \
    wget https://repo1.maven.org/maven2/org/postgresql/postgresql/42.6.0/postgresql-42.6.0.jar -P /opt/spark/jars/

# 6. คอนเฟิร์มให้ PySpark สื่อสารกันด้วยตัวแปรที่ถูกต้อง
ENV PYSPARK_PYTHON=/usr/bin/python3
ENV PYSPARK_DRIVER_PYTHON=/usr/bin/python3

USER spark