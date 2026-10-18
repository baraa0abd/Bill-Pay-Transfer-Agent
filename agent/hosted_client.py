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
    def __init__(self, provider, model=None, client=None, sleep=time.sleep, max_wait=None):
        # max_wait: seconds a user may wait (the app passes 3); None = patient, for evaluation and data generation.
        self.max_wait = max_wait
        base, key_var, default = PROVIDERS[provider]
        self.source, self.base, self.model = provider, base, model or os.getenv('LLM_MODEL') or default
        self.key = os.environ.get(key_var) if client is None else 'test'
        if not self.key: raise ValueError(f'Set {key_var} to use LLM_PROVIDER={provider}')
        self.client, self.sleep = client or httpx.Client(timeout=max_wait or 60), sleep

    def generate(self, prompt, schema, system=None, max_tokens=2048, effort=None):
        messages = ([{'role': 'system', 'content': system}] if system else []) + [{'role': 'user', 'content': prompt}]
        body = dict(model=self.model, messages=messages, temperature=0, max_tokens=max_tokens,
                    response_format={'type': 'json_schema', 'json_schema':
                                     {'name': schema.__name__, 'strict': True, 'schema': strict_schema(schema)}})
        if effort and 'gpt-oss' in self.model: body['reasoning_effort'] = effort
        start = time.monotonic()
        for attempt in range(4 if self.max_wait is not None else 8):
            r = self.client.post(self.base + '/chat/completions', json=body, headers={'Authorization': f'Bearer {self.key}'})
            # 429: free-tier rate limit. 400/5xx: strict-mode generations occasionally fail and succeed on retry.
            if r.status_code not in (429, 400, 500, 502, 503): break
            wait = min(60.0, float(r.headers.get('retry-after') or 2 ** attempt))
            if self.max_wait is not None and time.monotonic() - start + wait > self.max_wait:
                raise ValueError(f'{self.source} busy ({r.status_code}); not making the user wait {wait:.0f}s')
            self.sleep(wait)
        if r.status_code >= 400: raise ValueError(f'{self.source} {r.status_code}: {r.text[:300]}')
        choice = r.json()['choices'][0]
        if choice.get('finish_reason') not in (None, 'stop'): raise ValueError(f"generation incomplete: {choice.get('finish_reason')}")
        return schema.model_validate_json(choice['message']['content'])

    def parse(self, text):
        from .parser import IntentList, SYSTEM, check_spans
        # Extracting who/what/how much needs little reasoning: low effort keeps the same answers with ~60% fewer
        # reasoning tokens (measured: 318 -> 129), i.e. faster replies and more requests per free-tier minute.
        return check_spans(self.generate(text, IntentList, SYSTEM, max_tokens=1024, effort='low').intents, text)
