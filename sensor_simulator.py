# sensor_simulator.py
import time
import json
import random
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"   # public test broker (no auth) - fine for learning
PORT = 1883
TOPIC = "smartplant/device1"

def generate_reading():
    reading = {
        "temperature": round(random.uniform(20.0, 35.0), 2),  # °C
        "moisture": round(random.uniform(20.0, 80.0), 2),     # 0-100 %
        "light": round(random.uniform(100, 1000), 1)          # lux
    }
    return reading

def main():
    client = mqtt.Client()
    client.connect(BROKER, PORT, 60)
    client.loop_start()
    try:
        while True:
            payload = generate_reading()
            payload["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
            msg = json.dumps(payload)
            client.publish(TOPIC, msg)
            print("Published:", msg)
            time.sleep(5)  # publish every 5 seconds
    except KeyboardInterrupt:
        print("Stopping simulator...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()