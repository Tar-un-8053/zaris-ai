from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import time


class AgentCapability(Enum):
    SECURITY = "security"
    SYSTEM = "system"
    KNOWLEDGE = "knowledge"
    HOME = "home"
    HEALTH = "health"
    GENERAL = "general"


class AgentPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class AgentContext:
    query: str
    source: str = "unknown"
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class AgentResponse:
    success: bool
    message: str
    agent_name: str
    capability: AgentCapability
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)
    should_speak: bool = True
    should_log: bool = True
    follow_up_action: Optional[str] = None
    error: Optional[str] = None


class BaseAgent(ABC):
    name: str = "base_agent"
    capability: AgentCapability = AgentCapability.GENERAL
    priority: AgentPriority = AgentPriority.MEDIUM
    description: str = "Base agent class"
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._enabled = True
        self._initialized = False
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    def initialize(self) -> bool:
        if self._initialized:
            return True
        try:
            result = self._on_initialize()
            self._initialized = result
            return result
        except Exception as e:
            print(f"[{self.name}] Initialization failed: {e}")
            return False
    
    def _on_initialize(self) -> bool:
        return True
    
    @abstractmethod
    def can_handle(self, context: AgentContext) -> bool:
        pass
    
    @abstractmethod
    def handle(self, context: AgentContext) -> AgentResponse:
        pass
    
    def get_confidence(self, context: AgentContext) -> float:
        return 1.0 if self.can_handle(context) else 0.0
    
    def validate_response(self, response: AgentResponse) -> AgentResponse:
        if not response.message:
            response.message = "Action completed."
        if not response.agent_name:
            response.agent_name = self.name
        if not response.capability:
            response.capability = self.capability
        return response
    
    def safe_handle(self, context: AgentContext) -> AgentResponse:
        if not self._enabled:
            return AgentResponse(
                success=False,
                message="Agent is disabled",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.0,
                error="agent_disabled"
            )
        
        if not self.can_handle(context):
            return AgentResponse(
                success=False,
                message="Agent cannot handle this request",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.0,
                error="cannot_handle"
            )
        
        try:
            response = self.handle(context)
            return self.validate_response(response)
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error: {str(e)}",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.0,
                error=str(e)
            )
    
    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name} capability={self.capability.value}>"
