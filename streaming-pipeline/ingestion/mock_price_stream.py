import pika
import json
import time
import random
import os

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password123')
QUEUE_NAME = 'market_ticks'

def start_stream():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(RABBITMQ_HOST, 5672, '/', credentials)
    
    # วนลูปเชื่อมต่อจนกว่า RabbitMQ จะพร้อมทำงาน
    while True:
        try:
            connection = pika.BlockingConnection(parameters)
            break
        except Exception:
            print("⏳ Waiting for RabbitMQ to be ready...")
            time.sleep(5)
            
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    print("📈 Starting Market Data Stream (XAU/USD)...")
    current_price = 1995.00 

    try:
        while True:
            change = random.uniform(-2.5, 3.5) 
            current_price = round(current_price + change, 2)

            tick_data = {
                "ticker": "XAU/USD",
                "price": current_price,
                "timestamp": time.time()
            }

            channel.basic_publish(
                exchange='',
                routing_key=QUEUE_NAME,
                body=json.dumps(tick_data),
                properties=pika.BasicProperties(delivery_mode=2) # Persist ลง Disk
            )
            
            print(f"📡 Published: {tick_data}")
            time.sleep(60*60)

    except KeyboardInterrupt:
        print("🛑 Stream stopped.")
    finally:
        connection.close()

if __name__ == '__main__':
    start_stream()