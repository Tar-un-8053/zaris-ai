"""
MQTT Client for Smart Home Hub
Sync implementation using paho-mqtt ( no asyncio required)
"""
import json
import os
import threading
import time
from typing import Callable, Dict, Optional


class MQTTClient:
    """Thread-safe MQTT client for local device communication"""
    
    def __init__(
        self,
        broker: str = None,
        port: int = None,
        client_id: str = None,
        keepalive: int = 60
    ):
        self.broker = broker or os.getenv("ZARIS_MQTT_BROKER", "localhost")
        self.port = port or int(os.getenv("ZARIS_MQTT_PORT", "1883"))
        self.client_id = client_id or f"zaris-hub-{int(time.time())}"
        self.keepalive = keepalive
        self.reconnect_delay = 5
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
        self._client = None
        self._connected = False
        self._subscriptions: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._reconnect_thread = None
        self._running = False
        
    def connect(self) -> bool:
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            print("[MQTT] paho-mqtt not installed. Run: pip install paho-mqtt")
            return False
        
        with self._lock:
            if self._connected:
                return True
            
            try:
                self._client = mqtt.Client(client_id=self.client_id)
                self._client.on_connect = self._on_connect
                self._client.on_disconnect = self._on_disconnect
                self._client.on_message = self._on_message
                
                self._client.connect(self.broker, self.port, self.keepalive)
                self._client.loop_start()
                self._running = True
                
                timeout = 5
                start = time.time()
                while not self._connected and (time.time() - start) < timeout:
                    time.sleep(0.1)
                
                return self._connected
                
            except Exception as e:
                print(f"[MQTT] Connection error: {e}")
                return False
    
    def disconnect(self) -> bool:
        with self._lock:
            self._running = False
            if self._client:
                try:
                    self._client.loop_stop()
                    self._client.disconnect()
                except:
                    pass
                self._client = None
            self._connected = False
            print("[MQTT] Disconnected")
            return True
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            self.reconnect_attempts = 0
            print(f"[MQTT] Connected to {self.broker}:{self.port}")
            
            for topic in self._subscriptions:
                try:
                    client.subscribe(topic)
                    print(f"[MQTT] Resubscribed to: {topic}")
                except Exception as e:
                    print(f"[MQTT] Resubscribe error: {e}")
        else:
            print(f"[MQTT] Connection failed with code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        print(f"[MQTT] Disconnected (rc: {rc})")
        
        if self._running and self.reconnect_attempts < self.max_reconnect_attempts:
            self._schedule_reconnect()
    
    def _schedule_reconnect(self):
        self.reconnect_attempts += 1
        delay = min(self.reconnect_delay * self.reconnect_attempts, 60)
        print(f"[MQTT] Reconnecting in {delay}s (attempt {self.reconnect_attempts})")
        
        def _reconnect():
            time.sleep(delay)
            if self._running and not self._connected:
                self.connect()
        
        if self._reconnect_thread is None or not self._reconnect_thread.is_alive():
            self._reconnect_thread = threading.Thread(target=_reconnect, daemon=True)
            self._reconnect_thread.start()
    
    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            topic = msg.topic
            
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                data = {"raw": payload}
            
            if topic in self._subscriptions:
                try:
                    self._subscriptions[topic](topic, data)
                except Exception as e:
                    print(f"[MQTT] Handler error for {topic}: {e}")
            
            for pattern, handler in self._subscriptions.items():
                if pattern.endswith('#') or pattern.endswith('+'):
                    if self._topic_matches(topic, pattern):
                        try:
                            handler(topic, data)
                        except Exception as e:
                            print(f"[MQTT] Handler error for {pattern}: {e}")
                            
        except Exception as e:
            print(f"[MQTT] Message handling error: {e}")
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        for i, p in enumerate(pattern_parts):
            if p == '#':
                return True
            if i >= len(topic_parts):
                return False
            if p != '+' and p != topic_parts[i]:
                return False
        return len(topic_parts) == len(pattern_parts)
    
    def publish(self, topic: str, payload: dict, retain: bool = False, qos: int = 0) -> bool:
        if not self._connected or not self._client:
            print(f"[MQTT] Cannot publish - not connected")
            return False
        
        try:
            message = json.dumps(payload)
            info = self._client.publish(topic, message, qos=qos, retain=retain)
            return info.rc == 0
        except Exception as e:
            print(f"[MQTT] Publish error: {e}")
            return False
    
    def subscribe(self, topic: str, handler: Callable[[str, dict], None]) -> bool:
        self._subscriptions[topic] = handler
        
        if self._connected and self._client:
            try:
                self._client.subscribe(topic)
                print(f"[MQTT] Subscribed to: {topic}")
                return True
            except Exception as e:
                print(f"[MQTT] Subscribe error: {e}")
                return False
        return True
    
    def unsubscribe(self, topic: str) -> bool:
        if topic in self._subscriptions:
            del self._subscriptions[topic]
        
        if self._connected and self._client:
            try:
                self._client.unsubscribe(topic)
                print(f"[MQTT] Unsubscribed from: {topic}")
            except:
                pass
        return True
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def get_status(self) -> dict:
        return {
            "connected": self._connected,
            "broker": self.broker,
            "port": self.port,
            "client_id": self.client_id,
            "subscriptions": list(self._subscriptions.keys()),
            "reconnect_attempts": self.reconnect_attempts
        }


_mqtt_client_instance: Optional[MQTTClient] = None


def get_mqtt_client() -> MQTTClient:
    global _mqtt_client_instance
    if _mqtt_client_instance is None:
        _mqtt_client_instance = MQTTClient()
    return _mqtt_client_instance
