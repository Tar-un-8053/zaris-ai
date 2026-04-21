import re
from typing import Optional, List

from backend.core.agents.base import (
    AgentCapability,
    AgentContext,
    AgentPriority,
    AgentResponse,
    BaseAgent,
)


HOME_KEYWORDS = [
    "light", "lamp", "switch", "fan", "ac", "heater", "thermostat",
    "tv", "television", "speaker", "music", "blinds", "curtain",
    "room", "bedroom", "kitchen", "living", "bathroom", "hall",
    "turn on", "turn off", "switch on", "switch off", "dim", "bright",
    "scene", "automation", "routine", "mode", "movie", "night", "morning",
    "temperature", "heat", "cool", "warm", "cold",
    "home", "house", "device", "control", "smart",
]

HOME_PATTERNS = [
    r"(turn|switch)\s*(on|off)\s*(the\s*)?(light|fan|ac|tv|heater)",
    r"(dim|brighten|set)\s*(the\s*)?(light|lights)",
    r"(set|change)\s*(the\s*)?(temperature|temp)",
    r"(start|stop|play|pause)\s*(the\s*)?(music|tv)",
    r"(activate|enable|run)\s*(the\s*)?(scene|mode)\s*\w+",
    r"(what|show|list)\s*(devices|scenes|rooms)",
    r"(good\s*night|good\s*morning|movie\s*mode|away\s*mode)",
    r"(all\s*)?(lights|devices)\s*(on|off)",
]


