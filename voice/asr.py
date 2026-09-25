"""Pluggable speech-to-text. Unknown confidence always requires text review."""
import os
from dataclasses import dataclass,field
from typing import Protocol
import httpx


@dataclass
class Transcript:
    text: str
    confidence: int | None = None
    uncertain_tokens: list[str] = field(default_factory=list)


class ASRClient(Protocol):
    def transcribe(self,audio:bytes,filename:str,content_type:str) -> Transcript: ...


class WhisperClient:
    def __init__(self,key=None,model=None,transport=None):
        self.key=key or os.getenv('ASR_API_KEY')
        self.model=model or os.getenv('ASR_MODEL','whisper-1')
        self.transport=transport or httpx.Client(timeout=45)

    def transcribe(self,audio,filename,content_type):
        if not self.key: raise ValueError('ASR_UNAVAILABLE')
        r=self.transport.post('https://api.openai.com/v1/audio/transcriptions',
            headers={'Authorization':f'Bearer {self.key}'},
            files={'file':(filename,audio,content_type)},
            data={'model':self.model,'language':'ar','response_format':'json'})
        r.raise_for_status()
        text=r.json()['text']
        if not isinstance(text,str) or not text.strip() or len(text)>4000: raise ValueError('ASR_INVALID')
        # Hosted Whisper JSON has no calibrated token confidence: never invent it.
        return Transcript(text=text,confidence=None)


class MockASR:
    def __init__(self,text,confidence=100,uncertain_tokens=None):
        self.result=Transcript(text,confidence,uncertain_tokens or [])

    def transcribe(self,audio,filename,content_type): return self.result
