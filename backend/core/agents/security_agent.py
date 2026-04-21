import re
from typing import Optional

from backend.core.agents.base import (
    AgentCapability,
    AgentContext,
    AgentPriority,
    AgentResponse,
    BaseAgent,
)


SECURITY_KEYWORDS = [
    "scan", "threat", "virus", "malware", "rat", "security", "protect",
    "alert", "danger", "suspicious", "harmful", "safe", "check file",
    "delete file", "block", "quarantine", "vault", "encrypt", "decrypt",
    "auth", "login", "password", "pin", "face", "voice auth", "verify",
    "intruder", "forensics", "capture", "panic", "decoy", "lock",
    "arm", "disarm", "guard", "cyber", "firewall", "network",
    "download", "folder scan", "duplicate", "unused", "system status",
    "memory usage", "cpu", "disk", "processes", "risky", "attack",
    "hack", "trojan", "backdoor", "keylog", "remote access",
]

SECURITY_PATTERNS = [
    r"scan\s+(downloads?|folder|file)",
    r"check\s+(file|folder|system)",
    r"(show|list|find)\s+(risky|threats?|duplicates?|unused)",
    r"(delete|remove|block)\s+(file|folder)",
    r"(security|guard)\s+(mode|status|on|off)",
    r"(verify|auth).*?(owner|identity|face|voice)",
    r"(vault|encrypt|decrypt|protect)",
    r"(panic|decoy|emergency)",
    r"threat\s*(score|level)?",
    r"(arm|disarm)\s*(security)?",
]


class SecurityAgent(BaseAgent):
    name = "security_agent"
    capability = AgentCapability.SECURITY
    priority = AgentPriority.CRITICAL
    description = "Handles security, threat detection, and system protection"
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in SECURITY_PATTERNS]
    
    def _on_initialize(self) -> bool:
        try:
            from backend.security import is_security_enabled
            self._security_available = True
            return True
        except Exception as e:
            print(f"[SecurityAgent] Security module not available: {e}")
            self._security_available = False
            return True
    
    def can_handle(self, context: AgentContext) -> bool:
        query = context.query.lower()
        
        if any(kw in query for kw in SECURITY_KEYWORDS):
            return True
        
        for pattern in self._compiled_patterns:
            if pattern.search(query):
                return True
        
        return False
    
    def get_confidence(self, context: AgentContext) -> float:
        query = context.query.lower()
        confidence = 0.0
        
        keyword_matches = sum(1 for kw in SECURITY_KEYWORDS if kw in query)
        confidence += min(keyword_matches * 0.15, 0.6)
        
        pattern_matches = sum(1 for p in self._compiled_patterns if p.search(query))
        confidence += min(pattern_matches * 0.2, 0.3)
        
        if any(word in query for word in ["scan", "threat", "virus", "malware", "rat"]):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def handle(self, context: AgentContext) -> AgentResponse:
        query = context.query.strip()
        
        try:
            from backend.security.zaris_core import (
                execute_core_command,
                normalize_core_command,
                ZARIS_HELP_TEXT,
            )
            from backend.security.manager import handle_security_command
            
            normalized = normalize_core_command(query.lower())
            
            if normalized:
                reply = execute_core_command(normalized, original_query=query)
                return AgentResponse(
                    success=True,
                    message=reply,
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.95,
                    metadata={"normalized_command": normalized},
                )
            
            if handle_security_command(query, query.lower()):
                return AgentResponse(
                    success=True,
                    message="Security command executed.",
                    agent_name=self.name,
                    capability=self.capability,
                    confidence=0.9,
                )
            
            return AgentResponse(
                success=True,
                message=ZARIS_HELP_TEXT,
                agent_name=self.name,
                capability=self.capability,
                confidence=0.7,
                metadata={"help_requested": True},
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Security command failed: {str(e)}",
                agent_name=self.name,
                capability=self.capability,
                confidence=0.0,
                error=str(e),
            )


def create_security_agent(config: Optional[dict] = None) -> SecurityAgent:
    return SecurityAgent(config)
