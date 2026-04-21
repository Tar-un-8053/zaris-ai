import io
import os
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

from backend.core.config import get_config, VoiceConfig


@dataclass
class STTResult:
    text: str
    language: str
    confidence: float
    latency_ms: float
    segments: List[dict]
    success: bool = True
    error: Optional[str] = None


class BaseSTTEngine:
    def __init__(self, config: VoiceConfig):
        self.config = config
        self._model = None
        self._initialized = False
    
    def is_available(self) -> bool:
        raise NotImplementedError
    
    def load_model(self) -> bool:
        raise NotImplementedError
    
    def transcribe(self, audio_data: Union[bytes, str], **kwargs) -> STTResult:
        raise NotImplementedError


class FasterWhisperEngine(BaseSTTEngine):
    def is_available(self) -> bool:
        try:
            import faster_whisper
            return True
        except ImportError:
            return False
    
    def load_model(self) -> bool:
        if self._initialized:
            return True
        
        try:
            from faster_whisper import WhisperModel
            
            model_size = self.config.stt_model
            device = self.config.stt_device
            
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"
            
            compute_type = "float16" if device == "cuda" else "int8"
            
            self._model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
            )
            self._device = device
            self._initialized = True
            print(f"[FasterWhisperEngine] Loaded model: {model_size} on {device}")
            return True
            
        except Exception as e:
            print(f"[FasterWhisperEngine] Failed to load: {e}")
            return False
    
    def transcribe(self, audio_data: Union[bytes, str], **kwargs) -> STTResult:
        import time
        
        if not self._initialized:
            if not self.load_model():
                return STTResult(
                    text="",
                    language="",
                    confidence=0.0,
                    latency_ms=0,
                    segments=[],
                    success=False,
                    error="Model not loaded"
                )
        
        start_time = time.time()
        
        try:
            languages = kwargs.get("languages", ["en", "hi"])
            
            if isinstance(audio_data, bytes):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(audio_data)
                    temp_path = f.name
                audio_path = temp_path
            else:
                audio_path = audio_data
            
            segments_list = []
            all_text = []
            detected_lang = "en"
            
            for lang in languages:
                segments, info = self._model.transcribe(
                    audio_path,
                    language=lang,
                    beam_size=5,
                    vad_filter=True,
                )
                
                segments_list = list(segments)
                if segments_list:
                    detected_lang = info.language
                    all_text = [s.text for s in segments_list]
                    break
            
            if isinstance(audio_data, bytes):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            text = " ".join(all_text).strip()
            latency = (time.time() - start_time) * 1000
            
            segments_data = [
                {
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "avg_logprob": getattr(s, "avg_logprob", 0),
                }
                for s in segments_list
            ]
            
            avg_confidence = 0.85
            if segments_data:
                probs = [s.get("avg_logprob", 0) for s in segments_data]
                avg_confidence = min(1.0, max(0.0, sum(probs) / len(probs) + 1))
            
            return STTResult(
                text=text,
                language=detected_lang,
                confidence=avg_confidence,
                latency_ms=latency,
                segments=segments_data,
                success=True
            )
            
        except Exception as e:
            return STTResult(
                text="",
                language="",
                confidence=0.0,
                latency_ms=(time.time() - start_time) * 1000,
                segments=[],
                success=False,
                error=str(e)
            )


class WhisperCppEngine(BaseSTTEngine):
    def is_available(self) -> bool:
        try:
            import whisper_cpp
            return True
        except ImportError:
            try:
                from whisper_cpp import Whisper
                return True
            except ImportError:
                return False
    
    def load_model(self) -> bool:
        if self._initialized:
            return True
        
        try:
            config = get_config()
            models_dir = config.models_dir
            model_name = self.config.stt_model
            
            model_path = os.path.join(models_dir, f"ggml-{model_name}.bin")
            if not os.path.exists(model_path):
                model_path = os.path.join(models_dir, f"whisper-{model_name}.bin")
            
            if not os.path.exists(model_path):
                print(f"[WhisperCppEngine] Model not found: {model_path}")
                return False
            
            try:
                from whisper_cpp import Whisper
                self._model = Whisper(model_path)
            except ImportError:
                import whisper_cpp
                self._model = whisper_cpp.Whisper(model_path)
            
            self._initialized = True
            print(f"[WhisperCppEngine] Loaded model: {model_path}")
            return True
            
        except Exception as e:
            print(f"[WhisperCppEngine] Failed to load: {e}")
            return False
    
    def transcribe(self, audio_data: Union[bytes, str], **kwargs) -> STTResult:
        import time
        
        if not self._initialized:
            if not self.load_model():
                return STTResult(
                    text="",
                    language="",
                    confidence=0.0,
                    latency_ms=0,
                    segments=[],
                    success=False,
                    error="Model not loaded"
                )
        
        start_time = time.time()
        
        try:
            languages = kwargs.get("languages", ["en"])
            lang = languages[0] if languages else "en"
            
            if isinstance(audio_data, bytes):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(audio_data)
                    temp_path = f.name
                audio_path = temp_path
            else:
                audio_path = audio_data
            
            result = self._model.transcribe(audio_path, language=lang)
            
            if isinstance(audio_data, bytes):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            text = result.get("text", "") if isinstance(result, dict) else str(result)
            latency = (time.time() - start_time) * 1000
            
            return STTResult(
                text=text.strip(),
                language=lang,
                confidence=0.85,
                latency_ms=latency,
                segments=[],
                success=True
            )
            
        except Exception as e:
            return STTResult(
                text="",
                language="",
                confidence=0.0,
                latency_ms=(time.time() - start_time) * 1000,
                segments=[],
                success=False,
                error=str(e)
            )


