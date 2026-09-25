"""Optional read-back interface. Speech cannot invoke confirmation."""
from typing import Protocol


class TTSClient(Protocol):
    def speak(self,text:str) -> bytes: ...
