"""
Alibaba DashScope / Qwen API runner for ZTF/ALeRCE benchmark (vision-language).

Mirrors the public surface of api_tinker.py / api_nvidia.py so the benchmark
runners can dispatch without touching evaluate.py or prompts.py.

DashScope OpenAI-compatible mode
(https://dashscope.aliyuncs.com/compatible-mode/v1) accepts Chat Completions
with vision via base64 ``image_url`` data URIs. Hybrid thinking models
(qwen3.5 / qwen3.6 / qwen3-vl-*) toggle CoT with ``extra_body.enable_thinking``;
optional ``thinking_budget`` caps the reasoning tokens.

Requires:
  - export QWEN_API_KEY=...   (or DASHSCOPE_API_KEY=...; put in .env)
  - pip install openai>=2.0

Default model: qwen3.5-397b-a17b. Override via env QWEN_MODEL or CLI ``--model``.
Base URL override via env QWEN_BASE_URL / DASHSCOPE_BASE_URL
(default Beijing ``https://dashscope.aliyuncs.com/compatible-mode/v1``;
 Singapore intl: ``https://dashscope-intl.aliyuncs.com/compatible-mode/v1``).

Reasoning controls (shared ``reasoning_effort`` knob):
  - 'none'    -> enable_thinking=False
  - 'minimal' -> enable_thinking=True, thinking_budget=2048
  - 'low'     -> enable_thinking=True, thinking_budget=4096
  - 'medium'  -> enable_thinking=True, thinking_budget=8192
  - 'high'    -> enable_thinking=True  (no budget -> unbounded)
  - 'xhigh'   -> alias of 'high'
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

DEFAULT_MODEL = os.environ.get("QWEN_MODEL", "qwen3.5-397b-a17b")
DEFAULT_REASONING_EFFORT = os.environ.get("QWEN_REASONING_EFFORT", "high")
# Default to the international (Singapore) endpoint — many non-CN keys only
# authenticate there. Override with QWEN_BASE_URL for Beijing:
#   https://dashscope.aliyuncs.com/compatible-mode/v1
DEFAULT_BASE_URL = os.environ.get(
    "QWEN_BASE_URL",
    os.environ.get(
        "DASHSCOPE_BASE_URL",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    ),
)
DEFAULT_MAX_RETRIES = int(os.environ.get("QWEN_MAX_RETRIES", "8"))

# HF / Tinker ids -> DashScope OpenAI-compatible model ids.
_MODEL_ALIASES: dict[str, str] = {
    "Qwen/Qwen3.5-397B-A17B": "qwen3.5-397b-a17b",
    "Qwen/Qwen3.5-35B-A3B": "qwen3.5-35b-a3b",
    "Qwen/Qwen3.6-35B-A3B": "qwen3.6-35b-a3b",
    "Qwen/Qwen3.5-4B": "qwen3.5-4b",
    "Qwen/Qwen3-VL-30B-A3B-Instruct": "qwen3-vl-30b-a3b-instruct",
    "Qwen/Qwen3-VL-235B-A22B-Instruct": "qwen3-vl-235b-a22b-instruct",
    "Qwen/Qwen3-VL-235B-A22B-Thinking": "qwen3-vl-235b-a22b-thinking",
}

_VALID_EFFORT = {"none", "minimal", "low", "medium", "high", "xhigh"}
_EFFORT_THINKING_BUDGET: dict[str, int | None] = {
    "minimal": 2048,
    "low": 4096,
    "medium": 8192,
    "high": None,
    "xhigh": None,
}


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
    key = os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError(
            "QWEN_API_KEY (or DASHSCOPE_API_KEY) not set. Add it to .env or export it "
            "(Alibaba Cloud Model Studio / DashScope console)."
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
    Run one VLM completion via the DashScope / Qwen Chat Completions API.

    Returns the same dict shape as the other backends so evaluate.py is unchanged.
    Visible answer is ``message.content``; CoT (if any) is excluded from ``raw_text``.
    """
    client = _get_client()
    effort = _normalize_effort(reasoning_effort)
    model = _resolve_model(model_name)
    msgs = _ensure_system_prompt(messages, system_prompt)
    thinking_on = effort != "none"

    effective_max = max_tokens
    if thinking_on and effective_max <= 4096:
        effective_max = 20000

    extra_body: dict[str, Any] = {"enable_thinking": thinking_on}
    if thinking_on:
        budget = _EFFORT_THINKING_BUDGET.get(effort)
        if budget is not None:
            extra_body["thinking_budget"] = budget

    resp = client.chat.completions.create(
        model=model,
        messages=msgs,
        max_tokens=effective_max,
        temperature=temperature,
        stream=False,
        extra_body=extra_body,
    )

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
    """Build metadata from manifest row, load montage, call Qwen vision model."""
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