class SpeechRecognitionEngine(BaseSTTEngine):
    def is_available(self) -> bool:
        try:
            import speech_recognition
            return True
        except ImportError:
            return False
    
    def load_model(self) -> bool:
        if self._initialized:
            return True
        
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._initialized = True
            print("[SpeechRecognitionEngine] Initialized (Google Speech API)")
            return True
        except Exception as e:
            print(f"[SpeechRecognitionEngine] Failed: {e}")
            return False
    
    def transcribe(self, audio_data: Union[bytes, str], **kwargs) -> STTResult:
        import time
        import speech_recognition as sr
        
        if not self._initialized:
            self.load_model()
        
        start_time = time.time()
        
        try:
            if isinstance(audio_data, bytes):
                audio = sr.AudioData(audio_data, sample_rate=16000, sample_width=2)
            else:
                with sr.AudioFile(audio_data) as source:
                    audio = self._recognizer.record(source)
            
            languages = kwargs.get("languages", ["en-US", "hi-IN"])
            
            try:
                text = self._recognizer.recognize_google(audio, language=languages[0])
            except sr.UnknownValueError:
                if len(languages) > 1:
                    try:
                        text = self._recognizer.recognize_google(audio, language=languages[1])
                    except:
                        text = ""
                else:
                    text = ""
            
            latency = (time.time() - start_time) * 1000
            
            return STTResult(
                text=text.strip(),
                language=languages[0][:2],
                confidence=0.8,
                latency_ms=latency,
                segments=[],
                success=bool(text)
            )
            
        except Exception as e:
            return STTResult(
                text="",
                language="",
                confidence=0.0,
                latency_ms=(time.time() - start_time) * 1000,
                segments=[],
                success=False,
                error=str(e)
            )


class HybridSTT:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[VoiceConfig] = None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self.config = config or get_config().voice
        self._primary_engine: Optional[BaseSTTEngine] = None
        self._fallback_engine: Optional[BaseSTTEngine] = None
        self._initialized = False
    
    def initialize(self) -> bool:
        if self._initialized:
            return True
        
        engine_type = self.config.stt_engine.lower()
        
        engines = []
        if engine_type == "whisper" or engine_type == "auto":
            engines.append(("faster_whisper", FasterWhisperEngine(self.config)))
            engines.append(("whisper_cpp", WhisperCppEngine(self.config)))
        if engine_type == "speech_recognition" or engine_type == "auto":
            engines.append(("speech_recognition", SpeechRecognitionEngine(self.config)))
        
        for name, engine in engines:
            if engine.is_available():
                if engine.load_model():
                    if self._primary_engine is None:
                        self._primary_engine = engine
                        print(f"[HybridSTT] Primary engine: {name}")
                    elif self._fallback_engine is None:
                        self._fallback_engine = engine
                        print(f"[HybridSTT] Fallback engine: {name}")
        
        if self._primary_engine:
            self._initialized = True
            return True
        
        self._primary_engine = SpeechRecognitionEngine(self.config)
        self._primary_engine.load_model()
        self._initialized = True
        return True
    
    def transcribe(self, audio_data: Union[bytes, str], **kwargs) -> STTResult:
        if not self._initialized:
            if not self.initialize():
                return STTResult(
                    text="",
                    language="",
                    confidence=0.0,
                    latency_ms=0,
                    segments=[],
                    success=False,
                    error="STT not initialized"
                )
        
        result = self._primary_engine.transcribe(audio_data, **kwargs)
        
        if not result.success and self._fallback_engine:
            print(f"[HybridSTT] Primary failed, trying fallback")
            result = self._fallback_engine.transcribe(audio_data, **kwargs)
        
        return result
    
    def transcribe_file(self, file_path: str, **kwargs) -> STTResult:
        return self.transcribe(file_path, **kwargs)
    
    def is_ready(self) -> bool:
        return self._initialized or self.initialize()


def get_stt() -> HybridSTT:
    return HybridSTT()


__all__ = [
    "STTResult",
    "BaseSTTEngine",
    "FasterWhisperEngine",
    "WhisperCppEngine",
    "SpeechRecognitionEngine",
    "HybridSTT",
    "get_stt",
]
