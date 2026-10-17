"""Free hosted models through the OpenAI-compatible chat API (Groq, Gemini). No wallet tools are exposed."""
import os
import time
import httpx

# provider -> (base URL, key variable, default model). Free tiers per the challenge's LLM access guide.
PROVIDERS = {
    'groq': ('https://api.groq.com/openai/v1', 'GROQ_API_KEY', 'openai/gpt-oss-120b'),
    'gemini': ('https://generativelanguage.googleapis.com/v1beta/openai', 'GEMINI_API_KEY', 'gemini-3.8-flash'),
}


def strict_schema(model):
    """Strict mode wants every property required and no extra properties; optional fields stay nullable."""
    schema = model.model_json_schema()
    def walk(value):
        if isinstance(value, dict):
            value.pop('default', None)
            if value.get('type') == 'object':
                value['required'] = list(value.get('properties', {})); value['additionalProperties'] = False
            for child in value.values(): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
    walk(schema)
    return schema


class HostedClient:
    def __init__(self, provider, model=None, client=None, sleep=time.sleep):
        base, key_var, default = PROVIDERS[provider]
        self.source, self.base, self.model = provider, base, model or os.getenv('LLM_MODEL') or default
        self.key = os.environ.get(key_var) if client is None else 'test'
        if not self.key: raise ValueError(f'Set {key_var} to use LLM_PROVIDER={provider}')
        self.client, self.sleep = client or httpx.Client(timeout=60), sleep

    def generate(self, prompt, schema, system=None, max_tokens=2048):
        messages = ([{'role': 'system', 'content': system}] if system else []) + [{'role': 'user', 'content': prompt}]
        body = dict(model=self.model, messages=messages, temperature=0, max_tokens=max_tokens,
                    response_format={'type': 'json_schema', 'json_schema':
                                     {'name': schema.__name__, 'strict': True, 'schema': strict_schema(schema)}})
        for attempt in range(4):
            r = self.client.post(self.base + '/chat/completions', json=body, headers={'Authorization': f'Bearer {self.key}'})
            if r.status_code != 429: break
            # Free tiers rate-limit: wait as told (or back off) and retry.
            self.sleep(float(r.headers.get('retry-after') or 2 ** attempt))
        r.raise_for_status()
        choice = r.json()['choices'][0]
        if choice.get('finish_reason') not in (None, 'stop'): raise ValueError(f"generation incomplete: {choice.get('finish_reason')}")
        return schema.model_validate_json(choice['message']['content'])

    def parse(self, text):
        from .parser import IntentList, SYSTEM, check_spans
        return check_spans(self.generate(text, IntentList, SYSTEM).intents, text)
