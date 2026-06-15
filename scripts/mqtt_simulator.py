#!/usr/bin/env python3
"""
MQTT Simulator - Simulates a Raspberry Pi publishing drowsiness detection data.

Usage:
    python3 scripts/mqtt_simulator.py
    python3 scripts/mqtt_simulator.py --broker localhost --port 1883 --interval 5

Requires: pip install paho-mqtt
"""

import argparse
import json
import random
import time
import uuid

import paho.mqtt.client as mqtt


def parse_args():
    parser = argparse.ArgumentParser(description="MQTT Drowsiness Detector Simulator")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--device-id", default=None, help="Device UUID (auto-generated if omitted)")
    parser.add_argument("--interval", type=int, default=10, help="Seconds between messages")
    parser.add_argument("--alert-chance", type=float, default=0.3, help="Probability of alert per cycle (0-1)")
    parser.add_argument("--prefix", default="somnolence", help="MQTT topic prefix")
    return parser.parse_args()


def generate_environmental():
    """Generate realistic environmental sensor readings."""
    return {
        "temperature": round(random.uniform(18.0, 38.0), 1),
        "humidity": round(random.uniform(25.0, 85.0), 1),
        "co2": round(random.uniform(350.0, 1200.0), 0),
    }


def generate_alert():
    """Generate a random drowsiness alert."""
    alert_configs = {
        "EYE_CLOSURE": {"value_range": (0.10, 0.20), "threshold": 0.21},
        "YAWN": {"value_range": (0.6, 0.95), "threshold": 0.55},
        "HEAD_NOD": {"value_range": (15.0, 45.0), "threshold": 12.0},
        "PHONE_USE": {"value_range": (0.03, 0.14), "threshold": 0.15},
    }

    alert_type = random.choice(list(alert_configs.keys()))
    config = alert_configs[alert_type]
    value = round(random.uniform(*config["value_range"]), 2)

    severity_weights = {"LOW": 0.4, "MEDIUM": 0.35, "HIGH": 0.25}
    severity = random.choices(
        list(severity_weights.keys()),
        weights=list(severity_weights.values()),
    )[0]

    return {
        "alert_type": alert_type,
        "severity": severity,
        "value": value,
        "threshold": config["threshold"],
    }


def on_connect(client, userdata, connect_flags, reason_code, properties):
    print(f"Connected to broker: {reason_code}")


def main():
    args = parse_args()
    device_id = args.device_id or str(uuid.uuid4())

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.connect(args.broker, args.port)
    client.loop_start()

    prefix = args.prefix

    print(f"Simulator started")
    print(f"  Device ID: {device_id}")
    print(f"  Broker:    {args.broker}:{args.port}")
    print(f"  Interval:  {args.interval}s")
    print(f"  Topics:    {prefix}/{device_id}/...")
    print(f"  Alert chance: {args.alert_chance * 100:.0f}%")
    print()

    cycle = 0
    try:
        while True:
            cycle += 1

            # Environmental reading every cycle
            env = generate_environmental()
            client.publish(
                f"{prefix}/{device_id}/environmental",
                json.dumps(env),
                qos=1,
            )
            print(
                f"[{cycle}] Environmental: "
                f"temp={env['temperature']}C "
                f"hum={env['humidity']}% "
                f"co2={env['co2']}ppm"
            )

            # Alert with configured probability
            if random.random() < args.alert_chance:
                alert = generate_alert()
                client.publish(
                    f"{prefix}/{device_id}/alerts",
                    json.dumps(alert),
                    qos=1,
                )
                print(
                    f"[{cycle}] ALERT: {alert['alert_type']} "
                    f"severity={alert['severity']} "
                    f"value={alert['value']}"
                )

            # Status heartbeat every cycle
            client.publish(
                f"{prefix}/{device_id}/status",
                json.dumps({"status": "online"}),
                qos=1,
            )

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopping simulator...")
    finally:
        client.loop_stop()
        client.disconnect()
        print("Simulator stopped.")


if __name__ == "__main__":
    main()
