"""
Test script for Smart Home Hub
Run: python test_smart_home.py
"""


def main():
    print("=" * 60)
    print("ZARIS AI - Smart Home Hub Test")
    print("=" * 60)
    
    print("\n[1] Importing modules...")
    try:
        from backend.smart_home.mqtt_client import MQTTClient, get_mqtt_client
        print("    mqtt_client.py - OK")
        
        from backend.smart_home.device_manager import DeviceManager, get_device_manager
        print("    device_manager.py - OK")
        
        from backend.smart_home.scene_engine import SceneEngine, get_scene_engine
        print("    scene_engine.py - OK")
        
        from backend.core.agents.home_agent import HomeAgent, create_home_agent
        print("    home_agent.py - OK")
        
    except Exception as e:
        print(f"    ERROR: {e}")
        return
    
    print("\n[2] Creating components...")
    
    mqtt = get_mqtt_client()
    print(f"    MQTT Client: {mqtt.broker}:{mqtt.port}")
    
    device_manager = get_device_manager()
    print(f"    Device Manager: {len(device_manager.devices)} devices loaded")
    
    scene_engine = get_scene_engine()
    scene_engine.initialize()
    print(f"    Scene Engine: {len(scene_engine.scenes)} scenes loaded")
    
    home_agent = create_home_agent()
    print(f"    Home Agent: {home_agent.name}")
    
    print("\n[3] Testing Home Agent routing...")
    from backend.core.agents.base import AgentContext
    
    test_queries = [
        "turn on lights",
        "movie mode",
        "good night",
        "show devices",
        "dim the lights",
    ]
    
    for query in test_queries:
        context = AgentContext(query=query, source="test")
        can_handle = home_agent.can_handle(context)
        confidence = home_agent.get_confidence(context)
        print(f"    '{query}' -> can_handle={can_handle}, conf={confidence:.2f}")
    
    print("\n[4] Testing scenes...")
    scenes = scene_engine.get_all_scenes()
    for scene_id, scene in scenes.items():
        triggers = len(scene.triggers)
        actions = len(scene.actions)
        print(f"    {scene.name}: {triggers} triggers, {actions} actions, enabled={scene.enabled}")
    
    print("\n[5] Testing device manager...")
    summary = device_manager.get_summary()
    print(f"    Total devices: {summary['total_devices']}")
    print(f"    Rooms: {summary['rooms']}")
    print(f"    Types: {summary['types']}")
    
    print("\n[6] Registering test device...")
    device = device_manager.register_device(
        device_id="test_light_1",
        name="Test Light",
        device_type="light",
        room="bedroom",
        capabilities=["on_off", "brightness"]
    )
    print(f"    Registered: {device.name} in {device.room}")
    
    print("\n[7] Testing device control...")
    device_manager.update_device_state("test_light_1", {"on_off": True, "brightness": 80})
    updated_device = device_manager.get_device("test_light_1")
    print(f"    State updated: {updated_device.state}")
    
    print("\n[8] Testing scene voice triggers...")
    voice_triggers = [
        "movie mode",
        "good night",
        "away mode",
        "good morning",
    ]
    
    for trigger in voice_triggers:
        matched_scene = scene_engine.check_voice_triggers(trigger)
        if matched_scene:
            print(f"    '{trigger}' -> Scene: {matched_scene}")
        else:
            print(f"    '{trigger}' -> No match")
    
    print("\n[9] Smart Home Status:")
    from backend.smart_home import get_smart_home_status
    status = get_smart_home_status()
    print(f"    MQTT: connected={status['mqtt']['connected']}")
    print(f"    Devices: {status['devices']['total_devices']}")
    print(f"    Scenes: {status['scenes']['total_scenes']}")
    
    print("\n" + "=" * 60)
    print("Smart Home Hub test completed!")
    print("=" * 60)
    
    print("\nNote: MQTT broker connection requires Mosquitto or similar broker.")
    print("      The system will run in offline mode without MQTT.")


if __name__ == "__main__":
    main()
