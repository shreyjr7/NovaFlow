import paho.mqtt.client as mqtt
import json
import os
import time
from pathlib import Path
from .event import Event

class EventCommunicator:
    def __init__(self, config):
        self.broker = config.get('mqtt', {}).get('host', 'broker')
        self.port = config.get('mqtt', {}).get('port', 1883)
        self.tls = config.get('mqtt', {}).get('tls', False)
        self.client = mqtt.Client()
        if self.tls:
            self.client.tls_set()
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        # Local store for store‑and‑forward
        self.store_dir = Path('store')
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def send_event(self, event: Event):
        payload = json.dumps(event.to_dict())
        # Publish to topic "events"
        result = self.client.publish('events', payload)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            # Store locally for later forwarding
            timestamp = int(time.time())
            fname = self.store_dir / f"event_{timestamp}.json"
            with open(fname, 'w') as f:
                f.write(payload)
        # If clip_path is provided, upload to MinIO via HTTPS (placeholder)
        if event.clip_path:
            # In production, implement MinIO client upload here.
            pass
