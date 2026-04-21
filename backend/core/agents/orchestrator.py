from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import threading
import time

from backend.core.agents.base import (
    AgentCapability,
    AgentContext,
    AgentPriority,
    AgentResponse,
    BaseAgent,
)


@dataclass
class OrchestratorConfig:
    max_agents: int = 10
    default_timeout: float = 30.0
    enable_fallback: bool = True
    log_decisions: bool = True
    confidence_threshold: float = 0.3


@dataclass
class RoutingDecision:
    agent_name: str
    confidence: float
    fallback_chain: List[str] = field(default_factory=list)
    reasoning: str = ""


class AgentOrchestrator:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self.config = config or OrchestratorConfig()
        self._agents: Dict[str, BaseAgent] = {}
        self._capability_map: Dict[AgentCapability, List[str]] = {}
        self._initialized = False
        self._decision_history: List[Tuple[float, str, RoutingDecision]] = []
    
    def register_agent(self, agent: BaseAgent) -> bool:
        if len(self._agents) >= self.config.max_agents:
            print(f"[Orchestrator] Max agents limit reached: {self.config.max_agents}")
            return False
        
        if agent.name in self._agents:
            print(f"[Orchestrator] Agent {agent.name} already registered")
            return False
        
        if not agent.initialize():
            print(f"[Orchestrator] Failed to initialize agent: {agent.name}")
            return False
        
        self._agents[agent.name] = agent
        
        if agent.capability not in self._capability_map:
            self._capability_map[agent.capability] = []
        self._capability_map[agent.capability].append(agent.name)
        self._capability_map[agent.capability].sort(
            key=lambda n: self._agents[n].priority.value
        )
        
        print(f"[Orchestrator] Registered agent: {agent.name} (capability={agent.capability.value})")
        return True
    
    def unregister_agent(self, agent_name: str) -> bool:
        if agent_name not in self._agents:
            return False
        
        agent = self._agents[agent_name]
        self._agents.pop(agent_name)
        
        if agent.capability in self._capability_map:
            self._capability_map[agent.capability] = [
                n for n in self._capability_map[agent.capability] if n != agent_name
            ]
        
        print(f"[Orchestrator] Unregistered agent: {agent_name}")
        return True
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_name)
    
    def get_all_agents(self) -> Dict[str, BaseAgent]:
        return self._agents.copy()
    
    def route(self, context: AgentContext) -> RoutingDecision:
        candidates: List[Tuple[str, float]] = []
        
        for name, agent in self._agents.items():
            if not agent.is_enabled:
                continue
            if agent.can_handle(context):
                confidence = agent.get_confidence(context)
                candidates.append((name, confidence))
        
        if not candidates:
            fallback = self._get_fallback_agent(context)
            if fallback:
                decision = RoutingDecision(
                    agent_name=fallback,
                    confidence=0.1,
                    reasoning="No primary agent available, using fallback"
                )
            else:
                decision = RoutingDecision(
                    agent_name="none",
                    confidence=0.0,
                    reasoning="No agent available for this request"
                )
        else:
            candidates.sort(key=lambda x: (-x[1], self._agents[x[0]].priority.value))
            best_name, best_conf = candidates[0]
            
            fallback_chain = [name for name, _ in candidates[1:4]]
            
            decision = RoutingDecision(
                agent_name=best_name,
                confidence=best_conf,
                fallback_chain=fallback_chain,
                reasoning=f"Selected {best_name} with confidence {best_conf:.2f}"
            )
        
        if self.config.log_decisions:
            self._decision_history.append((time.time(), context.query, decision))
            if len(self._decision_history) > 1000:
                self._decision_history = self._decision_history[-500:]
        
        return decision
    
    def execute(self, context: AgentContext) -> AgentResponse:
        decision = self.route(context)
        
        if decision.agent_name == "none":
            return AgentResponse(
                success=False,
                message="No agent available to handle this request",
                agent_name="orchestrator",
                capability=AgentCapability.GENERAL,
                confidence=0.0,
                error="no_agent_available"
            )
        
        agent = self._agents.get(decision.agent_name)
        if not agent:
            return AgentResponse(
                success=False,
                message=f"Agent {decision.agent_name} not found",
                agent_name="orchestrator",
                capability=AgentCapability.GENERAL,
                confidence=0.0,
                error="agent_not_found"
            )
        
        response = agent.safe_handle(context)
        
        if not response.success and self.config.enable_fallback and decision.fallback_chain:
            for fallback_name in decision.fallback_chain:
                fallback_agent = self._agents.get(fallback_name)
                if fallback_agent and fallback_agent.is_enabled:
                    fallback_response = fallback_agent.safe_handle(context)
                    if fallback_response.success:
                        return fallback_response
        
        return response
    
    def _get_fallback_agent(self, context: AgentContext) -> Optional[str]:
        for capability in [AgentCapability.GENERAL, AgentCapability.KNOWLEDGE]:
            if capability in self._capability_map and self._capability_map[capability]:
                return self._capability_map[capability][0]
        return None
    
    def broadcast(self, context: AgentContext, capabilities: Optional[List[AgentCapability]] = None) -> Dict[str, AgentResponse]:
        results = {}
        for name, agent in self._agents.items():
            if not agent.is_enabled:
                continue
            if capabilities and agent.capability not in capabilities:
                continue
            if agent.can_handle(context):
                results[name] = agent.safe_handle(context)
        return results
    
    def get_status(self) -> dict:
        return {
            "total_agents": len(self._agents),
            "enabled_agents": sum(1 for a in self._agents.values() if a.is_enabled),
            "capabilities": {
                cap.value: names for cap, names in self._capability_map.items()
            },
            "agents": [
                {
                    "name": name,
                    "capability": agent.capability.value,
                    "enabled": agent.is_enabled,
                    "initialized": agent._initialized,
                }
                for name, agent in self._agents.items()
            ],
        }


_orchestrator_instance: Optional[AgentOrchestrator] = None


def get_orchestrator(config: Optional[OrchestratorConfig] = None) -> AgentOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator(config)
    return _orchestrator_instance
