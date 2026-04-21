"""
Bridge module to integrate the new multi-agent architecture with existing ZARIS code.
This allows gradual migration without breaking existing functionality.
"""

import threading
from typing import Optional, Tuple

from backend.core.agents import (
    AgentContext,
    AgentOrchestrator,
    AgentResponse,
    get_orchestrator,
    register_all_agents,
)
from backend.core.agents.base import AgentCapability
from backend.core.llm import get_llm
from backend.core.voice import get_stt


_bridge_initialized = False
_bridge_lock = threading.Lock()


def initialize_bridge(init_llm: bool = False, init_stt: bool = False) -> bool:
    global _bridge_initialized
    
    if _bridge_initialized:
        return True
    
    with _bridge_lock:
        if _bridge_initialized:
            return True
        
        try:
            orchestrator = get_orchestrator()
            register_all_agents(orchestrator)
            
            if init_llm:
                try:
                    llm = get_llm()
                    llm.initialize()
                except Exception as e:
                    print(f"[Bridge] LLM initialization skipped: {e}")
            
            if init_stt:
                try:
                    stt = get_stt()
                    stt.initialize()
                except Exception as e:
                    print(f"[Bridge] STT initialization skipped: {e}")
            
            _bridge_initialized = True
            print("[Bridge] Multi-agent system initialized (agents only)")
            return True
            
        except Exception as e:
            print(f"[Bridge] Initialization failed: {e}")
            return False


def handle_query_via_agents(query: str, source: str = "unknown") -> Tuple[bool, str]:
    if not _bridge_initialized:
        initialize_bridge()
    
    if not query or not query.strip():
        return False, "Empty query"
    
    orchestrator = get_orchestrator()
    context = AgentContext(
        query=query.strip(),
        source=source,
        metadata={}
    )
    
    response = orchestrator.execute(context)
    
    return response.success, response.message


def get_agent_status() -> dict:
    if not _bridge_initialized:
        initialize_bridge()
    
    orchestrator = get_orchestrator()
    return orchestrator.get_status()


def route_to_agent(query: str, source: str = "unknown") -> Optional[AgentResponse]:
    if not _bridge_initialized:
        initialize_bridge()
    
    orchestrator = get_orchestrator()
    context = AgentContext(
        query=query.strip(),
        source=source,
    )
    
    decision = orchestrator.route(context)
    
    if decision.agent_name == "none":
        return None
    
    return orchestrator.execute(context)


def is_bridge_ready() -> bool:
    return _bridge_initialized


def llm_chat(message: str, system_prompt: str = None, history: list = None) -> str:
    if not _bridge_initialized:
        initialize_bridge()
    
    llm = get_llm()
    return llm.chat(message, system_prompt=system_prompt, history=history)


def transcribe_audio_hybrid(audio_data, languages: list = None) -> Tuple[bool, str, float]:
    if not _bridge_initialized:
        initialize_bridge()
    
    stt = get_stt()
    
    kwargs = {}
    if languages:
        kwargs["languages"] = languages
    
    result = stt.transcribe(audio_data, **kwargs)
    
    return result.success, result.text, result.latency_ms


__all__ = [
    "initialize_bridge",
    "handle_query_via_agents",
    "get_agent_status",
    "route_to_agent",
    "is_bridge_ready",
    "llm_chat",
    "transcribe_audio_hybrid",
]
