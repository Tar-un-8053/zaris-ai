import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import threading

from backend.core.config import get_config, LLMProvider, LLMConfig


@dataclass
class LLMResponse:
    text: str
    tokens_generated: int
    latency_ms: float
    model: str
    provider: str
    success: bool = True
    error: Optional[str] = None


class BaseLLMEngine:
    def __init__(self, config: LLMConfig):
        self.config = config
        self._model = None
        self._tokenizer = None
        self._initialized = False
    
    def is_available(self) -> bool:
        raise NotImplementedError
    
    def load_model(self) -> bool:
        raise NotImplementedError
    
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        raise NotImplementedError
    
    def embed(self, text: str) -> List[float]:
        raise NotImplementedError
    
    def get_token_count(self, text: str) -> int:
        return len(text.split())


class LlamaCppEngine(BaseLLMEngine):
    def is_available(self) -> bool:
        try:
            import llama_cpp
            return True
        except ImportError:
            return False
    
    def load_model(self) -> bool:
        if self._initialized:
            return True
        
        try:
            import llama_cpp
            
            model_path = self.config.model_path
            if not model_path:
                models_dir = get_config().models_dir
                model_name = self.config.model_name
                possible_paths = [
                    os.path.join(models_dir, f"{model_name}-q4_k_m.gguf"),
                    os.path.join(models_dir, f"{model_name}.gguf"),
                    os.path.join(models_dir, f"{model_name}-q4_0.gguf"),
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        model_path = path
                        break
            
            if not model_path or not os.path.exists(model_path):
                print(f"[LlamaCppEngine] Model not found: {model_path}")
                return False
            
            self._model = llama_cpp.Llama(
                model_path=model_path,
                n_ctx=self.config.context_window,
                n_threads=max(1, os.cpu_count() or 4),
                verbose=False,
            )
            self._initialized = True
            print(f"[LlamaCppEngine] Loaded model: {model_path}")
            return True
            
        except Exception as e:
            print(f"[LlamaCppEngine] Failed to load model: {e}")
            return False
    
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        import time
        
        if not self._initialized:
            if not self.load_model():
                return LLMResponse(
                    text="",
                    tokens_generated=0,
                    latency_ms=0,
                    model=self.config.model_name,
                    provider="llama_cpp",
                    success=False,
                    error="Model not loaded"
                )
        
        start_time = time.time()
        
        try:
            max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
            temperature = kwargs.get("temperature", self.config.temperature)
            top_p = kwargs.get("top_p", self.config.top_p)
            
            output = self._model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                echo=False,
            )
            
            text = output.get("choices", [{}])[0].get("text", "")
            tokens = output.get("usage", {}).get("completion_tokens", 0)
            latency = (time.time() - start_time) * 1000
            
            return LLMResponse(
                text=text.strip(),
                tokens_generated=tokens,
                latency_ms=latency,
                model=self.config.model_name,
                provider="llama_cpp",
                success=True
            )
            
        except Exception as e:
            return LLMResponse(
                text="",
                tokens_generated=0,
                latency_ms=(time.time() - start_time) * 1000,
                model=self.config.model_name,
                provider="llama_cpp",
                success=False,
                error=str(e)
            )


