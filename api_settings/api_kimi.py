"""
Moonshot / Kimi API runner for ZTF/ALeRCE benchmark (vision-language).

Mirrors the public surface of api_tinker.py / api_nvidia.py so the benchmark
runners can dispatch without touching evaluate.py or prompts.py.

Moonshot (https://api.moonshot.ai/v1) implements the OpenAI *Chat Completions*
API. Vision inputs use a base64 ``image_url`` data URI (URL-form images are
NOT supported). Thinking for ``kimi-k2.5`` / ``kimi-k2.6`` is toggled with
``extra_body.thinking.type`` ∈ {enabled, disabled}; ``kimi-k3`` uses the
top-level ``reasoning_effort`` field instead.

Requires:
  - export KIMI_API_KEY=...   (or MOONSHOT_API_KEY=...; put in .env)
  - pip install openai>=2.0

Default model: kimi-k2.6. Override via env KIMI_MODEL or CLI ``--model``.
Base URL override via env KIMI_BASE_URL / MOONSHOT_BASE_URL
(default ``https://api.moonshot.ai/v1``; China: ``https://api.moonshot.cn/v1``).

Reasoning controls (shared ``reasoning_effort`` knob):
  - 'none'                         -> thinking.type=disabled  (k2.5/k2.6)
  - 'minimal'|'low'|'medium'|'high' -> thinking.type=enabled
  - 'xhigh'                        -> alias of 'high'
  For ``kimi-k3`` (always-thinking), 'none' is rejected; the rest map to
  Moonshot's top-level reasoning_effort ∈ {low, high, max} (high/xhigh -> max).

Temperature note (Moonshot docs):
  When thinking is enabled on k2.5/k2.6, ``temperature`` is not modifiable —
  we omit it from the request. When thinking is disabled we forward the
  caller's temperature (Moonshot recommends 0.6 for non-thinking).
"""
from __future__ import annotations

import base64
import os
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from openai import OpenAI

from prompts import STAMPS_LLM_DIRNAME, SYSTEM_PROMPT, build_user_prompt, manifest_row_to_metadata

DEFAULT_MODEL = os.environ.get("KIMI_MODEL", "kimi-k2.6")
DEFAULT_REASONING_EFFORT = os.environ.get("KIMI_REASONING_EFFORT", "high")
DEFAULT_BASE_URL = os.environ.get(
    "KIMI_BASE_URL",
    os.environ.get("MOONSHOT_BASE_URL", "https://api.moonshot.ai/v1"),
)
DEFAULT_MAX_RETRIES = int(os.environ.get("KIMI_MAX_RETRIES", "8"))

# HF / Tinker ids -> Moonshot API model ids (so existing CLI flags keep working).
_MODEL_ALIASES: dict[str, str] = {
    "moonshotai/Kimi-K2.6": "kimi-k2.6",
    "moonshotai/Kimi-K2.5": "kimi-k2.5",
    "moonshotai/Kimi-K2": "kimi-k2",
    "Kimi-K2.6": "kimi-k2.6",
    "Kimi-K2.5": "kimi-k2.5",
}

_VALID_EFFORT = {"none", "minimal", "low", "medium", "high", "xhigh"}


def montage_path(target_class: str, oid: str, root: Path | None = None) -> Path:
    base = root or ROOT
    return base / STAMPS_LLM_DIRNAME / target_class / oid / "montage.png"


