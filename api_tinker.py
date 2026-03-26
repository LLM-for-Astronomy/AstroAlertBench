"""
Tinker API runner for ZTF/ALeRCE benchmark (vision-language, zero-shot).

Pipeline (cf. AstroAlertBench Figure 2):
  (1) First-alert inputs: image triplet (here: one PNG montage = Science|Template|Difference) + metadata
  (2) Prompt construction: system + user from prompts.py
  (3) VLM response -> parse JSON (evaluate.py)

Requires:
  - export TINKER_API_KEY=...  (https://tinker-console.thinkingmachines.ai/)
  - pip install tinker tinker-cookbook transformers torch  (see requirements.txt)

Default vision model: moonshotai/Kimi-K2.5 (zero-shot; override via TINKER_MODEL or --model).

Renderer routing (tinker-cookbook): Kimi K2.5 → KimiK25DisableThinkingRenderer (structured JSON);
Qwen3.5* → Qwen3_5Renderer; Qwen3-VL* → Qwen3VLInstructRenderer. Llama Vision is not wired here.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import tinker
from tinker.types import SamplingParams

DEFAULT_MODEL = os.environ.get("TINKER_MODEL", "moonshotai/Kimi-K2.5")

from prompts import SYSTEM_PROMPT, build_user_prompt, manifest_row_to_metadata


def montage_path(target_class: str, oid: str, root: Path | None = None) -> Path:
    base = root or ROOT
    return base / "stamps_llm" / target_class / oid / "montage.png"


def build_messages(
    oid: str,
    target_class: str,
    metadata: dict[str, Any],
    image_path: Path,
) -> list[dict[str, Any]]:
    """User message = one image (montage) + text; system = SYSTEM_PROMPT."""
    from PIL import Image

    user_text = build_user_prompt(oid, metadata)
    img = Image.open(image_path).convert("RGB")
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image", "image": img},
                {"type": "text", "text": user_text},
            ],
        },
    ]


def get_renderer(model_name: str, tokenizer: Any, image_processor: Any) -> Any:
    """
    Return a tinker-cookbook renderer for the given HF model id.
    Kimi K2.5 uses thinking-disabled mode so assistant output is direct JSON-friendly text.
    """
    mn = model_name.lower()
    if "kimi" in mn and "k2.5" in mn:
        from tinker_cookbook.renderers.kimi_k25 import KimiK25DisableThinkingRenderer

        return KimiK25DisableThinkingRenderer(tokenizer, image_processor)
    if "qwen3.5" in mn or "qwen3-35" in mn:
        from tinker_cookbook.renderers.qwen3_5 import Qwen3_5Renderer

        return Qwen3_5Renderer(tokenizer, image_processor)
    if "qwen3-vl" in mn:
        from tinker_cookbook.renderers.qwen3 import Qwen3VLInstructRenderer

        return Qwen3VLInstructRenderer(tokenizer, image_processor)
    if "llama" in mn and "vision" in mn:
        raise NotImplementedError(
            "Llama 3.2 Vision is not supported by the bundled tinker-cookbook renderers in api_tinker.py. "
            "Use Kimi K2.5 or a Qwen3-VL / Qwen3.5 model id, or add a custom renderer."
        )
    from tinker_cookbook.renderers.qwen3 import Qwen3VLInstructRenderer

    return Qwen3VLInstructRenderer(tokenizer, image_processor)


def sample_vlm(
    messages: list[dict[str, Any]],
    model_name: str = DEFAULT_MODEL,
    max_tokens: int = 2048,
    temperature: float = 0.2,
) -> str:
    """
    Run one VLM completion via Tinker sampling client + model-appropriate cookbook renderer.
    Returns assistant text (raw).
    """
    try:
        from tinker_cookbook import tokenizer_utils
        from tinker_cookbook.image_processing_utils import get_image_processor
    except ImportError as e:
        raise ImportError(
            "Install Tinker cookbook for multimodal rendering: pip install tinker-cookbook"
        ) from e

    tokenizer = tokenizer_utils.get_tokenizer(model_name)
    image_processor = get_image_processor(model_name)
    renderer = get_renderer(model_name, tokenizer, image_processor)

    service = tinker.ServiceClient()
    sampling_client = service.create_sampling_client(base_model=model_name)

    prompt = renderer.build_generation_prompt(messages)
    stop = renderer.get_stop_sequences()
    params = SamplingParams(
        max_tokens=max_tokens,
        temperature=temperature,
        stop=stop,
    )
    fut = sampling_client.sample(prompt=prompt, sampling_params=params, num_samples=1)
    result = fut.result()
    tokens = result.sequences[0].tokens
    msg, ok = renderer.parse_response(tokens)
    if ok and isinstance(msg, dict) and msg.get("content"):
        return str(msg["content"])
    return tokenizer.decode(tokens)


def run_one(
    oid: str,
    target_class: str,
    row: Any,
    stamps_root: Path | None = None,
    model_name: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    """Build metadata from manifest row, load montage, call VLM. Returns dict with raw_text."""
    meta = manifest_row_to_metadata(row)
    img = montage_path(target_class, oid, stamps_root)
    if not img.is_file():
        raise FileNotFoundError(f"Missing montage: {img}")
    messages = build_messages(oid, target_class, meta, img)
    raw = sample_vlm(messages, model_name=model_name)
    return {
        "oid": oid,
        "target_class": target_class,
        "montage_path": str(img),
        "raw_text": raw,
        "model": model_name,
    }
