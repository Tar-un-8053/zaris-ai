from dataclasses import dataclass, field
from enum import Enum
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class LLMProvider(Enum):
    LLAMA_CPP = "llama_cpp"
    TRANSFORMERS = "transformers"
    ONNX = "onnx"
    AUTO = "auto"


@dataclass
class LLMConfig:
    provider: LLMProvider = LLMProvider.AUTO
    model_name: str = "phi-2"
    model_path: Optional[str] = None
    context_window: int = 2048
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    quantization: str = "q4_k_m"
    device: str = "auto"
    use_gpu: bool = True
    
    def get_effective_provider(self) -> LLMProvider:
        if self.provider != LLMProvider.AUTO:
            return self.provider
        
        try:
            import torch
            if torch.cuda.is_available():
                return LLMProvider.TRANSFORMERS
        except ImportError:
            pass
        
        try:
            import llama_cpp
            return LLMProvider.LLAMA_CPP
        except ImportError:
            pass
        
        return LLMProvider.TRANSFORMERS


@dataclass
class VoiceConfig:
    stt_engine: str = "whisper"
    stt_model: str = "base"
    stt_device: str = "auto"
    tts_engine: str = "edge_tts"
    tts_voice: str = "en-IN-PratimaNeural"
    wake_words: list = field(default_factory=lambda: ["zaris", "hey zaris", "jarvis"])
    wake_threshold: float = 0.5


@dataclass
class SecurityConfig:
    enabled: bool = True
    auto_arm_on_startup: bool = True
    require_face: bool = True
    require_voice: bool = False
    require_pin: bool = False
    threat_score_threshold: int = 70
    failed_attempt_threshold: int = 3
    monitor_usb: bool = True
    monitor_processes: bool = True
    monitor_downloads: bool = True


@dataclass
class MemoryConfig:
    enabled: bool = True
    vector_db: str = "chromadb"
    embedding_model: str = "all-MiniLM-L6-v2"
    max_records: int = 10000
    retention_days: int = 365


@dataclass
class HomeConfig:
    enabled: bool = False
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    homekit_enabled: bool = False
    alexa_enabled: bool = False


@dataclass
class UIConfig:
    frontend_mode: str = "eel"
    theme: str = "dark"
    enable_avatar: bool = True
    enable_animations: bool = True


@dataclass
class ZarisConfig:
    assistant_name: str = "Zaris AI"
    user_title: str = "operator"
    debug_mode: bool = False
    log_level: str = "INFO"
    data_dir: str = "security_data"
    models_dir: str = "models"
    llm: LLMConfig = field(default_factory=LLMConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    home: HomeConfig = field(default_factory=HomeConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    _instance = None
    
    @classmethod
    def get(cls) -> "ZarisConfig":
        if cls._instance is None:
            cls._instance = cls.load()
        return cls._instance
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "ZarisConfig":
        if config_path is None:
            config_path = os.getenv("ZARIS_CONFIG_PATH", "security_data/zaris_config.json")
        
        path = Path(config_path)
        
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls._from_dict(data)
            except Exception as e:
                print(f"[Config] Failed to load config from {config_path}: {e}")
        
        return cls()
    
    @classmethod
    def _from_dict(cls, data: dict) -> "ZarisConfig":
        llm_data = data.get("llm", {})
        if isinstance(llm_data.get("provider"), str):
            llm_data["provider"] = LLMProvider(llm_data["provider"])
        
        return cls(
            assistant_name=data.get("assistant_name", "Zaris AI"),
            user_title=data.get("user_title", "operator"),
            debug_mode=data.get("debug_mode", False),
            log_level=data.get("log_level", "INFO"),
            data_dir=data.get("data_dir", "security_data"),
            models_dir=data.get("models_dir", "models"),
            llm=LLMConfig(**llm_data) if llm_data else LLMConfig(),
            voice=VoiceConfig(**data.get("voice", {})),
            security=SecurityConfig(**data.get("security", {})),
            memory=MemoryConfig(**data.get("memory", {})),
            home=HomeConfig(**data.get("home", {})),
            ui=UIConfig(**data.get("ui", {})),
        )
    
    def to_dict(self) -> dict:
        return {
            "assistant_name": self.assistant_name,
            "user_title": self.user_title,
            "debug_mode": self.debug_mode,
            "log_level": self.log_level,
            "data_dir": self.data_dir,
            "models_dir": self.models_dir,
            "llm": {
                "provider": self.llm.provider.value,
                "model_name": self.llm.model_name,
                "model_path": self.llm.model_path,
                "context_window": self.llm.context_window,
                "max_tokens": self.llm.max_tokens,
                "temperature": self.llm.temperature,
                "top_p": self.llm.top_p,
                "quantization": self.llm.quantization,
                "device": self.llm.device,
                "use_gpu": self.llm.use_gpu,
            },
            "voice": {
                "stt_engine": self.voice.stt_engine,
                "stt_model": self.voice.stt_model,
                "stt_device": self.voice.stt_device,
                "tts_engine": self.voice.tts_engine,
                "tts_voice": self.voice.tts_voice,
                "wake_words": self.voice.wake_words,
                "wake_threshold": self.voice.wake_threshold,
            },
            "security": {
                "enabled": self.security.enabled,
                "auto_arm_on_startup": self.security.auto_arm_on_startup,
                "require_face": self.security.require_face,
                "require_voice": self.security.require_voice,
                "require_pin": self.security.require_pin,
                "threat_score_threshold": self.security.threat_score_threshold,
                "failed_attempt_threshold": self.security.failed_attempt_threshold,
                "monitor_usb": self.security.monitor_usb,
                "monitor_processes": self.security.monitor_processes,
                "monitor_downloads": self.security.monitor_downloads,
            },
            "memory": {
                "enabled": self.memory.enabled,
                "vector_db": self.memory.vector_db,
                "embedding_model": self.memory.embedding_model,
                "max_records": self.memory.max_records,
                "retention_days": self.memory.retention_days,
            },
            "home": {
                "enabled": self.home.enabled,
                "mqtt_broker": self.home.mqtt_broker,
                "mqtt_port": self.home.mqtt_port,
                "homekit_enabled": self.home.homekit_enabled,
                "alexa_enabled": self.home.alexa_enabled,
            },
            "ui": {
                "frontend_mode": self.ui.frontend_mode,
                "theme": self.ui.theme,
                "enable_avatar": self.ui.enable_avatar,
                "enable_animations": self.ui.enable_animations,
            },
        }
    
    def save(self, config_path: Optional[str] = None) -> bool:
        if config_path is None:
            config_path = os.getenv("ZARIS_CONFIG_PATH", "security_data/zaris_config.json")
        
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Config] Failed to save config to {config_path}: {e}")
            return False
    
    def get_data_path(self, *parts) -> Path:
        return Path(self.data_dir).joinpath(*parts)
    
    def get_model_path(self, *parts) -> Path:
        return Path(self.models_dir).joinpath(*parts)


def get_config() -> ZarisConfig:
    return ZarisConfig.get()


def reload_config() -> ZarisConfig:
    ZarisConfig._instance = None
    return ZarisConfig.get()


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
]
