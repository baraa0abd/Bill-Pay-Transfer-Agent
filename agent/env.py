"""Read KEY=VALUE lines from the untracked .env file. Variables already set in the shell win."""
import os
from pathlib import Path


def load_env(path=Path(__file__).resolve().parents[1] / '.env'):
    if not path.exists(): return
    for line in path.read_text(encoding='utf-8').splitlines():
        key, sep, value = line.strip().partition('=')
        if sep and key and not key.startswith('#'):
            os.environ.setdefault(key.strip(), value.strip().strip('"\''))
