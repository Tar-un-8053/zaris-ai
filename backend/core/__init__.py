from backend.core.config import (
    LLMConfig,
    LLMProvider,
    VoiceConfig,
    SecurityConfig,
    MemoryConfig,
    HomeConfig,
    UIConfig,
    ZarisConfig,
    get_config,
    reload_config,
)
from backend.core.agents import (
    AgentCapability,
    AgentContext,
    AgentOrchestrator,
    AgentPriority,
    AgentResponse,
    BaseAgent,
    SecurityAgent,
    SystemAgent,
    KnowledgeAgent,
    HomeAgent,
    get_orchestrator,
    register_all_agents,
)
from backend.core.llm import (
    LLMResponse,
    HybridLLM,
    get_llm,
)


def initialize_zaris_core() -> AgentOrchestrator:
    config = get_config()
    orchestrator = get_orchestrator()
    register_all_agents(orchestrator)
    
    llm = get_llm()
    llm.initialize()
    
    print("[ZarisCore] Initialized with agents:", list(orchestrator.get_all_agents().keys()))
    return orchestrator


__all__ = [
    "LLMConfig",
    "LLMProvider",
    "VoiceConfig",
    "SecurityConfig",
    "MemoryConfig",
    "HomeConfig",
    "UIConfig",
    "ZarisConfig",
    "get_config",
    "reload_config",
    "AgentCapability",
    "AgentContext",
    "AgentOrchestrator",
    "AgentPriority",
    "AgentResponse",
    "BaseAgent",
    "SecurityAgent",
    "SystemAgent",
    "KnowledgeAgent",
    "get_orchestrator",
    "register_all_agents",
    "LLMResponse",
    "HybridLLM",
    "get_llm",
    "initialize_zaris_core",
]
