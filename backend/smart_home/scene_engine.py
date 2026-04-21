"""
Scene Engine for Smart Home Hub
Automation rules and scene management
"""
import json
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from backend.smart_home.device_manager import get_device_manager


@dataclass
class Action:
    device_id: str
    command: dict
    delay_seconds: float = 0.0


@dataclass
class Trigger:
    type: str
    condition: dict
    
    def matches(self, context: dict) -> bool:
        if self.type == "time":
            current_time = context.get("current_time")
            target_hour = self.condition.get("hour")
            target_minute = self.condition.get("minute")
            
            if target_hour is not None and current_time.hour != target_hour:
                return False
            if target_minute is not None and current_time.minute != target_minute:
                return False
            return True
        
        elif self.type == "device_state":
            device_id = self.condition.get("device_id")
            expected_state = self.condition.get("state", {})
            actual_state = context.get("device_states", {}).get(device_id, {})
            
            for key, value in expected_state.items():
                if actual_state.get(key) != value:
                    return False
            return True
        
        elif self.type == "voice":
            spoken = context.get("voice_text", "").lower()
            keywords = self.condition.get("keywords", [])
            return any(kw.lower() in spoken for kw in keywords)
        
        return False


@dataclass
class Scene:
    id: str
    name: str
    description: str = ""
    triggers: List[Trigger] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    enabled: bool = True
    last_triggered: str = ""
    trigger_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "triggers": [{"type": t.type, "condition": t.condition} for t in self.triggers],
            "actions": [asdict(a) for a in self.actions],
            "enabled": self.enabled,
            "last_triggered": self.last_triggered,
            "trigger_count": self.trigger_count,
        }


