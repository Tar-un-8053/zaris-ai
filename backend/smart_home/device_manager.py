"""
Device Manager for Smart Home Hub
Unified device registry and state management
"""
import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable

from backend.smart_home.mqtt_client import get_mqtt_client


@dataclass
class Device:
    id: str
    name: str
    type: str
    room: str = "unknown"
    state: dict = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    last_updated: str = ""
    mqtt_topic: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


class DeviceManager:
    """Manages device registry and state"""
    
    DEVICE_TYPES = {
        "light": {"capabilities": ["on_off", "brightness", "color"]},
        "switch": {"capabilities": ["on_off"]},
        "sensor": {"capabilities": ["temperature", "humidity", "motion"]},
        "thermostat": {"capabilities": ["temperature", "mode", "target_temp"]},
        "camera": {"capabilities": ["stream", "snapshot", "motion_detect"]},
        "speaker": {"capabilities": ["volume", "play", "pause"]},
        "tv": {"capabilities": ["power", "volume", "channel", "input"]},
        "fan": {"capabilities": ["on_off", "speed"]},
        "blinds": {"capabilities": ["position"]},
    }
    
    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path or "security_data/smart_home/devices.json")
        self.devices: Dict[str, Device] = {}
        self._lock = threading.Lock()
        self._mqtt = None
        self._state_callbacks: List[Callable] = []
        
        self._load_devices()
    
    def _load_devices(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for device_id, device_data in data.get("devices", {}).items():
                    self.devices[device_id] = Device(**device_data)
                    
                print(f"[DeviceManager] Loaded {len(self.devices)} devices")
            except Exception as e:
                print(f"[DeviceManager] Load error: {e}")
    
    def _save_devices(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = {
                "devices": {did: d.to_dict() for did, d in self.devices.items()},
                "last_updated": datetime.now().isoformat()
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[DeviceManager] Save error: {e}")
    
    def initialize(self) -> bool:
        self._mqtt = get_mqtt_client()
        
        if not self._mqtt.connect():
            print("[DeviceManager] MQTT connection failed, running in offline mode")
            return False
        
        self._mqtt.subscribe("home/+/+/state", self._on_device_state)
        self._mqtt.subscribe("home/+/+/status", self._on_device_status)
        
        print("[DeviceManager] Initialized with MQTT")
        return True
    
    def _on_device_state(self, topic: str, payload: dict):
        try:
            parts = topic.split('/')
            if len(parts) >= 4:
                room = parts[1]
                device_id = parts[2]
                
                if device_id in self.devices:
                    self.update_device_state(device_id, payload)
        except Exception as e:
            print(f"[DeviceManager] State update error: {e}")
    
    def _on_device_status(self, topic: str, payload: dict):
        try:
            parts = topic.split('/')
            if len(parts) >= 4:
                device_id = parts[2]
                
                if device_id in self.devices:
                    device = self.devices[device_id]
                    device.state["online"] = payload.get("online", True)
                    device.last_updated = datetime.now().isoformat()
        except Exception as e:
            print(f"[DeviceManager] Status update error: {e}")
    
    def register_device(
        self,
        device_id: str,
        name: str,
        device_type: str,
        room: str = "unknown",
        mqtt_topic: str = None,
        capabilities: List[str] = None,
    ) -> Device:
        with self._lock:
            if device_id in self.devices:
                print(f"[DeviceManager] Device {device_id} already exists, updating...")
            
            type_info = self.DEVICE_TYPES.get(device_type, {})
            default_caps = capabilities or type_info.get("capabilities", [])
            
            device = Device(
                id=device_id,
                name=name,
                type=device_type,
                room=room,
                mqtt_topic=mqtt_topic or f"home/{room}/{device_id}",
                capabilities=default_caps,
                state={},
                last_updated=datetime.now().isoformat(),
            )
            
            self.devices[device_id] = device
            self._save_devices()
            
            print(f"[DeviceManager] Registered device: {name} ({device_type}) in {room}")
            return device
    
    def unregister_device(self, device_id: str) -> bool:
        with self._lock:
            if device_id not in self.devices:
                return False
            
            del self.devices[device_id]
            self._save_devices()
            
            print(f"[DeviceManager] Unregistered device: {device_id}")
            return True
    
    def get_device(self, device_id: str) -> Optional[Device]:
        return self.devices.get(device_id)
    
    def get_all_devices(self) -> Dict[str, Device]:
        return self.devices.copy()
    
    def get_devices_by_room(self, room: str) -> List[Device]:
        return [d for d in self.devices.values() if d.room == room]
    
    def get_devices_by_type(self, device_type: str) -> List[Device]:
        return [d for d in self.devices.values() if d.type == device_type]
    
    def update_device_state(self, device_id: str, state: dict) -> bool:
        with self._lock:
            if device_id not in self.devices:
                return False
            
            device = self.devices[device_id]
            device.state.update(state)
            device.last_updated = datetime.now().isoformat()
            
            for callback in self._state_callbacks:
                try:
                    callback(device_id, state)
                except Exception as e:
                    print(f"[DeviceManager] Callback error: {e}")
            
            return True
    
    def control_device(self, device_id: str, command: dict) -> bool:
        if device_id not in self.devices:
            print(f"[DeviceManager] Device {device_id} not found")
            return False
        
        device = self.devices[device_id]
        
        if not self._mqtt or not self._mqtt.is_connected:
            print("[DeviceManager] MQTT not connected, command queued")
            self.update_device_state(device_id, command)
            return True
        
        topic = f"{device.mqtt_topic}/command"
        return self._mqtt.publish(topic, command)
    
    def add_state_callback(self, callback: Callable[[str, dict], None]):
        self._state_callbacks.append(callback)
    
    def get_summary(self) -> dict:
        rooms = {}
        types = {}
        
        for device in self.devices.values():
            rooms[device.room] = rooms.get(device.room, 0) + 1
            types[device.type] = types.get(device.type, 0) + 1
        
        online_count = sum(1 for d in self.devices.values() if d.state.get("online", False))
        
        return {
            "total_devices": len(self.devices),
            "online_devices": online_count,
            "rooms": rooms,
            "types": types,
        }


_device_manager_instance: Optional[DeviceManager] = None


def get_device_manager() -> DeviceManager:
    global _device_manager_instance
    if _device_manager_instance is None:
        _device_manager_instance = DeviceManager()
    return _device_manager_instance
