"""Local Ollama structured output transport. No wallet tools are exposed."""
import os
import httpx


class OllamaClient:
    source = 'ollama'

    def __init__(self, model=None, client=None):
        self.model = model or os.getenv('OLLAMA_MODEL', 'qwen3.5:4b')
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
        self.client = client

    def generate(self, prompt, schema, system=None, max_tokens=2048):
        messages = ([{'role': 'system', 'content': system}] if system else [])
        messages.append({'role': 'user', 'content': prompt})
        payload = dict(model=self.model, messages=messages, stream=False, think=False,
                       format=schema.model_json_schema(),
                       options={'temperature': 0, 'num_ctx': 16384, 'num_predict': max_tokens})
        if self.client is not None:
            response = self.client.post(self.base_url + '/api/chat', json=payload)
        else:
            with httpx.Client(timeout=float(os.getenv('OLLAMA_TIMEOUT', '300')), trust_env=False) as client:
                response = client.post(self.base_url + '/api/chat', json=payload)
        response.raise_for_status()
        result = response.json()
        if not result.get('done') or result.get('done_reason') == 'length':
            raise ValueError('Ollama generation incomplete')
        return schema.model_validate_json(result['message']['content'])

    def parse(self, text):
        from .parser import IntentList, SYSTEM, check_spans
        return check_spans(self.generate(text, IntentList, SYSTEM).intents, text)
