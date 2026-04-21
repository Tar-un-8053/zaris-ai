import re
from typing import Optional

from backend.core.agents.base import (
    AgentCapability,
    AgentContext,
    AgentPriority,
    AgentResponse,
    BaseAgent,
)


KNOWLEDGE_KEYWORDS = [
    "remember", "memory", "study", "learn", "knowledge", "notes",
    "history", "dashboard", "what did i", "recall", "forget",
    "revision", "topic", "subject", "weak", "strong", "progress",
    "record", "save", "store", "retriev", "search", "find",
    "teach", "explain", "what is", "how to", "why", "when",
    "memory twin", "study history", "weak topics", "strong topics",
]

KNOWLEDGE_PATTERNS = [
    r"(remember|memorize|store|save)\s*(this|that|the)?",
    r"(what\s*did\s*i\s*(study|learn|read))",
    r"(memory|study)\s*(dashboard|history|status)",
    r"(show|get|list)\s*(my\s*)?(notes|memory|study)",
    r"(revision|review)\s*(plan|schedule|topics)",
    r"(weak|strong)\s*(topics?|areas?|subjects?)",
    r"(recall|remember)\s*",
    r"(add|create)\s*(memory|note|study)",
    r"verify\s*(memory|integrity)",
]


class KnowledgeAgent(BaseAgent):
    name = "knowledge_agent"
    capability = AgentCapability.KNOWLEDGE
    priority = AgentPriority.MEDIUM
    description = "Handles memory twin, knowledge storage, and RAG-based queries"
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in KNOWLEDGE_PATTERNS]
        self._memory_twin = None
        self._llm = None
    
    def _on_initialize(self) -> bool:
        try:
            from backend.memory_twin import get_dashboard
            self._memory_twin_available = True
            return True
        except Exception as e:
            print(f"[KnowledgeAgent] Memory twin not available: {e}")
            self._memory_twin_available = True
            return True
    
    def can_handle(self, context: AgentContext) -> bool:
        query = context.query.lower()
        
        if any(kw in query for kw in KNOWLEDGE_KEYWORDS):
            return True
        
        for pattern in self._compiled_patterns:
            if pattern.search(query):
                return True
        
        if query.startswith("what") or query.startswith("how") or query.startswith("why"):
            return True
        
        return False
    
    def get_confidence(self, context: AgentContext) -> float:
        query = context.query.lower()
        confidence = 0.0
        
        keyword_matches = sum(1 for kw in KNOWLEDGE_KEYWORDS if kw in query)
        confidence += min(keyword_matches * 0.12, 0.5)
        
        pattern_matches = sum(1 for p in self._compiled_patterns if p.search(query))
        confidence += min(pattern_matches * 0.2, 0.3)
        
        if "memory" in query or "study" in query:
            confidence += 0.2
        if any(word in query for word in ["remember", "recall", "what did i"]):
            confidence += 0.25
        
        return min(confidence, 1.0)
    
    def handle(self, context: AgentContext) -> AgentResponse:
        query = context.query.lower().strip()
        
        if "memory" in query or "study" in query:
            return self._handle_memory_commands(query)
        
        if any(word in query for word in ["what did i", "recall", "remember"]):
            return self._handle_recall(query)
        
        if "revision" in query:
            return self._handle_revision(query)
        
        if "weak" in query or "strong" in query:
            return self._handle_topic_analysis(query)
        
        if "verify" in query and "integrity" in query:
            return self._handle_integrity_check()
        
        if "add" in query or "remember" in query:
            return self._handle_add_memory(query, context)
        
        return self._handle_general_query(query)
    
    def _handle_memory_commands(self, query: str) -> AgentResponse:
        try:
            if "dashboard" in query or "status" in query:
                from backend.memory_twin import get_dashboard
                dashboard = get_dashboard()
                
                total_records = dashboard.get("total_records", 0)
                weak_topics = len(dashboard.get("weak_topics", []))
                strong_topics = len(dashboard.get("strong_topics", []))
                
                message = f"Memory dashboard: {total_records} records stored. "
                if weak_topics > 0:
                    message += f"{weak_topics} weak topics need attention. "
                if strong_topics > 0:
                    message += f"{strong_topics} strong topics. "
                
                return AgentResponse(
                    success=True,
                    message=message,
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                    metadata=dashboard,
                )
            
            if "history" in query:
                from backend.memory_twin import voice_history_reply
                reply = voice_history_reply()
                return AgentResponse(
                    success=True,
                    message=reply,
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Memory operation failed: {str(e)}",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.3,
                error=str(e),
            )
        
        return AgentResponse(
            success=False,
            message="Memory command not recognized.",
            agent_name=self.name,
            capability=self.capability,
            confidence=0.5,
        )
    
    def _handle_recall(self, query: str) -> AgentResponse:
        try:
            from backend.memory_twin import get_dashboard
            
            dashboard = get_dashboard()
            recent = dashboard.get("recent_records", [])
            
            if recent:
                topics = [r.get("topic", "unknown") for r in recent[:3]]
                message = f"Recent topics: {', '.join(topics)}."
            else:
                message = "No recent memory records found."
            
            return AgentResponse(
                success=True,
                message=message,
                agent_name=self.name,
                capability=self.capability,
                confidence=0.9,
                metadata={"recent_count": len(recent)},
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Recall failed: {str(e)}",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.3,
                error=str(e),
            )
    
    def _handle_revision(self, query: str) -> AgentResponse:
        try:
            from backend.memory_twin import voice_revision_reply
            reply = voice_revision_reply()
            return AgentResponse(
                success=True,
                message=reply,
                agent_name=self.name,
                capability=self.capability,
                confidence=0.95,
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Revision plan failed: {str(e)}",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.3,
                error=str(e),
            )
    
    def _handle_topic_analysis(self, query: str) -> AgentResponse:
        try:
            if "weak" in query:
                from backend.memory_twin import voice_weak_topics_reply
                reply = voice_weak_topics_reply()
                return AgentResponse(
                    success=True,
                    message=reply,
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                )
            
            if "strong" in query:
                from backend.memory_twin import voice_strong_topics_reply
                reply = voice_strong_topics_reply()
                return AgentResponse(
                    success=True,
                    message=reply,
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Topic analysis failed: {str(e)}",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.3,
                error=str(e),
            )
        
        return AgentResponse(
            success=False,
            message="Topic analysis not available.",
            agent_name=self.name,
            capability=self.capability,
            confidence=0.5,
        )
    
    def _handle_integrity_check(self) -> AgentResponse:
        try:
            from backend.memory_twin import verify_integrity
            result = verify_integrity()
            
            if result.get("valid", False):
                return AgentResponse(
                    success=True,
                    message="Memory integrity verified. All records are intact.",
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                    metadata=result,
                )
            else:
                return AgentResponse(
                    success=False,
                    message="Memory integrity check failed. Some records may be corrupted.",
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.8,
                    metadata=result,
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Integrity check failed: {str(e)}",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.3,
                error=str(e),
            )
    
    def _handle_add_memory(self, query: str, context: AgentContext) -> AgentResponse:
        try:
            from backend.memory_twin import add_study_record, parse_quick_add_command
            
            parsed = parse_quick_add_command(query)
            
            if parsed:
                result = add_study_record(
                    topic=parsed.get("topic", "general"),
                    content=parsed.get("content", query),
                    source_type="voice",
                    confidence=3,
                    importance=5,
                    source=context.source,
                )
                
                if result.get("success"):
                    return AgentResponse(
                        success=True,
                        message=f"Remembered: {parsed.get('topic', 'general')}",
                        agent_name=self.name,
                        capability=self.capability,
                        confidence=0.95,
                        metadata=result,
                    )
            
            return AgentResponse(
                success=False,
                message="Could not parse the memory command. Try: 'remember topic: content'",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.5,
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Failed to add memory: {str(e)}",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.3,
                error=str(e),
            )
    
    def _handle_general_query(self, query: str) -> AgentResponse:
        if query.startswith("what is") or query.startswith("how to") or query.startswith("why"):
            return AgentResponse(
                success=True,
                message="I can help you find information. Let me search my knowledge base.",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.7,
                follow_up_action="rag_search",
                metadata={"query": query},
            )
        
        return AgentResponse(
            success=False,
            message="Knowledge query not recognized.",
            agent_name=self.name,
            capability=self.capability,
            confidence=0.3,
        )


def create_knowledge_agent(config: Optional[dict] = None) -> KnowledgeAgent:
    return KnowledgeAgent(config)
