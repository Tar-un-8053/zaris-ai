from backend.core.agents.base import (
    AgentCapability,
    AgentContext,
    AgentPriority,
    AgentResponse,
    BaseAgent,
)
from backend.core.agents.orchestrator import (
    AgentOrchestrator,
    OrchestratorConfig,
    RoutingDecision,
    get_orchestrator,
)
from backend.core.agents.security_agent import SecurityAgent, create_security_agent
from backend.core.agents.system_agent import SystemAgent, create_system_agent
from backend.core.agents.knowledge_agent import KnowledgeAgent, create_knowledge_agent
from backend.core.agents.home_agent import HomeAgent, create_home_agent


def create_all_agents(config: dict = None) -> dict:
    agents = {}
    
    security_agent = create_security_agent(config)
    agents[security_agent.name] = security_agent
    
    system_agent = create_system_agent(config)
    agents[system_agent.name] = system_agent
    
    knowledge_agent = create_knowledge_agent(config)
    agents[knowledge_agent.name] = knowledge_agent
    
    home_agent = create_home_agent(config)
    agents[home_agent.name] = home_agent
    
    return agents


def register_all_agents(orchestrator: AgentOrchestrator = None, config: dict = None) -> AgentOrchestrator:
    if orchestrator is None:
        orchestrator = get_orchestrator()
    
    agents = create_all_agents(config)
    
    for agent in agents.values():
        orchestrator.register_agent(agent)
    
    return orchestrator


__all__ = [
    "AgentCapability",
    "AgentContext",
    "AgentOrchestrator",
    "AgentPriority",
    "AgentResponse",
    "BaseAgent",
    "KnowledgeAgent",
    "OrchestratorConfig",
    "RoutingDecision",
    "SecurityAgent",
    "SystemAgent",
    "HomeAgent",
    "create_all_agents",
    "create_knowledge_agent",
    "create_security_agent",
    "create_system_agent",
    "create_home_agent",
    "get_orchestrator",
    "register_all_agents",
]