class SceneEngine:
    """Manages automation scenes and triggers"""
    
    BUILTIN_SCENES = [
        {
            "id": "goodnight",
            "name": "Good Night",
            "description": "Turn off all lights at night",
            "triggers": [{"type": "time", "condition": {"hour": 23}}],
            "actions": [
                {"device_id": "all_lights", "command": {"on_off": False}, "delay_seconds": 0}
            ],
            "enabled": True,
        },
        {
            "id": "morning",
            "name": "Good Morning",
            "description": "Turn on lights in the morning",
            "triggers": [{"type": "time", "condition": {"hour": 7}}],
            "actions": [
                {"device_id": "all_lights", "command": {"on_off": True, "brightness": 80}, "delay_seconds": 0}
            ],
            "enabled": True,
        },
        {
            "id": "away_mode",
            "name": "Away Mode",
            "description": "Turn off all devices when leaving",
            "triggers": [{"type": "voice", "condition": {"keywords": ["away mode", "leaving home", "goodbye home"]}}],
            "actions": [
                {"device_id": "all_devices", "command": {"on_off": False}, "delay_seconds": 0}
            ],
            "enabled": True,
        },
        {
            "id": "movie_mode",
            "name": "Movie Mode",
            "description": "Dim lights for movie",
            "triggers": [{"type": "voice", "condition": {"keywords": ["movie mode", "watch movie", "cinema mode"]}}],
            "actions": [
                {"device_id": "all_lights", "command": {"on_off": True, "brightness": 20}, "delay_seconds": 0}
            ],
            "enabled": True,
        },
    ]
    
    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path or "security_data/smart_home/scenes.json")
        self.scenes: Dict[str, Scene] = {}
        self._device_manager = None
        self._lock = threading.Lock()
        self._time_check_thread = None
        self._running = False
        self._last_minute = -1
        
        self._load_scenes()
        self._create_builtin_scenes()
    
    def _load_scenes(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for scene_id, scene_data in data.get("scenes", {}).items():
                    triggers = [
                        Trigger(**t) for t in scene_data.get("triggers", [])
                    ]
                    actions = [
                        Action(**a) for a in scene_data.get("actions", [])
                    ]
                    self.scenes[scene_id] = Scene(
                        id=scene_data["id"],
                        name=scene_data["name"],
                        description=scene_data.get("description", ""),
                        triggers=triggers,
                        actions=actions,
                        enabled=scene_data.get("enabled", True),
                        last_triggered=scene_data.get("last_triggered", ""),
                        trigger_count=scene_data.get("trigger_count", 0),
                    )
                    
                print(f"[SceneEngine] Loaded {len(self.scenes)} scenes")
            except Exception as e:
                print(f"[SceneEngine] Load error: {e}")
    
    def _save_scenes(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = {
                "scenes": {sid: s.to_dict() for sid, s in self.scenes.items()},
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[SceneEngine] Save error: {e}")
    
    def _create_builtin_scenes(self):
        for scene_data in self.BUILTIN_SCENES:
            if scene_data["id"] not in self.scenes:
                scene = Scene(
                    id=scene_data["id"],
                    name=scene_data["name"],
                    description=scene_data.get("description", ""),
                    triggers=[Trigger(**t) for t in scene_data.get("triggers", [])],
                    actions=[Action(**a) for a in scene_data.get("actions", [])],
                    enabled=scene_data.get("enabled", True),
                )
                self.scenes[scene.id] = scene
                print(f"[SceneEngine] Created builtin scene: {scene.name}")
        
        self._save_scenes()
    
    def initialize(self) -> bool:
        self._device_manager = get_device_manager()
        self._running = True
        
        self._time_check_thread = threading.Thread(target=self._time_trigger_loop, daemon=True)
        self._time_check_thread.start()
        
        self._device_manager.add_state_callback(self._on_device_state_change)
        
        print("[SceneEngine] Initialized")
        return True
    
    def _time_trigger_loop(self):
        while self._running:
            try:
                current_time = datetime.now()
                current_minute = current_time.minute
                
                if current_minute != self._last_minute:
                    self._last_minute = current_minute
                    
                    context = {
                        "current_time": current_time,
                        "device_states": {
                            d.id: d.state for d in self._device_manager.get_all_devices().values()
                        }
                    }
                    
                    for scene in self.scenes.values():
                        if not scene.enabled:
                            continue
                        
                        for trigger in scene.triggers:
                            if trigger.type == "time" and trigger.matches(context):
                                self._trigger_scene(scene.id)
                                break
                
                time.sleep(5)
                
            except Exception as e:
                print(f"[SceneEngine] Time trigger error: {e}")
                time.sleep(10)
    
    def _on_device_state_change(self, device_id: str, state: dict):
        if not self._running:
            return
        
        context = {
            "device_states": {
                d.id: d.state for d in self._device_manager.get_all_devices().values()
            }
        }
        
        for scene in self.scenes.values():
            if not scene.enabled:
                continue
            
            for trigger in scene.triggers:
                if trigger.type == "device_state" and trigger.matches(context):
                    self._trigger_scene(scene.id)
                    break
    
    def check_voice_triggers(self, voice_text: str) -> Optional[str]:
        context = {"voice_text": voice_text}
        
        for scene in self.scenes.values():
            if not scene.enabled:
                continue
            
            for trigger in scene.triggers:
                if trigger.type == "voice" and trigger.matches(context):
                    self._trigger_scene(scene.id)
                    return scene.name
        
        return None
    
    def _trigger_scene(self, scene_id: str) -> bool:
        if scene_id not in self.scenes:
            return False
        
        scene = self.scenes[scene_id]
        
        print(f"[SceneEngine] Triggering scene: {scene.name}")
        
        for action in scene.actions:
            if action.delay_seconds > 0:
                threading.Timer(action.delay_seconds, lambda a=action: self._execute_action(a)).start()
            else:
                self._execute_action(action)
        
        scene.last_triggered = datetime.now().isoformat()
        scene.trigger_count += 1
        self._save_scenes()
        
        return True
    
    def _execute_action(self, action: Action) -> bool:
        try:
            if self._device_manager is None:
                print("[SceneEngine] Device manager not initialized")
                return False
            
            if action.device_id == "all_lights":
                for device in self._device_manager.get_devices_by_type("light"):
                    self._device_manager.control_device(device.id, action.command)
            elif action.device_id == "all_devices":
                for device in self._device_manager.get_all_devices().values():
                    if "on_off" in device.capabilities:
                        self._device_manager.control_device(device.id, action.command)
            else:
                return self._device_manager.control_device(action.device_id, action.command)
            
            return True
        except Exception as e:
            print(f"[SceneEngine] Action execution error: {e}")
            return False
    
    def create_scene(
        self,
        scene_id: str,
        name: str,
        triggers: List[dict],
        actions: List[dict],
        description: str = "",
        enabled: bool = True,
    ) -> Scene:
        with self._lock:
            trigger_objs = [Trigger(**t) for t in triggers]
            action_objs = [Action(**a) for a in actions]
            
            scene = Scene(
                id=scene_id,
                name=name,
                description=description,
                triggers=trigger_objs,
                actions=action_objs,
                enabled=enabled,
            )
            
            self.scenes[scene_id] = scene
            self._save_scenes()
            
            print(f"[SceneEngine] Created scene: {name}")
            return scene
    
    def delete_scene(self, scene_id: str) -> bool:
        with self._lock:
            if scene_id not in self.scenes:
                return False
            
            del self.scenes[scene_id]
            self._save_scenes()
            
            print(f"[SceneEngine] Deleted scene: {scene_id}")
            return True
    
    def get_scene(self, scene_id: str) -> Optional[Scene]:
        return self.scenes.get(scene_id)
    
    def get_all_scenes(self) -> Dict[str, Scene]:
        return self.scenes.copy()
    
    def enable_scene(self, scene_id: str) -> bool:
        if scene_id in self.scenes:
            self.scenes[scene_id].enabled = True
            self._save_scenes()
            return True
        return False
    
    def disable_scene(self, scene_id: str) -> bool:
        if scene_id in self.scenes:
            self.scenes[scene_id].enabled = False
            self._save_scenes()
            return True
        return False
    
    def trigger_scene_manual(self, scene_id: str) -> bool:
        return self._trigger_scene(scene_id)
    
    def get_summary(self) -> dict:
        enabled_count = sum(1 for s in self.scenes.values() if s.enabled)
        triggered_today = 0
        
        for s in self.scenes.values():
            if s.last_triggered:
                try:
                    triggered_date = datetime.fromisoformat(s.last_triggered).date()
                    if triggered_date == datetime.now().date():
                        triggered_today += 1
                except:
                    pass
        
        return {
            "total_scenes": len(self.scenes),
            "enabled_scenes": enabled_count,
            "triggered_today": triggered_today,
        }


_scene_engine_instance: Optional[SceneEngine] = None


def get_scene_engine() -> SceneEngine:
    global _scene_engine_instance
    if _scene_engine_instance is None:
        _scene_engine_instance = SceneEngine()
    return _scene_engine_instance
