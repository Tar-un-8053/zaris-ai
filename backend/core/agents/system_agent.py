import re
from typing import Optional

from backend.core.agents.base import (
    AgentCapability,
    AgentContext,
    AgentPriority,
    AgentResponse,
    BaseAgent,
)


SYSTEM_KEYWORDS = [
    "system", "cpu", "ram", "memory", "disk", "drive", "storage",
    "process", "battery", "power", "temperature", "fan", "performance",
    "health", "status", "monitor", "usage", "percent", "gb", "mb",
    "shutdown", "restart", "reboot", "sleep", "wake", "lock",
    "screenshot", "volume", "brightness", "wifi", "bluetooth",
    "open", "close", "launch", "app", "application", "window",
    "time", "date", "weather", "reminder", "alarm", "timer",
    "clean", "optimize", "clear", "free", "space",
]

SYSTEM_PATTERNS = [
    r"(show|get|check)\s*(system|cpu|ram|memory|disk|battery)",
    r"(cpu|ram|memory|disk|storage)\s*(usage|info|status)",
    r"(shutdown|restart|reboot|sleep|lock)\s*(computer|pc|laptop|system)?",
    r"(open|launch|start)\s*\w+",
    r"(set|change|adjust)\s*(volume|brightness)",
    r"(what\s*(is|'s)\s*)?(the\s*)?(time|date)",
    r"system\s*(health|status|info)",
    r"top\s*processes",
    r"(clean|optimize|free)\s*(up)?\s*(space|memory|disk)?",
]