class TransformersEngine(BaseLLMEngine):
    def is_available(self) -> bool:
        try:
            import torch
            import transformers
            return True
        except ImportError:
            return False
    
    def load_model(self) -> bool:
        if self._initialized:
            return True
        
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            
            device = self.config.device
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            model_name = self.config.model_name
            
            if "/" not in model_name:
                model_map = {
                    "phi-2": "microsoft/phi-2",
                    "tinyllama": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                    "phi-3": "microsoft/Phi-3-mini-4k-instruct",
                }
                model_name = model_map.get(model_name, f"microsoft/{model_name}")
            
            print(f"[TransformersEngine] Loading {model_name} on {device}...")
            
            self._tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            
            load_kwargs = {"trust_remote_code": True}
            if device == "cuda" and self.config.use_gpu:
                load_kwargs["torch_dtype"] = torch.float16
                load_kwargs["device_map"] = "auto"
            else:
                load_kwargs["torch_dtype"] = torch.float32
            
            self._model = AutoModelForCausalLM.from_pretrained(model_name, **load_kwargs)
            
            if device == "cpu":
                self._model = self._model.to("cpu")
            
            self._device = device
            self._initialized = True
            print(f"[TransformersEngine] Loaded model: {model_name}")
            return True
            
        except Exception as e:
            print(f"[TransformersEngine] Failed to load model: {e}")
            return False
    
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        import time
        
        if not self._initialized:
            if not self.load_model():
                return LLMResponse(
                    text="",
                    tokens_generated=0,
                    latency_ms=0,
                    model=self.config.model_name,
                    provider="transformers",
                    success=False,
                    error="Model not loaded"
                )
        
        start_time = time.time()
        
        try:
            import torch
            
            max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
            temperature = kwargs.get("temperature", self.config.temperature)
            top_p = kwargs.get("top_p", self.config.top_p)
            
            inputs = self._tokenizer(prompt, return_tensors="pt")
            if hasattr(self, "_device") and self._device == "cuda":
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature if temperature > 0 else 1.0,
                    top_p=top_p,
                    do_sample=temperature > 0,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            
            generated = outputs[0][inputs["input_ids"].shape[1]:]
            text = self._tokenizer.decode(generated, skip_special_tokens=True)
            tokens = len(generated)
            latency = (time.time() - start_time) * 1000
            
            return LLMResponse(
                text=text.strip(),
                tokens_generated=tokens,
                latency_ms=latency,
                model=self.config.model_name,
                provider="transformers",
                success=True
            )
            
        except Exception as e:
            return LLMResponse(
                text="",
                tokens_generated=0,
                latency_ms=(time.time() - start_time) * 1000,
                model=self.config.model_name,
                provider="transformers",
                success=False,
                error=str(e)
            )


class HybridLLM:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[LLMConfig] = None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self.config = config or get_config().llm
        self._primary_engine: Optional[BaseLLMEngine] = None
        self._fallback_engine: Optional[BaseLLMEngine] = None
        self._initialized = False
    
    def initialize(self) -> bool:
        if self._initialized:
            return True
        
        provider = self.config.get_effective_provider()
        print(f"[HybridLLM] Effective provider: {provider.value}")
        
        if provider == LLMProvider.LLAMA_CPP:
            self._primary_engine = LlamaCppEngine(self.config)
            self._fallback_engine = TransformersEngine(self.config)
        else:
            self._primary_engine = TransformersEngine(self.config)
            self._fallback_engine = LlamaCppEngine(self.config)
        
        if self._primary_engine.is_available():
            if self._primary_engine.load_model():
                self._initialized = True
                return True
        
        if self._fallback_engine.is_available():
            if self._fallback_engine.load_model():
                self._primary_engine, self._fallback_engine = self._fallback_engine, self._primary_engine
                self._initialized = True
                return True
        
        print("[HybridLLM] No LLM engine available")
        return False
    
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        if not self._initialized:
            if not self.initialize():
                return LLMResponse(
                    text="",
                    tokens_generated=0,
                    latency_ms=0,
                    model="none",
                    provider="none",
                    success=False,
                    error="LLM not initialized"
                )
        
        response = self._primary_engine.generate(prompt, **kwargs)
        
        if not response.success and self._fallback_engine:
            print(f"[HybridLLM] Primary engine failed, trying fallback")
            response = self._fallback_engine.generate(prompt, **kwargs)
        
        return response
    
    def is_ready(self) -> bool:
        return self._initialized or self.initialize()
    
    def chat(self, message: str, system_prompt: str = None, history: List[Dict] = None) -> str:
        prompt_parts = []
        
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}")
        
        if history:
            for turn in history[-5:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role == "user":
                    prompt_parts.append(f"User: {content}")
                else:
                    prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append(f"User: {message}")
        prompt_parts.append("Assistant:")
        
        prompt = "\n".join(prompt_parts)
        
        response = self.generate(prompt, max_tokens=256, temperature=0.7)
        
        if response.success:
            return response.text
        else:
            return f"Error: {response.error}"


def get_llm() -> HybridLLM:
    return HybridLLM()


__all__ = [
    "LLMResponse",
    "BaseLLMEngine",
    "LlamaCppEngine",
    "TransformersEngine",
    "HybridLLM",
    "get_llm",
]
