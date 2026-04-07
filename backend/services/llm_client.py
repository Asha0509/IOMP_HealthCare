"""
Shared LLM client.
Primary: Groq (Llama)
Fallback: NVIDIA NIM (OpenAI-compatible endpoint)
"""

import json
import re
from typing import Any, Optional, Tuple

import httpx

from core.config import settings
from core.logging import app_logger


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
NVIDIA_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


def _strip_code_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            candidate = parts[1]
            if candidate.startswith("json"):
                candidate = candidate[4:]
            return candidate.strip()
    return text


def _extract_json_candidate(text: str) -> str:
    cleaned = _strip_code_fence(text)
    if cleaned.startswith("{") or cleaned.startswith("["):
        return cleaned

    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
    return match.group(1).strip() if match else cleaned


def has_any_provider() -> bool:
    return bool(settings.GROQ_API_KEY or settings.NVIDIA_NIM_API_KEY)


def _groq_generate(prompt: str, temperature: float, max_tokens: int) -> Optional[str]:
    if not settings.GROQ_API_KEY:
        return None

    try:
        response = httpx.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a strict clinical triage assistant that returns valid JSON when asked.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        app_logger.warning(f"Groq request failed: {exc}")
        return None


def _nim_generate(prompt: str, temperature: float, max_tokens: int) -> Optional[str]:
    if not settings.NVIDIA_NIM_API_KEY:
        return None

    try:
        response = httpx.post(
            NVIDIA_NIM_URL,
            headers={
                "Authorization": f"Bearer {settings.NVIDIA_NIM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.NVIDIA_NIM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a strict clinical triage assistant that returns valid JSON when asked.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        app_logger.warning(f"NVIDIA NIM request failed: {exc}")
        return None


def generate_text_with_fallback(
    prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 900,
) -> Tuple[Optional[str], Optional[str]]:
    """Return (text, provider) using Groq first then NVIDIA NIM."""
    groq_text = _groq_generate(prompt, temperature=temperature, max_tokens=max_tokens)
    if groq_text:
        return groq_text, "groq"

    nim_text = _nim_generate(prompt, temperature=temperature, max_tokens=max_tokens)
    if nim_text:
        return nim_text, "nvidia_nim"

    return None, None


def generate_json_with_fallback(
    prompt: str,
    default: Any,
    temperature: float = 0.2,
    max_tokens: int = 900,
) -> Tuple[Any, Optional[str]]:
    """Return (parsed_json, provider) using Groq first then NVIDIA NIM."""
    text, provider = generate_text_with_fallback(prompt, temperature=temperature, max_tokens=max_tokens)
    if not text:
        return default, None

    try:
        candidate = _extract_json_candidate(text)
        return json.loads(candidate), provider
    except Exception as exc:
        app_logger.warning(f"Failed to parse JSON from {provider}: {exc}")
        return default, provider