class SystemAgent(BaseAgent):
    name = "system_agent"
    capability = AgentCapability.SYSTEM
    priority = AgentPriority.HIGH
    description = "Handles system monitoring, control, and status queries"
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in SYSTEM_PATTERNS]
        self._monitor = None
    
    def _on_initialize(self) -> bool:
        try:
            from backend.system_monitor import get_system_monitor
            self._monitor = get_system_monitor()
            return True
        except Exception as e:
            print(f"[SystemAgent] Monitor not available: {e}")
            return True
    
    def can_handle(self, context: AgentContext) -> bool:
        query = context.query.lower()
        
        if any(kw in query for kw in SYSTEM_KEYWORDS):
            return True
        
        for pattern in self._compiled_patterns:
            if pattern.search(query):
                return True
        
        return False
    
    def get_confidence(self, context: AgentContext) -> float:
        query = context.query.lower()
        confidence = 0.0
        
        keyword_matches = sum(1 for kw in SYSTEM_KEYWORDS if kw in query)
        confidence += min(keyword_matches * 0.1, 0.5)
        
        pattern_matches = sum(1 for p in self._compiled_patterns if p.search(query))
        confidence += min(pattern_matches * 0.2, 0.3)
        
        if any(word in query for word in ["cpu", "ram", "disk", "battery"]):
            confidence += 0.2
        if any(word in query for word in ["shutdown", "restart", "lock"]):
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def handle(self, context: AgentContext) -> AgentResponse:
        query = context.query.lower().strip()
        
        if self._handle_system_status(query):
            return self._handle_system_status(query)
        
        if self._handle_power_control(query):
            return self._handle_power_control(query)
        
        if self._handle_app_control(query):
            return self._handle_app_control(query)
        
        if self._handle_time_date(query):
            return self._handle_time_date(query)
        
        return AgentResponse(
            success=False,
            message="System command not recognized. Try: system status, cpu usage, disk space.",
            agent_name=self.name,
            capability=self.capability,
            confidence=0.3,
        )
    
    def _handle_system_status(self, query: str) -> Optional[AgentResponse]:
        if "cpu" in query and ("usage" in query or "info" in query or "status" in query):
            if self._monitor:
                cpu = self._monitor.get_cpu_usage()
                return AgentResponse(
                    success=True,
                    message=f"CPU usage is {cpu} percent.",
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                    metadata={"cpu_percent": cpu},
                )
        
        if "ram" in query or "memory" in query:
            if self._monitor:
                ram = self._monitor.get_ram_usage()
                return AgentResponse(
                    success=True,
                    message=f"RAM: {ram['used_gb']:.1f} of {ram['total_gb']:.1f} GB used ({ram['percent']} percent).",
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                    metadata=ram,
                )
        
        if "disk" in query or "storage" in query or "drive" in query:
            if self._monitor:
                drives = self._monitor.get_all_drives()
                if drives:
                    lines = []
                    for d in drives:
                        lines.append(f"{d['drive']} {d['percent']} percent used")
                    return AgentResponse(
                        success=True,
                        message=". ".join(lines),
                        agent_name=self.name,
                        capability=self.capability,
                        confidence=0.95,
                        metadata={"drives": drives},
                    )
        
        if "process" in query:
            if self._monitor:
                processes = self._monitor.get_top_processes(5)
                if processes:
                    lines = [f"{p.name}: {p.memory_mb:.0f} MB" for p in processes]
                    return AgentResponse(
                        success=True,
                        message=f"Top processes by memory: {', '.join(lines)}",
                        agent_name=self.name,
                        capability=self.capability,
                        confidence=0.95,
                        metadata={"processes": [{"name": p.name, "memory_mb": p.memory_mb} for p in processes]},
                    )
        
        if "system status" in query or "system health" in query:
            if self._monitor:
                cpu = self._monitor.get_cpu_usage()
                ram = self._monitor.get_ram_usage()
                health = self._monitor.calculate_health_score()
                return AgentResponse(
                    success=True,
                    message=f"System health: {health} percent. CPU: {cpu} percent. RAM: {ram['percent']} percent used.",
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                    metadata={"health_score": health, "cpu": cpu, "ram": ram},
                )
        
        return None
    
    def _handle_power_control(self, query: str) -> Optional[AgentResponse]:
        if "shutdown" in query:
            return AgentResponse(
                success=True,
                message="Shutting down the system in 30 seconds. Say cancel to abort.",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.9,
                follow_up_action="shutdown",
                metadata={"action": "shutdown", "delay": 30},
            )
        
        if "restart" in query or "reboot" in query:
            return AgentResponse(
                success=True,
                message="Restarting the system in 30 seconds. Say cancel to abort.",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.9,
                follow_up_action="restart",
                metadata={"action": "restart", "delay": 30},
            )
        
        if "lock" in query and ("system" in query or "computer" in query or "laptop" in query):
            try:
                from backend.system_control import lock_screen
                lock_screen()
                return AgentResponse(
                    success=True,
                    message="System locked.",
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                )
            except Exception:
                return AgentResponse(
                    success=False,
                    message="Could not lock the system.",
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.5,
                )
        
        return None
    
    def _handle_app_control(self, query: str) -> Optional[AgentResponse]:
        import webbrowser
        
        if "youtube" in query and ("open" in query or "chalao" in query):
            webbrowser.open("https://www.youtube.com")
            return AgentResponse(
                success=True,
                message="Opening YouTube.",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.95,
            )
        
        if "google" in query and ("open" in query or "chalao" in query):
            webbrowser.open("https://www.google.com")
            return AgentResponse(
                success=True,
                message="Opening Google.",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.95,
            )
        
        return None
    
    def _handle_time_date(self, query: str) -> Optional[AgentResponse]:
        from datetime import datetime
        
        if "time" in query:
            now = datetime.now()
            return AgentResponse(
                success=True,
                message=f"The time is {now.strftime('%I:%M %p')}.",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.95,
            )
        
        if "date" in query:
            now = datetime.now()
            return AgentResponse(
                success=True,
                message=f"Today is {now.strftime('%A, %B %d, %Y')}.",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.95,
            )
        
        return None


def create_system_agent(config: Optional[dict] = None) -> SystemAgent:
    return SystemAgent(config)
