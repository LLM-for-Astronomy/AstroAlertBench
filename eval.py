"""Run test-set evaluation with **Tinker-hosted** or **API-based** (GPT, Claude, Gemini) buyers.

Tinker buyer mode (default)
~~~~~~~~~~~~~~~~~~~~~~~~~~~
The policy loads **public base** weights via
``ServiceClient.create_sampling_client(base_model=...)`` or a ``tinker://`` checkpoint, then
runs ``RLTestSetEvaluator`` on the test split.

API buyer mode (``buyer_type=gpt``, future: ``claude``, ``gemini``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The buyer generates via the provider's Chat Completions API.  The seller is still Tinker-hosted
(default Qwen) or GPT (``seller_type=gpt``).  The evaluation drives ``NegotiationMessageEnv``
directly (no ``EnvFromMessageEnv`` / ``SamplingClient``).

CLI arguments (``chz``: ``python -m tink_rl.eval key=value ...``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Shared flags (both buyer modes):**

``run``
    Training run folder under ``tink_rl_runs/``, or absolute path. Must contain ``config.json``
    (template for dataset, seller, group sizes, eval knobs). **Default:** see
    ``_DEFAULT_RUN_FOLDER``.

``max_tokens``
    Per-turn generation cap. ``dataset_builder.max_trajectory_tokens`` = ``max_tokens * 6``.

``first_n_data``
    Optional; only the first N test env groups. Omit for the full test split.

``house_eval``
    Evaluate on **dataset_house** instead of default Amazon data.

``group_size``
    Parallel buyer rollouts per test env group (**default:** ``4``).

``seller_persona``
    Seller tone (see ``tink_rl.seller.build_seller_system_prompt``).

``eval_output_root``
    Optional directory override for output (default: ``tink_rl_eval/``).

``output_dir_name``
    Override for the subdirectory name under ``eval_output_root``.

``seller_type`` / ``gpt_model`` / ``gpt_reasoning_effort``
    Seller-side configuration (seller backend, model, reasoning effort).

**Buyer type:**

``buyer_type``
    ``tinker`` (default) | ``gpt`` (future: ``claude``, ``gemini``).

``buyer_api_model``
    Model id for API-based buyers (e.g. ``gpt-5``, ``gpt-5-mini``).
    Required when ``buyer_type != tinker``.

``buyer_reasoning_effort``
    Reasoning effort for API buyers (``low`` | ``medium`` | ``high``).

**Tinker-only flags (ignored when ``buyer_type != tinker``):**

``tinker_preset``
    ``non_reasoning`` | ``reasoning`` | ``all`` — curated Tinker model sweeps.

``tinker_models``
    Comma-separated Tinker/HF model ids.

``tinker_base_url``
    Override for ``tinker.ServiceClient`` endpoint.

``tinker_renderer_name``
    Override cookbook renderer (single-model ``tinker_models=`` only).

``tinker_train_model``
    ``/path/to/run+iteration_NNNNNN`` — Tinker training checkpoint.

**Examples**

  # Tinker buyer (existing usage, now with tinker_ prefix):
  python -m tink_rl.eval tinker_models=openai/gpt-oss-20b first_n_data=32

  python -m tink_rl.eval tinker_preset=non_reasoning

  python -m tink_rl.eval \\
    'tinker_train_model=/path/tink_rl_runs/MY-RUN+iteration_000060'

  # GPT buyer vs default Qwen seller:
  python -m tink_rl.eval \\
    buyer_type=gpt buyer_api_model=gpt-5 buyer_reasoning_effort=medium \\
    first_n_data=10 eval_output_root=tink_rl_eval/03_gpt/gpt_buyer/generation

**Credentials:** ``TINKER_API_KEY`` and ``OPENAI_API_KEY`` from ``.env`` (see ``.env.example``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import chz
import tinker
from tink_rl.benchmark_dotenv import load_benchmark_dotenv
from tinker_cookbook import checkpoint_utils
from tinker_cookbook.model_info import get_recommended_renderer_name
from tinker_cookbook.rl.metric_util import RLTestSetEvaluator
from tinker_cookbook.rl import train as rl_train
from tinker_cookbook.rl.train import _get_logtree_scope
from tinker_cookbook.utils import logtree, ml_log

from tink_rl.dataset import TEST_INDICES_PATH, DatasetBuilder, load_indices
from tink_rl.eval_from_trained_model import (
    resolve_run_dir,
    state_path_from_checkpoints_jsonl,
    train_config_from_run_dir,
)

load_benchmark_dotenv()

_DEFAULT_RUN_FOLDER = (
    "2026-03-20-01-52-Qwen3-30B-A3B-Instruct-2507-Qwen3-30B-A3B-Instruct-2507"
)

logger = logging.getLogger(__name__)

os.environ.setdefault("USE_TINKER", "1")

_BENCHMARK_ROOT = Path(__file__).resolve().parent.parent
_EVAL_ROOT = _BENCHMARK_ROOT / "tink_rl_eval"
_HOUSE_CAMEL_DIR = _BENCHMARK_ROOT / "data" / "dataset_house" / "camel_format"
_HOUSE_INDICES_JSON = (
    _BENCHMARK_ROOT / "tink_rl" / "data" / "dataset_house" / "house_vehicle_electronics_indices.json"
)
_UNTRAINED_EVAL_ITERATION = 0

_TRAIN_MODEL_ITER_MARKER = "+iteration_"


def parse_train_model_spec(raw: str) -> tuple[Path, int]:
    """Split ``…/RUN+iteration_NNNNNN`` into ``(resolved_run_dir, batch_index)``."""
    left, _, right = raw.strip().rpartition(_TRAIN_MODEL_ITER_MARKER)
    if not left:
        raise SystemExit(
            "tinker_train_model must look like .../RUN+iteration_NNNNNN "
            "(e.g. tink_rl_runs/MY-RUN+iteration_000060)"
        )
    return Path(os.path.expanduser(left.strip())).resolve(), int(right.strip())


@dataclass(frozen=True)
class BaseModelEvalPreset:
    """One Tinker base-model eval job: HF id, cookbook ``renderer_name``, output folder name."""

    buyer_model: str
    renderer_name: str
    output_dir_name: str


NON_REASONING_EVAL_PRESETS: tuple[BaseModelEvalPreset, ...] = (
    BaseModelEvalPreset(
        "meta-llama/Llama-3.3-70B-Instruct", "llama3", "meta-llama-Llama-3.3-70B-Instruct"
    ),
    BaseModelEvalPreset(
        "Qwen/Qwen3-4B-Instruct-2507",
        "qwen3_instruct",
        "Qwen-Qwen3-4B-Instruct-2507",
    ),
    BaseModelEvalPreset(
        "Qwen/Qwen3-30B-A3B-Instruct-2507",
        "qwen3_instruct",
        "Qwen-Qwen3-30B-A3B-Instruct-2507",
    ),
    BaseModelEvalPreset(
        "Qwen/Qwen3-235B-A22B-Instruct-2507",
        "qwen3_instruct",
        "Qwen-Qwen3-235B-A22B-Instruct-2507",
    ),
    BaseModelEvalPreset(
        "Qwen/Qwen3-30B-A3B",
        "qwen3_disable_thinking",
        "Qwen-Qwen3-30B-A3B-nothink",
    ),
    BaseModelEvalPreset(
        "deepseek-ai/DeepSeek-V3.1",
        "deepseekv3",
        "deepseek-ai-DeepSeek-V3.1-nothink",
    ),
    BaseModelEvalPreset(
        "openai/gpt-oss-20b",
        "gpt_oss_no_sysprompt",
        "openai-gpt-oss-20b-noreason",
    ),
    BaseModelEvalPreset(
        "openai/gpt-oss-120b",
        "gpt_oss_no_sysprompt",
        "openai-gpt-oss-120b-noreason",
    ),
    BaseModelEvalPreset(
        "moonshotai/Kimi-K2.5",
        "kimi_k25_disable_thinking",
        "moonshotai-Kimi-K2.5-nothink",
    ),
)

REASONING_EVAL_PRESETS: tuple[BaseModelEvalPreset, ...] = (
    BaseModelEvalPreset(
        "moonshotai/Kimi-K2-Thinking",
        "kimi_k2",
        "moonshotai-Kimi-K2-Thinking",
    ),
    BaseModelEvalPreset(
        "moonshotai/Kimi-K2.5",
        "kimi_k25",
        "moonshotai-Kimi-K2.5-reason",
    ),
    BaseModelEvalPreset(
        "deepseek-ai/DeepSeek-V3.1",
        "deepseekv3_thinking",
        "deepseek-ai-DeepSeek-V3.1-thinking",
    ),
    BaseModelEvalPreset(
        "openai/gpt-oss-20b",
        "gpt_oss_medium_reasoning",
        "openai-gpt-oss-20b-reason",
    ),
    BaseModelEvalPreset(
        "openai/gpt-oss-120b",
        "gpt_oss_medium_reasoning",
        "openai-gpt-oss-120b-reason",
    ),
    BaseModelEvalPreset(
        "Qwen/Qwen3-30B-A3B",
        "qwen3",
        "Qwen-Qwen3-30B-A3B-think",
    ),
)


# ---------------------------------------------------------------------------
# Tinker buyer eval path (extracted from old _async_eval_one_base_model)
# ---------------------------------------------------------------------------

async def _run_tinker_buyer_eval(
    train_cfg: rl_train.Config,
    buyer_model: str,
    dir_name: str,
    *,
    first_n_data: int | None = None,
    checkpoint_weights: str | None = None,
    eval_iteration: int = 0,
    ml_logger_obj=None,
) -> dict:
    """Tinker SamplingClient + RLTestSetEvaluator path. Returns metrics dict."""
    tinker_service_client = tinker.ServiceClient(base_url=train_cfg.base_url)
    if checkpoint_weights is None:
        tinker_sampling_client = tinker_service_client.create_sampling_client(
            base_model=buyer_model
        )
        logger.info("Tinker sampling client for base model %s", buyer_model)
    else:
        user_metadata: dict[str, str] = {}
        if ml_logger_obj is not None:
            if wandb_link := ml_logger_obj.get_logger_url():
                user_metadata["wandb_link"] = wandb_link
        checkpoint_utils.add_renderer_name_to_user_metadata(
            user_metadata, train_cfg.renderer_name
        )
        await checkpoint_utils.check_renderer_name_for_checkpoint_async(
            tinker_service_client, checkpoint_weights, train_cfg.renderer_name
        )
        training_client = await tinker_service_client.create_training_client_from_state_async(
            checkpoint_weights, user_metadata=user_metadata
        )
        logger.info("Tinker sampling client from checkpoint %s", checkpoint_weights)
        tinker_sampling_client = await training_client.save_weights_and_get_sampling_client_async()

    _, test_dataset = await train_cfg.dataset_builder()
    if test_dataset is None:
        raise SystemExit("dataset_builder returned no test dataset; cannot run eval.")
    evaluators: list = [
        RLTestSetEvaluator(
            test_dataset,
            max_tokens=train_cfg.max_tokens,
            temperature=train_cfg.eval_temperature,
            num_groups_to_log=train_cfg.num_groups_to_log,
            name=dir_name,
        )
    ]
    test_eval = evaluators[0]
    if first_n_data is not None:
        full_P = test_eval.env_group_builders_P
        test_eval.env_group_builders_P = list(full_P[:first_n_data])
        logger.info(
            "first_n_data=%s: eval on %s test groups (of %s full test groups)",
            first_n_data,
            len(test_eval.env_group_builders_P),
            len(full_P),
        )
    for builder in train_cfg.evaluator_builders:
        evaluators.append(builder())

    step = eval_iteration
    eval_tag = rl_train._sanitize_filename_component(dir_name)
    prefix = f"eval_{eval_tag}_iteration_{step:06d}"
    out_html = Path(train_cfg.log_path) / f"{prefix}.html"
    out_jsonl = Path(train_cfg.log_path) / f"{prefix}_rollout_summaries.jsonl"
    logger.info(
        "Running Tinker buyer eval buyer=%s step=%s → %s, %s, …",
        buyer_model, step, out_html.name, out_jsonl.name,
    )

    metrics = await rl_train.run_evaluations_parallel(
        evaluators, tinker_sampling_client, train_cfg, step
    )
    logger.info("Tinker buyer eval metrics: %s", metrics)
    return metrics


# ---------------------------------------------------------------------------
# API buyer eval path (GPT, future Claude / Gemini)
# ---------------------------------------------------------------------------

async def _eval_one_episode_api(buyer, env, episode_label: str = "") -> dict:
    """Drive one negotiation episode: API buyer vs seller inside *env*.

    Returns a dict containing:
      - ``episode_summary``: unified top-level fields from ``env.episode_summary()``,
      - ``steps``: per-turn metrics/logs list,
      - ``buyer_usage``: total prompt/completion tokens,
      - ``per_turn_buyer_usage``: list of per-turn token dicts.

    The caller (``_run_one_group_api``) merges ``episode_summary`` into the JSONL row
    and attaches the other fields alongside it.
    """
    messages = await env.initial_observation()
    total_prompt = 0
    total_completion = 0
    turn = 0
    steps: list[dict] = []
    per_turn_buyer_usage: list[dict] = []

    while True:
        turn += 1
        text, prompt_tokens, completion_tokens = await buyer.generate(messages)
        total_prompt += prompt_tokens
        total_completion += completion_tokens
        result = await env.step({"role": "assistant", "content": text})

        # Accumulate per-turn data (metrics + logs + buyer token counts).
        step_entry: dict = {
            "turn": turn,
            "metrics": dict(result.metrics),
            "logs": dict(result.logs),
        }
        steps.append(step_entry)
        per_turn_buyer_usage.append({
            "turn": turn,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        })

        logger.info(
            "[%s] turn %d  buyer=%d tok  seller done=%s  reward=%.4f",
            episode_label, turn, completion_tokens, result.episode_done, result.reward,
        )
        if result.episode_done:
            return {
                "episode_summary": env.episode_summary(),
                "steps": steps,
                "buyer_usage": {
                    "prompt_tokens": total_prompt,
                    "completion_tokens": total_completion,
                },
                "per_turn_buyer_usage": per_turn_buyer_usage,
            }
        messages = result.next_messages


async def _run_one_group_api(
    buyer,
    spec,
    spec_idx: int,
    group_size: int,
    tinker_seller_completer,
    buyer_type: str,
    buyer_api_model: str,
    num_groups_to_log: int,
) -> list[dict]:
    """Run ``group_size`` parallel rollouts for one spec.  Returns list of summary dicts.

    Mirrors ``do_group_rollout`` in ``tinker_cookbook.rl.rollouts``: all rollouts within the
    group execute concurrently via ``asyncio.gather``.

    When ``spec_idx < num_groups_to_log`` and a logtree trace is active (see
    ``_get_logtree_scope`` in ``_run_api_buyer_eval``), each trajectory is wrapped in a
    ``Trajectory {g} Episode`` section; terminal turns log buyer/seller transcripts via
    ``NegotiationMessageEnv._make_terminal`` (same as Tinker buyer eval).

    Each returned dict is one JSONL row in the unified schema (v2).  Top-level
    fields come from ``env.episode_summary()`` (codename, category, outcome,
    deal_price, reward, turn_log, …).  API-buyer-specific fields (buyer_type,
    buyer_api_model, buyer_usage, per_turn_buyer_usage, steps) are merged in
    alongside.  The ``metrics`` dict is kept for backward compatibility with the
    aggregation in ``_run_api_buyer_eval``.
    """
    from tink_rl.env import NegotiationMessageEnv

    enable_logtree = spec_idx < num_groups_to_log

    async def _one_rollout(g: int) -> dict:
        with logtree.optional_enable_logging(enable=enable_logtree):
            with logtree.scope_header(
                f"Trajectory {g} Episode (spec {spec_idx}, product {spec.product_index})"
            ):
                env = NegotiationMessageEnv(
                    spec, tinker_seller_completer=tinker_seller_completer
                )
                ep_label = f"spec{spec_idx}/g{g}"
                result = await _eval_one_episode_api(buyer, env, episode_label=ep_label)

        # Build unified JSONL row: episode_summary fields at top level,
        # plus API-buyer-specific metadata.
        summary = result["episode_summary"]
        summary.update({
            "spec_idx": spec_idx,
            "group_idx": g,
            "buyer_type": buyer_type,
            "buyer_model": buyer_api_model,
            "buyer_usage": result["buyer_usage"],
            "per_turn_buyer_usage": result["per_turn_buyer_usage"],
            "steps": result["steps"],
            "metrics": result["steps"][-1]["metrics"] if result["steps"] else {},
        })
        return summary

    results = list(await asyncio.gather(*[_one_rollout(g) for g in range(group_size)]))
    rewards = [r["reward"] for r in results]
    logger.info(
        "spec %d (product=%d) — %d rollouts done  mean_reward=%.4f",
        spec_idx, spec.product_index, group_size, sum(rewards) / len(rewards),
    )
    return results


async def _run_api_buyer_eval(
    train_cfg: rl_train.Config,
    dir_name: str,
    *,
    buyer_type: str,
    buyer_api_model: str,
    buyer_reasoning_effort: str = "",
    first_n_data: int | None = None,
    group_size: int = 4,
    eval_iteration: int = 0,
    max_concurrent_specs: int = 16,
    api_buyer_spec_start: int = 0,
) -> dict:
    """API buyer (GPT / Claude / Gemini) eval loop using NegotiationMessageEnv directly.

    Parallelism mirrors ``RLTestSetEvaluator`` + ``do_group_rollout``:
    - **Outer gather**: all test groups (specs) run concurrently.
    - **Inner gather**: ``group_size`` rollouts per spec run concurrently.

    HTML + JSON logtree reuse the same mechanism as Tinker eval
    (``tinker_cookbook.rl.train._get_logtree_scope``): writes
    ``{prefix}.html`` and ``{prefix}_logtree.json`` under ``train_cfg.log_path``.
    The first ``num_groups_to_log`` specs (same field as training config) get
    ``logtree.optional_enable_logging(True)`` so ``NegotiationMessageEnv`` can
    record terminal buyer/seller conversations.
    """
    from tink_rl.buyer import create_api_buyer
    from tink_rl.dataset import _make_specs
    from tink_rl.seller import create_seller_completer

    buyer = create_api_buyer(
        buyer_type,
        buyer_api_model,
        max_tokens=train_cfg.max_tokens,
        reasoning_effort=buyer_reasoning_effort,
        temperature=train_cfg.eval_temperature,
    )

    db = cast(DatasetBuilder, train_cfg.dataset_builder)

    tinker_seller_completer = None
    if db.seller_type != "gpt":
        tinker_service_client = tinker.ServiceClient(base_url=train_cfg.base_url)
        tinker_seller_completer = create_seller_completer(
            tinker_service_client,
            db.seller_model,
            db.max_tokens,
            db.seller_temperature,
        )

    test_path = Path(db.test_data_path) if db.test_data_path else TEST_INDICES_PATH
    test_indices = load_indices(test_path)
    specs = _make_specs(
        test_indices,
        seller_model=db.seller_model,
        budget_ratio=db.budget_ratio,
        max_turns=db.max_turns,
        max_tokens=db.max_tokens,
        seller_temperature=db.seller_temperature,
        product_data_dir=db.product_data_dir,
        seller_persona=db.seller_persona,
        seller_type=db.seller_type,
        gpt_reasoning_effort=db.gpt_reasoning_effort,
    )

    if first_n_data is not None:
        specs = specs[:first_n_data]

    n_specs_before_start = len(specs)
    spec_start = api_buyer_spec_start
    if spec_start < 0:
        raise SystemExit("api_buyer_spec_start must be >= 0.")
    if spec_start >= n_specs_before_start:
        raise SystemExit(
            f"api_buyer_spec_start={spec_start} must be < number of specs ({n_specs_before_start})."
        )
    idx_base = spec_start
    if spec_start:
        specs = specs[spec_start:]

    total_episodes = len(specs) * group_size
    if max_concurrent_specs < 1:
        raise SystemExit("api_buyer_max_concurrent_specs must be >= 1.")
    logger.info(
        "API buyer eval: type=%s model=%s effort=%s specs=%d (global_idx %d..%d) "
        "group_size=%d total_episodes=%d (max %d specs parallel)",
        buyer_type, buyer_api_model, buyer_reasoning_effort or "(none)",
        len(specs),
        idx_base,
        idx_base + len(specs) - 1,
        group_size,
        total_episodes,
        max_concurrent_specs,
    )

    step = eval_iteration
    eval_tag = rl_train._sanitize_filename_component(dir_name)
    prefix = f"eval_{eval_tag}_iteration_{step:06d}"
    jsonl_path = Path(train_cfg.log_path) / f"{prefix}_rollout_summaries.jsonl"
    num_groups_to_log = train_cfg.num_groups_to_log

    all_rewards: list[float] = []
    all_metrics: list[dict] = []

    jsonl_mode = "a" if spec_start else "w"
    with _get_logtree_scope(
        log_path=train_cfg.log_path,
        num_groups_to_log=num_groups_to_log,
        f_name=prefix,
        scope_name=f"API buyer eval {buyer_api_model} iteration {step:06d}",
    ):
        with open(jsonl_path, jsonl_mode) as fout:
            for batch_start in range(0, len(specs), max_concurrent_specs):
                batch_slice = specs[
                    batch_start : batch_start + max_concurrent_specs
                ]
                batch_specs = [
                    (idx_base + batch_start + j, spec)
                    for j, spec in enumerate(batch_slice)
                ]
                batch_results: list[list[dict]] = list(
                    await asyncio.gather(
                        *[
                            _run_one_group_api(
                                buyer,
                                spec,
                                spec_idx,
                                group_size,
                                tinker_seller_completer,
                                buyer_type,
                                buyer_api_model,
                                num_groups_to_log,
                            )
                            for spec_idx, spec in batch_specs
                        ]
                    )
                )
                for summaries in batch_results:
                    for summary in summaries:
                        all_rewards.append(summary["reward"])
                        all_metrics.append(summary["metrics"])
                        fout.write(json.dumps(summary, default=str) + "\n")
                fout.flush()
                logger.info(
                    "  batch spec_idx %d–%d (run %d/%d in this invocation)  "
                    "(cumulative mean reward=%.4f)",
                    idx_base + batch_start,
                    idx_base
                    + min(batch_start + max_concurrent_specs, len(specs))
                    - 1,
                    min(batch_start + max_concurrent_specs, len(specs)),
                    len(specs),
                    sum(all_rewards) / len(all_rewards),
                )

    if num_groups_to_log > 0:
        logger.info(
            "Wrote logtree HTML/JSON: %s.html, %s_logtree.json",
            prefix,
            prefix,
        )
    logger.info("Wrote %s (%d episodes)", jsonl_path.name, len(all_rewards))

    agg: dict[str, float] = {}
    if all_metrics:
        all_keys = set()
        for m in all_metrics:
            all_keys.update(m.keys())
        for k in sorted(all_keys):
            vals = [m[k] for m in all_metrics if k in m and isinstance(m[k], (int, float))]
            if vals:
                agg[k] = sum(vals) / len(vals)

    agg["mean_reward"] = sum(all_rewards) / len(all_rewards) if all_rewards else 0.0
    agg["num_episodes"] = float(len(all_rewards))
    logger.info("API buyer eval metrics: %s", agg)
    return agg


# ---------------------------------------------------------------------------
# Shared outer function
# ---------------------------------------------------------------------------

async def _async_eval_one_base_model(
    template_cfg: rl_train.Config,
    buyer_label: str,
    *,
    buyer_type: str = "tinker",
    buyer_api_model: str = "",
    buyer_reasoning_effort: str = "",
    tinker_renderer_name: str | None = None,
    output_dir_name: str | None = None,
    first_n_data: int | None = None,
    eval_root: Path | None = None,
    checkpoint_weights: str | None = None,
    eval_iteration: int | None = None,
    group_size: int = 4,
    api_buyer_max_concurrent_specs: int = 16,
    api_buyer_spec_start: int = 0,
) -> dict:
    """Evaluate one buyer on the test split; shared setup then dispatch to Tinker or API path.

    ``buyer_label`` is the HF model id (Tinker) or the API model name (API buyer).
    """
    dir_name = (output_dir_name or buyer_label.strip("/").replace("/", "-")).strip("/")
    root = eval_root if eval_root is not None else _EVAL_ROOT
    out_dir = root / dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    if buyer_type == "tinker":
        if checkpoint_weights is None:
            renderer = tinker_renderer_name or get_recommended_renderer_name(buyer_label)
        else:
            renderer = (
                tinker_renderer_name
                or template_cfg.renderer_name
                or get_recommended_renderer_name(buyer_label)
            )
    else:
        renderer = template_cfg.renderer_name or "qwen3"

    dataset_builder = chz.replace(
        template_cfg.dataset_builder,
        buyer_model=buyer_label,
        renderer_name=renderer,
    )
    train_cfg = chz.replace(
        template_cfg,
        model_name=buyer_label,
        dataset_builder=dataset_builder,
        renderer_name=renderer,
        log_path=str(out_dir.resolve()),
    )
    if train_cfg.wandb_name:
        train_cfg = chz.replace(train_cfg, wandb_name=f"{train_cfg.wandb_name}-{dir_name}")

    logger.info(
        "Eval: buyer_type=%s buyer=%s renderer=%s → out_dir=%s",
        buyer_type, buyer_label, renderer, out_dir.name,
    )

    ml_logger = ml_log.setup_logging(
        log_dir=train_cfg.log_path,
        wandb_project=train_cfg.wandb_project,
        config=train_cfg,
        wandb_name=train_cfg.wandb_name,
    )
    try:
        step = eval_iteration if eval_iteration is not None else _UNTRAINED_EVAL_ITERATION

        if buyer_type == "tinker":
            metrics = await _run_tinker_buyer_eval(
                train_cfg,
                buyer_label,
                dir_name,
                first_n_data=first_n_data,
                checkpoint_weights=checkpoint_weights,
                eval_iteration=step,
                ml_logger_obj=ml_logger,
            )
        else:
            metrics = await _run_api_buyer_eval(
                train_cfg,
                dir_name,
                buyer_type=buyer_type,
                buyer_api_model=buyer_api_model,
                buyer_reasoning_effort=buyer_reasoning_effort,
                first_n_data=first_n_data,
                group_size=group_size,
                eval_iteration=step,
                max_concurrent_specs=api_buyer_max_concurrent_specs,
                api_buyer_spec_start=api_buyer_spec_start,
            )

        eval_tag = rl_train._sanitize_filename_component(dir_name)
        prefix = f"eval_{eval_tag}_iteration_{step:06d}"
        metrics_path = Path(train_cfg.log_path) / f"{prefix}_rollout_metrics.json"
        payload: dict[str, object] = {
            "step": step,
            "iteration": step,
            "split": "eval/test",
            "rollout_metrics": metrics,
            "first_n_data": first_n_data,
            "checkpoint_weights": checkpoint_weights,
            "buyer_type": buyer_type,
            "buyer_api_model": buyer_api_model or None,
            "buyer_reasoning_effort": buyer_reasoning_effort or None,
            "api_buyer_max_concurrent_specs": api_buyer_max_concurrent_specs
            if buyer_type != "tinker"
            else None,
            "api_buyer_spec_start": api_buyer_spec_start
            if buyer_type != "tinker"
            else None,
        }
        with open(metrics_path, "w") as f:
            json.dump(
                payload,
                f,
                indent=2,
                sort_keys=True,
                default=lambda o: float(o) if hasattr(o, "__float__") else str(o),
            )
        logger.info("Wrote %s", metrics_path.name)

        return metrics
    finally:
        ml_logger.close()


# ---------------------------------------------------------------------------
# CLI config
# ---------------------------------------------------------------------------

@chz.chz
class CommonModelEvalConfig:
    """Parses ``key=value`` CLI; see module docstring."""

    # --- Shared (both Tinker and API buyer paths) ---
    run: str = _DEFAULT_RUN_FOLDER
    max_tokens: int = 4000
    first_n_data: int | None = None
    house_eval: bool = False
    group_size: int = chz.field(
        default=4,
        doc="Parallel rollouts per test env group; default 4.",
    )
    eval_output_root: str = ""
    output_dir_name: str = chz.field(
        default="",
        doc="Override subdirectory under eval_output_root.",
    )
    seller_persona: str = chz.field(
        default="default",
        doc="Key for tink_rl.seller.build_seller_system_prompt (see seller.py mapping).",
    )
    seller_type: str = chz.field(
        default="tinker",
        doc="Seller backend: tinker | gpt.",
    )
    gpt_model: str = chz.field(
        default="",
        doc="GPT model id for the seller (only when seller_type=gpt).",
    )
    gpt_reasoning_effort: str = chz.field(
        default="",
        doc="Reasoning effort for GPT seller (minimal | low | medium | high).",
    )

    # --- Buyer type selection ---
    buyer_type: str = chz.field(
        default="tinker",
        doc="Buyer backend: tinker | gpt (future: claude, gemini).",
    )
    buyer_api_model: str = chz.field(
        default="",
        doc="Model id for API-based buyers (e.g. gpt-5, gpt-5-mini).",
    )
    buyer_reasoning_effort: str = chz.field(
        default="",
        doc="Reasoning effort for API buyer (low | medium | high).",
    )
    api_buyer_max_concurrent_specs: int = chz.field(
        default=16,
        doc="API buyer only: max spec-groups in flight per batch (rate-limit control).",
    )
    api_buyer_spec_start: int = chz.field(
        default=0,
        doc="API buyer only: skip leading test specs (global spec_idx); use with append to jsonl.",
    )

    # --- Tinker-only (ignored when buyer_type != tinker) ---
    tinker_preset: str = chz.field(
        default="",
        doc="Tinker only. non_reasoning | reasoning | all.",
    )
    tinker_models: str = chz.field(
        default="",
        doc="Tinker only. Comma-separated HF model ids.",
    )
    tinker_base_url: str | None = None
    tinker_renderer_name: str = chz.field(
        default="",
        doc="Tinker only. Override cookbook renderer (single tinker_models= only).",
    )
    tinker_train_model: str = chz.field(
        default="",
        doc="Tinker only. Run dir + '+iteration_NNNNNN'.",
    )


def apply_common_eval_cli_overrides(
    cfg: CommonModelEvalConfig, train_cfg: rl_train.Config
) -> rl_train.Config:
    """Apply shared CLI overrides to the template train config."""
    if cfg.tinker_base_url is not None:
        train_cfg = chz.replace(train_cfg, base_url=cfg.tinker_base_url)
    mt = cfg.max_tokens
    db_for_seller = cast(DatasetBuilder, train_cfg.dataset_builder)
    seller_model_override = (
        cfg.gpt_model
        if cfg.seller_type == "gpt" and cfg.gpt_model
        else db_for_seller.seller_model
    )
    train_cfg = chz.replace(
        train_cfg,
        max_tokens=mt,
        dataset_builder=chz.replace(
            train_cfg.dataset_builder,
            max_tokens=mt,
            max_trajectory_tokens=mt * 6,
            group_size=cfg.group_size,
            seller_persona=cfg.seller_persona,
            seller_type=cfg.seller_type,
            seller_model=seller_model_override,
            gpt_reasoning_effort=cfg.gpt_reasoning_effort,
        ),
    )
    train_cfg = chz.replace(train_cfg, rollout_json_export=True)
    if cfg.house_eval:
        camel = _HOUSE_CAMEL_DIR.resolve()
        idx_path = _HOUSE_INDICES_JSON.resolve()
        if not camel.is_dir():
            raise SystemExit(
                f"house_eval: missing camel-format catalog at {camel}\n"
                "Run: python data/dataset_house/build_camel_format_catalog.py"
            )
        if not idx_path.is_file():
            raise SystemExit(f"house_eval: missing indices file at {idx_path}")
        idx_s = str(idx_path)
        house_idx = json.loads(idx_path.read_text(encoding="utf-8"))
        house_n = int(house_idx["n"])
        db = cast(DatasetBuilder, train_cfg.dataset_builder)
        train_cfg = chz.replace(
            train_cfg,
            dataset_builder=chz.replace(
                db,
                product_data_dir=str(camel),
                train_data_path=idx_s,
                test_data_path=idx_s,
                batch_size=house_n,
            ),
        )
    elif cfg.first_n_data is None:
        db = cast(DatasetBuilder, train_cfg.dataset_builder)
        tp = Path(db.test_data_path) if db.test_data_path else TEST_INDICES_PATH
        train_cfg = chz.replace(
            train_cfg,
            dataset_builder=chz.replace(db, batch_size=len(load_indices(tp))),
        )
    return train_cfg


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    cfg = chz.entrypoint(CommonModelEvalConfig)
    if cfg.first_n_data is not None and cfg.first_n_data < 1:
        raise SystemExit("`first_n_data` must be a positive integer when set.")
    if cfg.api_buyer_spec_start < 0:
        raise SystemExit("`api_buyer_spec_start` must be >= 0.")

    eval_root = (
        Path(cfg.eval_output_root).expanduser().resolve()
        if (cfg.eval_output_root or "").strip()
        else _EVAL_ROOT
    )
    eval_root.mkdir(parents=True, exist_ok=True)

    # ── API buyer path (GPT, future Claude / Gemini) ──────────────────────
    if cfg.buyer_type != "tinker":
        if not cfg.buyer_api_model:
            raise SystemExit(
                f"buyer_type={cfg.buyer_type!r} requires buyer_api_model=<model-id> "
                "(e.g. buyer_api_model=gpt-5)."
            )
        run_dir = resolve_run_dir(cfg.run)
        train_cfg = train_config_from_run_dir(run_dir)
        train_cfg = apply_common_eval_cli_overrides(cfg, train_cfg)

        effort_tag = cfg.buyer_reasoning_effort or "default"
        output_cfg = (cfg.output_dir_name or "").strip()
        dir_name = output_cfg or f"{cfg.buyer_api_model}-buyer_{effort_tag}"

        logger.info(
            "--- API buyer eval: %s (%s effort=%s) → %s ---",
            cfg.buyer_type, cfg.buyer_api_model, effort_tag, eval_root / dir_name,
        )
        asyncio.run(
            _async_eval_one_base_model(
                train_cfg,
                cfg.buyer_api_model,
                buyer_type=cfg.buyer_type,
                buyer_api_model=cfg.buyer_api_model,
                buyer_reasoning_effort=cfg.buyer_reasoning_effort,
                output_dir_name=dir_name,
                first_n_data=cfg.first_n_data,
                eval_root=eval_root,
                group_size=cfg.group_size,
                api_buyer_max_concurrent_specs=cfg.api_buyer_max_concurrent_specs,
                api_buyer_spec_start=cfg.api_buyer_spec_start,
            )
        )
        return

    # ── Tinker buyer path ─────────────────────────────────────────────────
    tinker_preset = (cfg.tinker_preset or "").strip().lower()
    train_model_raw = (cfg.tinker_train_model or "").strip()
    n_modes = bool(tinker_preset) + bool(cfg.tinker_models.strip()) + bool(train_model_raw)
    if n_modes > 1:
        raise SystemExit(
            "Use only one of: tinker_preset=..., tinker_models=id1,id2,..., "
            "tinker_train_model=/path...+iteration_NNNNNN."
        )
    renderer_cfg = (cfg.tinker_renderer_name or "").strip()
    output_cfg = (cfg.output_dir_name or "").strip()
    if train_model_raw and renderer_cfg:
        raise SystemExit(
            "`tinker_renderer_name` is not used with "
            "``tinker_train_model=`` (renderer comes from that run)."
        )

    # -- Tinker checkpoint eval --
    if train_model_raw:
        ckpt_run_dir, batch = parse_train_model_spec(train_model_raw)
        train_cfg = train_config_from_run_dir(ckpt_run_dir)
        train_cfg = apply_common_eval_cli_overrides(cfg, train_cfg)
        weights_uri: str | None = (
            None if batch == 0 else state_path_from_checkpoints_jsonl(ckpt_run_dir, batch)
        )
        out_subdir = output_cfg or f"{ckpt_run_dir.name}-iter_{batch:06d}-seller_{cfg.seller_persona}"
        buyer = train_cfg.model_name
        logger.info(
            "--- tinker_train_model eval: run=%s batch=%s buyer=%s → %s ---",
            ckpt_run_dir.name, batch, buyer, eval_root / out_subdir,
        )
        asyncio.run(
            _async_eval_one_base_model(
                train_cfg,
                buyer,
                output_dir_name=out_subdir,
                first_n_data=cfg.first_n_data,
                eval_root=eval_root,
                checkpoint_weights=weights_uri,
                eval_iteration=batch,
            )
        )
        return

    # -- Template config from run= --
    run_dir = resolve_run_dir(cfg.run)
    train_cfg = train_config_from_run_dir(run_dir)
    train_cfg = apply_common_eval_cli_overrides(cfg, train_cfg)

    # -- Tinker preset mode --
    if tinker_preset:
        if tinker_preset == "non_reasoning":
            jobs: tuple[BaseModelEvalPreset, ...] = NON_REASONING_EVAL_PRESETS
        elif tinker_preset == "reasoning":
            jobs = REASONING_EVAL_PRESETS
        elif tinker_preset == "all":
            jobs = NON_REASONING_EVAL_PRESETS + REASONING_EVAL_PRESETS
        else:
            raise SystemExit(
                "``tinker_preset`` must be one of: non_reasoning, reasoning, all "
                f"(got {cfg.tinker_preset!r})."
            )
        for p in jobs:
            logger.info(
                "--- Tinker preset %s: %s (%s) → %s ---",
                tinker_preset, p.buyer_model, p.renderer_name, eval_root / p.output_dir_name,
            )
            asyncio.run(
                _async_eval_one_base_model(
                    train_cfg,
                    p.buyer_model,
                    tinker_renderer_name=p.renderer_name,
                    output_dir_name=p.output_dir_name,
                    first_n_data=cfg.first_n_data,
                    eval_root=eval_root,
                )
            )
        return

    # -- Tinker explicit models --
    buyer_models = [m.strip() for m in cfg.tinker_models.split(",") if m.strip()]
    if not buyer_models:
        raise SystemExit(
            "Pass tinker_models=id1,id2,... OR tinker_preset=non_reasoning|reasoning|all "
            "OR tinker_train_model=/path/to/run+iteration_NNNNNN "
            "OR buyer_type=gpt buyer_api_model=gpt-5.\n"
            "See module docstring or https://tinker-docs.thinkingmachines.ai/model-lineup"
        )

    renderer_override = renderer_cfg or None
    output_override = output_cfg or None
    if len(buyer_models) != 1 and (renderer_override is not None or output_override is not None):
        raise SystemExit(
            "`tinker_renderer_name` and `output_dir_name` apply only when "
            "`tinker_models=` contains a single model id."
        )

    for buyer_model in buyer_models:
        _dir = buyer_model.strip("/").replace("/", "-")
        logger.info("--- Tinker base model eval: %s → %s ---", buyer_model, eval_root / _dir)
        asyncio.run(
            _async_eval_one_base_model(
                train_cfg,
                buyer_model,
                tinker_renderer_name=renderer_override,
                output_dir_name=output_override,
                first_n_data=cfg.first_n_data,
                eval_root=eval_root,
            )
        )


if __name__ == "__main__":
    main()
