from datetime import datetime

import pika
import json
import requests
import os
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password123')
QUEUE_NAME = 'market_ticks'

BACKEND_TRIGGER_URL = os.getenv('BACKEND_TRIGGER_URL', 'http://backend-api:8000/api/v1/schedules/trigger')
AI_SCOPE_ID = os.getenv('AI_SCOPE_ID', "00000000-0000-0000-0000-000000000000")

price_history = []
ALERT_THRESHOLD = 2000.00 

def trigger_deep_analysis(ticker, price, event_type):
    payload = {
        "event_trigger_source": f"STREAMING_FAST_LANE_{event_type}",
        "override_args": {
            # โยนข้อมูลสดๆ จาก Stream เข้าไปเป็น Parameter ให้ Airflow และ Spark ใช้
            "ticker": ticker,
            "trigger_price": price,
            "event_type": event_type,
            "detected_at": datetime.utcnow().isoformat(),
            # สามารถโยน Path ของไฟล์ชั่วคราวให้ Spark ไปอ่านต่อได้เลย
            # "custom_input_path": "s3a://raw-data/stream-dumps/..."
        }
    }
    try:
        logging.info(f"⚡ Firing API Trigger to Backend for Scope {AI_SCOPE_ID}...")
        response = requests.post(f"{BACKEND_TRIGGER_URL}/{AI_SCOPE_ID}", json=payload)
        
        if response.status_code in (200, 201):
            logging.info(f"✅ Triggered Deep Analyzer DAG! Response: {response.json()}")
        else:
            logging.error(f"❌ Trigger failed. Code: {response.status_code}")
    except Exception as e:
        logging.error(f"❌ Backend unreachable: {e}")

def analyze_fast_lane(ticker, current_price, timestamp):
    global price_history
    price_history.append(current_price)
    
    if len(price_history) > 100:
        price_history.pop(0)

    logging.info(f"[{ticker}] Current Price: {current_price}")

    if current_price >= ALERT_THRESHOLD:
        logging.warning(f"🚨 BREAKOUT DETECTED for {ticker} at {current_price}!")
        trigger_deep_analysis(ticker, current_price, "BREAKOUT_RESISTANCE")
        price_history.clear()

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        analyze_fast_lane(data.get('ticker'), data.get('price'), data.get('timestamp'))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def start_worker():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(RABBITMQ_HOST, 5672, '/', credentials)
    
    while True:
        try:
            connection = pika.BlockingConnection(parameters)
            break
        except Exception:
            logging.info("⏳ Waiting for RabbitMQ to be ready...")
            time.sleep(5)
            
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    logging.info(f"🎧 Streaming Worker started. Listening for '{QUEUE_NAME}' events...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logging.info("🛑 Worker stopped.")
    finally:
        connection.close()

if __name__ == '__main__':
    start_worker()