class HomeAgent(BaseAgent):
    name = "home_agent"
    capability = AgentCapability.HOME
    priority = AgentPriority.MEDIUM
    description = "Handles smart home control, devices, and scenes"
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in HOME_PATTERNS]
        self._mqtt = None
        self._device_manager = None
        self._scene_engine = None
    
    def _on_initialize(self) -> bool:
        try:
            from backend.smart_home import get_mqtt_client, get_device_manager, get_scene_engine
            self._mqtt = get_mqtt_client()
            self._device_manager = get_device_manager()
            self._scene_engine = get_scene_engine()
            return True
        except Exception as e:
            print(f"[HomeAgent] Smart home not available: {e}")
            return True
    
    def can_handle(self, context: AgentContext) -> bool:
        query = context.query.lower()
        
        if any(kw in query for kw in HOME_KEYWORDS):
            return True
        
        for pattern in self._compiled_patterns:
            if pattern.search(query):
                return True
        
        return False
    
    def get_confidence(self, context: AgentContext) -> float:
        query = context.query.lower()
        confidence = 0.0
        
        keyword_matches = sum(1 for kw in HOME_KEYWORDS if kw in query)
        confidence += min(keyword_matches * 0.1, 0.4)
        
        pattern_matches = sum(1 for p in self._compiled_patterns if p.search(query))
        confidence += min(pattern_matches * 0.2, 0.3)
        
        if any(word in query for word in ["light", "fan", "ac", "tv"]):
            confidence += 0.2
        if any(word in query for word in ["turn on", "turn off", "switch"]):
            confidence += 0.2
        if "scene" in query or "mode" in query:
            confidence += 0.15
        
        return min(confidence, 1.0)
    
    def handle(self, context: AgentContext) -> AgentResponse:
        query = context.query.lower().strip()
        
        scene_name = self._check_scene_trigger(query)
        if scene_name:
            return AgentResponse(
                success=True,
                message=f"Activated scene: {scene_name}",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.95,
                metadata={"scene": scene_name}
            )
        
        device_control = self._handle_device_control(query)
        if device_control:
            return device_control
        
        status_response = self._handle_status_query(query)
        if status_response:
            return status_response
        
        return AgentResponse(
            success=False,
            message="Home command not recognized. Try: 'turn on lights', 'movie mode', 'show devices'.",
            agent_name=self.name,
            capability=self.capability,
            confidence=0.3,
        )
    
    def _check_scene_trigger(self, query: str) -> Optional[str]:
        if not self._scene_engine:
            return None
        
        scene_name = self._scene_engine.check_voice_triggers(query)
        return scene_name
    
    def _handle_device_control(self, query: str) -> Optional[AgentResponse]:
        if not self._device_manager:
            return None
        
        devices = self._device_manager.get_all_devices()
        if not devices:
            return AgentResponse(
                success=False,
                message="No devices registered. Register devices first using the home dashboard.",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.5,
            )
        
        target_device = None
        command = {}
        
        for device in devices.values():
            if device.name.lower() in query or device.id.lower() in query:
                target_device = device
                break
        
        if "all lights" in query or "all devices" in query:
            if "turn on" in query or "switch on" in query:
                command = {"on_off": True}
                for device in self._device_manager.get_devices_by_type("light"):
                    self._device_manager.control_device(device.id, command)
                return AgentResponse(
                    success=True,
                    message="All lights turned on.",
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                )
            
            if "turn off" in query or "switch off" in query:
                command = {"on_off": False}
                for device in self._device_manager.get_devices_by_type("light"):
                    self._device_manager.control_device(device.id, command)
                return AgentResponse(
                    success=True,
                    message="All lights turned off.",
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                )
        
        if not target_device:
            room = self._extract_room(query)
            if room:
                room_devices = self._device_manager.get_devices_by_room(room)
                if room_devices:
                    if "turn on" in query or "switch on" in query:
                        for device in room_devices:
                            self._device_manager.control_device(device.id, {"on_off": True})
                        return AgentResponse(
                            success=True,
                            message=f"All devices in {room} turned on.",
                            agent_name=self.name,
                            capability=self.capability,
                            confidence=0.9,
                        )
                    if "turn off" in query or "switch off" in query:
                        for device in room_devices:
                            self._device_manager.control_device(device.id, {"on_off": False})
                        return AgentResponse(
                            success=True,
                            message=f"All devices in {room} turned off.",
                            agent_name=self.name,
                            capability=self.capability,
                            confidence=0.9,
                        )
        
        if target_device:
            if "turn on" in query or "switch on" in query:
                command = {"on_off": True}
            elif "turn off" in query or "switch off" in query:
                command = {"on_off": False}
            elif "dim" in query:
                brightness = self._extract_brightness(query)
                command = {"on_off": True, "brightness": brightness}
            elif "bright" in query:
                command = {"on_off": True, "brightness": 100}
            else:
                command = {"toggle": True}
            
            success = self._device_manager.control_device(target_device.id, command)
            
            return AgentResponse(
                success=success,
                message=f"{target_device.name} {'updated' if success else 'control failed'}.",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.95,
                metadata={"device": target_device.id, "command": command}
            )
        
        return None
    
    def _handle_status_query(self, query: str) -> Optional[AgentResponse]:
        if not self._device_manager:
            return None
        
        if "show devices" in query or "list devices" in query or "what devices" in query:
            summary = self._device_manager.get_summary()
            return AgentResponse(
                success=True,
                message=f"You have {summary['total_devices']} devices in {len(summary['rooms'])} rooms.",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.95,
                metadata=summary
            )
        
        if "show scenes" in query or "list scenes" in query or "what scenes" in query:
            if self._scene_engine:
                scenes = self._scene_engine.get_all_scenes()
                scene_names = [s.name for s in scenes.values() if s.enabled]
                return AgentResponse(
                    success=True,
                    message=f"Available scenes: {', '.join(scene_names)}.",
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                )
        
        return None
    
    def _extract_room(self, query: str) -> Optional[str]:
        rooms = ["bedroom", "kitchen", "living", "living room", "bathroom", "hall", "study", "office"]
        for room in rooms:
            if room in query:
                return room.replace(" ", "_")
        return None
    
    def _extract_brightness(self, query: str) -> int:
        import re
        match = re.search(r'(\d+)%?', query)
        if match:
            return int(match.group(1))
        return 50


def create_home_agent(config: Optional[dict] = None) -> HomeAgent:
    return HomeAgent(config)
