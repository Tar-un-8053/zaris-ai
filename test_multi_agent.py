"""
Test script for the new multi-agent architecture.
Run: python test_multi_agent.py
"""

from backend.core.bridge import (
    initialize_bridge,
    handle_query_via_agents,
    get_agent_status,
    is_bridge_ready,
)


def main():
    print("=" * 60)
    print("ZARIS AI - Multi-Agent System Test")
    print("=" * 60)
    
    print("\n[1] Initializing bridge...")
    result = initialize_bridge()
    print(f"    Bridge initialized: {result}")
    print(f"    Bridge ready: {is_bridge_ready()}")
    
    print("\n[2] Agent Status:")
    status = get_agent_status()
    print(f"    Total agents: {status['total_agents']}")
    print(f"    Enabled agents: {status['enabled_agents']}")
    for agent in status['agents']:
        print(f"    - {agent['name']}: enabled={agent['enabled']}, capability={agent['capability']}")
    
    print("\n[3] Testing Queries:")
    print("-" * 60)
    
    test_queries = [
        ("scan downloads", "security"),
        ("system status", "system"),
        ("cpu usage", "system"),
        ("memory dashboard", "knowledge"),
        ("what time is it", "system"),
        ("threat score", "security"),
        ("show disk", "system"),
    ]
    
    for query, expected_agent in test_queries:
        success, msg = handle_query_via_agents(query, source="test")
        print(f"\nQuery: '{query}'")
        print(f"  Expected agent: {expected_agent}")
        print(f"  Success: {success}")
        if len(msg) > 150:
            print(f"  Response: {msg[:150]}...")
        else:
            print(f"  Response: {msg}")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
