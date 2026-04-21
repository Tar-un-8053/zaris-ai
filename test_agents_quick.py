"""
Quick test script for multi-agent architecture (without LLM loading).
Run: python test_agents_quick.py
"""


def main():
    print("=" * 60)
    print("ZARIS AI - Quick Agent Test (No LLM)")
    print("=" * 60)
    
    print("\n[1] Importing modules...")
    try:
        from backend.core.agents.base import BaseAgent, AgentContext, AgentResponse, AgentCapability
        print("    base.py - OK")
        
        from backend.core.agents.orchestrator import AgentOrchestrator, get_orchestrator
        print("    orchestrator.py - OK")
        
        from backend.core.agents.security_agent import SecurityAgent, create_security_agent
        print("    security_agent.py - OK")
        
        from backend.core.agents.system_agent import SystemAgent, create_system_agent
        print("    system_agent.py - OK")
        
        from backend.core.agents.knowledge_agent import KnowledgeAgent, create_knowledge_agent
        print("    knowledge_agent.py - OK")
        
        from backend.core.config import get_config, ZarisConfig
        print("    config.py - OK")
        
    except Exception as e:
        print(f"    ERROR: {e}")
        return
    
    print("\n[2] Creating orchestrator...")
    orchestrator = get_orchestrator()
    print("    OK")
    
    print("\n[3] Registering agents...")
    security_agent = create_security_agent()
    orchestrator.register_agent(security_agent)
    print(f"    Registered: {security_agent.name}")
    
    system_agent = create_system_agent()
    orchestrator.register_agent(system_agent)
    print(f"    Registered: {system_agent.name}")
    
    knowledge_agent = create_knowledge_agent()
    orchestrator.register_agent(knowledge_agent)
    print(f"    Registered: {knowledge_agent.name}")
    
    print("\n[4] Testing routing...")
    test_queries = [
        "scan downloads",
        "system status",
        "cpu usage",
        "memory dashboard",
        "threat score",
        "show disk",
        "what time is it",
    ]
    
    for query in test_queries:
        context = AgentContext(query=query, source="test")
        decision = orchestrator.route(context)
        print(f"    '{query}' -> {decision.agent_name} (conf: {decision.confidence:.2f})")
    
    print("\n[5] Testing execution...")
    test_queries_exec = [
        "cpu usage",
        "what time is it",
        "show disk",
    ]
    
    for query in test_queries_exec:
        context = AgentContext(query=query, source="test")
        response = orchestrator.execute(context)
        print(f"\n    Query: '{query}'")
        print(f"    Agent: {response.agent_name}")
        print(f"    Success: {response.success}")
        if len(response.message) > 100:
            print(f"    Response: {response.message[:100]}...")
        else:
            print(f"    Response: {response.message}")
    
    print("\n[6] Agent status:")
    status = orchestrator.get_status()
    print(f"    Total agents: {status['total_agents']}")
    print(f"    Enabled agents: {status['enabled_agents']}")
    
    print("\n" + "=" * 60)
    print("Quick test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
