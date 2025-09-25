# app.py
import sqlite3
import json
import time
from flask import Flask, jsonify, render_template, request
import threading
import paho.mqtt.client as mqtt
from flask_cors import CORS

DB_FILE = "data.db"
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "smartplant/device1"

app = Flask(__name__)
CORS(app)  # allow cross-origin if needed

latest_reading = {}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            temperature REAL,
            moisture REAL,
            light REAL
        )
    ''')
    conn.commit()
    conn.close()

def insert_reading(ts, temperature, moisture, light):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO readings (timestamp, temperature, moisture, light)
        VALUES (?, ?, ?, ?)
    ''', (ts, temperature, moisture, light))
    conn.commit()
    conn.close()

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker (rc=%s)" % rc)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global latest_reading
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        ts = data.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S")
        temperature = float(data.get("temperature", 0.0))
        moisture = float(data.get("moisture", 0.0))
        light = float(data.get("light", 0.0))

        # Save to DB
        insert_reading(ts, temperature, moisture, light)

        # Update latest
        latest_reading = {
            "timestamp": ts,
            "temperature": temperature,
            "moisture": moisture,
            "light": light
        }
        print("Saved:", latest_reading)
    except Exception as e:
        print("Failed to process MQTT message:", e)

def start_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_start()
    return client

# Flask routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/latest")
def api_latest():
    if latest_reading:
        return jsonify({"status": "ok", "data": latest_reading})
    else:
        # fallback: get latest from DB
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT timestamp, temperature, moisture, light FROM readings ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if row:
            ts, temperature, moisture, light = row
            return jsonify({"status": "ok", "data": {"timestamp": ts, "temperature": temperature, "moisture": moisture, "light": light}})
        else:
            return jsonify({"status": "empty", "data": {}})

@app.route("/api/history")
def api_history():
    # optional query param: ?limit=100
    limit = int(request.args.get("limit", 100))
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT timestamp, temperature, moisture, light FROM readings ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    # rows are newest->oldest; reverse to oldest->newest
    rows.reverse()
    data = [{"timestamp": r[0], "temperature": r[1], "moisture": r[2], "light": r[3]} for r in rows]
    return jsonify({"status": "ok", "data": data})

if __name__ == "__main__":
    init_db()
    mqtt_client = start_mqtt()
    # Run Flask without the reloader to avoid duplicate MQTT threads
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    # when app stops:
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
