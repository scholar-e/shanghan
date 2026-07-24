"""AI provider configuration for chat completion backends."""

import json
import os
from copy import deepcopy


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "data", "ai_config.json")

DEFAULT_CONFIG = {
    "active_provider": "deepseek",
    "providers": {
        "deepseek": {
            "label": "DeepSeek",
            "api_key": "",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
        },
        "claude": {
            "label": "Claude",
            "api_key": "",
            "base_url": "https://api.anthropic.com",
            "model": "claude-sonnet-5",
        },
    },
}


def _masked(value):
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def _env_key(provider):
    if provider == "deepseek":
        return os.environ.get("DEEPSEEK_API_KEY", "")
    if provider == "claude":
        return os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    return ""


def load_ai_config(include_secrets=True):
    config = deepcopy(DEFAULT_CONFIG)
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        config["active_provider"] = saved.get("active_provider", config["active_provider"])
        for provider, provider_config in saved.get("providers", {}).items():
            if provider in config["providers"]:
                config["providers"][provider].update(provider_config)

    for provider, provider_config in config["providers"].items():
        if not provider_config.get("api_key"):
            provider_config["api_key"] = _env_key(provider)

    if not include_secrets:
        safe = deepcopy(config)
        for provider_config in safe["providers"].values():
            api_key = provider_config.get("api_key", "")
            provider_config["api_key_configured"] = bool(api_key)
            provider_config["api_key_masked"] = _masked(api_key)
            provider_config.pop("api_key", None)
        return safe

    return config


def save_ai_config(payload):
    current = deepcopy(DEFAULT_CONFIG)
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        current["active_provider"] = saved.get("active_provider", current["active_provider"])
        for provider, provider_config in saved.get("providers", {}).items():
            if provider in current["providers"]:
                current["providers"][provider].update(provider_config)
    active_provider = payload.get("active_provider")
    if active_provider in current["providers"]:
        current["active_provider"] = active_provider

    for provider, updates in payload.get("providers", {}).items():
        if provider not in current["providers"]:
            continue
        for field in ["base_url", "model"]:
            if updates.get(field):
                current["providers"][provider][field] = updates[field].strip()
        if updates.get("api_key"):
            current["providers"][provider]["api_key"] = updates["api_key"].strip()

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass
    return load_ai_config(include_secrets=False)


def get_active_ai_provider():
    config = load_ai_config(include_secrets=True)
    provider = config.get("active_provider", "deepseek")
    provider_config = config["providers"].get(provider, config["providers"]["deepseek"])
    return provider, provider_config
