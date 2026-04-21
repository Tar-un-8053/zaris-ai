"""Smart Home Hub for ZARIS AI"""
from backend.smart_home.mqtt_client import MQTTClient, get_mqtt_client
from backend.smart_home.device_manager import Device, DeviceManager, get_device_manager
from backend.smart_home.scene_engine import Scene, SceneEngine, get_scene_engine


def initialize_smart_home() -> bool:
    mqtt = get_mqtt_client()
    device_manager = get_device_manager()
    scene_engine = get_scene_engine()
    
    if mqtt.connect():
        device_manager.initialize()
    else:
        print("[SmartHome] Running in offline mode (no MQTT broker)")
    
    scene_engine.initialize()
    
    print("[SmartHome] Hub initialized")
    return True


def get_smart_home_status() -> dict:
    mqtt = get_mqtt_client()
    device_manager = get_device_manager()
    scene_engine = get_scene_engine()
    
    return {
        "mqtt": mqtt.get_status(),
        "devices": device_manager.get_summary(),
        "scenes": scene_engine.get_summary(),
    }


__all__ = [
    "MQTTClient",
    "Device",
    "DeviceManager",
    "Scene",
    "SceneEngine",
    "get_mqtt_client",
    "get_device_manager",
    "get_scene_engine",
    "initialize_smart_home",
    "get_smart_home_status",
]