def _encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _encode_pil(img: Any) -> str:
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def build_messages(
    oid: str,
    target_class: str,
    metadata: dict[str, Any],
    image_path: Path,
    system_prompt: str | None = None,
    extra_images: list | None = None,
) -> list[dict[str, Any]]:
    """Construct a Chat Completions ``messages`` list with image(s) + text."""
    user_text = build_user_prompt(oid, metadata)
    content: list[dict[str, Any]] = [
        {"type": "image_url", "image_url": {"url": _encode_image(image_path)}},
    ]
    for extra in extra_images or []:
        content.append(
            {"type": "image_url", "image_url": {"url": _encode_pil(extra)}}
        )
    content.append({"type": "text", "text": user_text})
    return [
        {"role": "system", "content": system_prompt if system_prompt is not None else SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def _resolve_extra_images(oid: str, metadata: dict[str, Any]) -> list:
    hook = globals().get("extra_images")
    if not callable(hook):
        return []
    try:
        return list(hook(oid, metadata) or [])
    except Exception:
        return []


_client_cache: dict[str, OpenAI] = {}
_client_lock = threading.Lock()


def _resolve_api_key() -> str:
    key = os.environ.get("KIMI_API_KEY") or os.environ.get("MOONSHOT_API_KEY")
    if not key:
        raise RuntimeError(
            "KIMI_API_KEY (or MOONSHOT_API_KEY) not set. Add it to .env or export it "
            "(https://platform.moonshot.ai / https://platform.kimi.ai)."
        )
    return key


def _get_client() -> OpenAI:
    with _client_lock:
        client = _client_cache.get("default")
        if client is None:
            client = OpenAI(
                api_key=_resolve_api_key(),
                base_url=DEFAULT_BASE_URL,
                max_retries=DEFAULT_MAX_RETRIES,
            )
            _client_cache["default"] = client
        return client


def _normalize_effort(effort: str | None) -> str:
    e = (effort or DEFAULT_REASONING_EFFORT or "none").lower()
    if e not in _VALID_EFFORT:
        raise ValueError(
            f"Invalid reasoning_effort {effort!r}. Must be one of {sorted(_VALID_EFFORT)}."
        )
    return e


def _resolve_model(model_name: str) -> str:
    return _MODEL_ALIASES.get(model_name, model_name)


def _is_k3(model_name: str) -> bool:
    return "kimi-k3" in model_name.lower() or model_name.lower().startswith("kimi-k3")


def _ensure_system_prompt(
    messages: list[dict[str, Any]], system_prompt: str | None
) -> list[dict[str, Any]]:
    if system_prompt is None:
        return messages
    if messages and messages[0].get("role") == "system":
        return messages
    return [{"role": "system", "content": system_prompt}, *messages]


def sample_vlm(
    messages: list[dict[str, Any]],
    model_name: str = DEFAULT_MODEL,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    reasoning_effort: str | None = None,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """
    Run one VLM completion via the Moonshot / Kimi Chat Completions API.

    Returns the same dict shape as the other backends so evaluate.py is unchanged.
    Visible answer is ``message.content``; CoT (if any) lives in
    ``message.reasoning_content`` and is excluded from ``raw_text``.
    """
    client = _get_client()
    effort = _normalize_effort(reasoning_effort)
    model = _resolve_model(model_name)
    msgs = _ensure_system_prompt(messages, system_prompt)
    thinking_on = effort != "none"

    effective_max = max_tokens
    if thinking_on and effective_max <= 4096:
        # Moonshot recommends max_tokens >= 16000 when reasoning_content is returned.
        effective_max = 32000

    create_kwargs: dict[str, Any] = {
        "model": model,
        "messages": msgs,
        "max_tokens": effective_max,
        "stream": False,
    }

    if _is_k3(model):
        if not thinking_on:
            raise ValueError(
                f"Model {model!r} is always-thinking; reasoning_effort='none' is not supported. "
                "Use 'low', 'high', or 'xhigh' (maps to Moonshot reasoning_effort)."
            )
        # Moonshot k3: low / high / max
        k3_effort = {"low": "low", "minimal": "low", "medium": "high",
                     "high": "max", "xhigh": "max"}[effort]
        create_kwargs["reasoning_effort"] = k3_effort
        # k3 docs: do not set temperature
    else:
        # k2.5 / k2.6 (and similar): thinking.type enabled|disabled
        create_kwargs["extra_body"] = {
            "thinking": {"type": "enabled" if thinking_on else "disabled"},
        }
        if thinking_on:
            # temperature is not modifiable in thinking mode — omit it
            pass
        else:
            # Moonshot k2.5/k2.6 non-thinking: only temperature=0.6 is allowed.
            create_kwargs["temperature"] = 0.6

    resp = client.chat.completions.create(**create_kwargs)

    choice = resp.choices[0] if resp.choices else None
    message = getattr(choice, "message", None) if choice else None
    raw_text = (getattr(message, "content", None) or "").strip() if message else ""

    usage = getattr(resp, "usage", None)
    n_prompt = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
    n_output = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
    n_reasoning = 0
    details = getattr(usage, "completion_tokens_details", None) if usage else None
    if details is not None:
        n_reasoning = int(getattr(details, "reasoning_tokens", 0) or 0)
    # Fallback: some Moonshot responses omit details; estimate from reasoning_content length.
    if n_reasoning == 0 and message is not None:
        rc = getattr(message, "reasoning_content", None)
        if rc:
            # rough; keep 0 if we cannot measure — answer_tokens stays == output
            pass
    n_answer = max(0, n_output - n_reasoning)

    finish_reason = getattr(choice, "finish_reason", None) or "stop" if choice else "stop"
    truncated = finish_reason == "length"

    return {
        "raw_text": raw_text,
        "answer_text": raw_text,
        "n_output_tokens": n_output,
        "n_answer_tokens": n_answer,
        "n_reasoning_tokens": n_reasoning,
        "n_prompt_tokens": n_prompt,
        "max_tokens": effective_max,
        "truncated": truncated,
        "finish_reason": finish_reason,
        "reasoning_effort": effort,
    }


def run_one(
    oid: str,
    target_class: str,
    row: Any,
    stamps_root: Path | None = None,
    model_name: str = DEFAULT_MODEL,
    reasoning_effort: str | None = None,
) -> dict[str, Any]:
    """Build metadata from manifest row, load montage, call Kimi vision model."""
    meta = manifest_row_to_metadata(row)
    img = montage_path(target_class, oid, stamps_root)
    if not img.is_file():
        raise FileNotFoundError(f"Missing montage: {img}")
    extras = _resolve_extra_images(oid, meta)
    messages = build_messages(oid, target_class, meta, img, extra_images=extras)
    vlm_out = sample_vlm(messages, model_name=model_name, reasoning_effort=reasoning_effort)
    return {
        "oid": oid,
        "target_class": target_class,
        "montage_path": str(img),
        "raw_text": vlm_out["raw_text"],
        "answer_text": vlm_out["answer_text"],
        "n_output_tokens": vlm_out["n_output_tokens"],
        "n_answer_tokens": vlm_out["n_answer_tokens"],
        "n_reasoning_tokens": vlm_out["n_reasoning_tokens"],
        "n_prompt_tokens": vlm_out["n_prompt_tokens"],
        "max_tokens": vlm_out["max_tokens"],
        "truncated": vlm_out["truncated"],
        "finish_reason": vlm_out["finish_reason"],
        "reasoning_effort": vlm_out["reasoning_effort"],
        "model": _resolve_model(model_name),
    }
