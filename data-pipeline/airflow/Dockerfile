# Use your exact base image
FROM apache/airflow:3.1.2

USER root
RUN apt-get update \
  # 📌 เพิ่ม wget เข้าไปในบรรทัดนี้ เพื่อให้ดาวน์โหลดไฟล์ได้
  && apt-get install -y --no-install-recommends default-jre procps wget \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/default-java

# 📌 สร้างโฟลเดอร์สำหรับเก็บไฟล์ JAR และยกสิทธิ์ให้ user airflow
RUN mkdir -p /opt/airflow/jars && chown -R airflow: /opt/airflow/jars

# The Airflow image runs as the 'airflow' user by default.
USER airflow

# 📌 ดาวน์โหลด JAR files ทั้ง 3 ตัวมาเก็บไว้ใน Image ถาวร
RUN wget https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.4.1/hadoop-aws-3.4.1.jar -P /opt/airflow/jars/ && \
    wget https://repo1.maven.org/maven2/software/amazon/awssdk/bundle/2.25.4/bundle-2.25.4.jar -P /opt/airflow/jars/ && \
    wget https://repo1.maven.org/maven2/org/postgresql/postgresql/42.6.0/postgresql-42.6.0.jar -P /opt/airflow/jars/

# Copy the requirements file into the container
COPY data-pipeline/airflow/requirements.txt /requirements.txt

# Install the Python libraries before the container runs its main command
RUN pip install --user --no-cache-dir -r /requirements.txt