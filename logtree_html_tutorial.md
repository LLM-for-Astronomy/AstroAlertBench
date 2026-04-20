# Logging Conversations to HTML with `logtree` (with/without Thinking)

A self-contained tutorial on how I generate the per-iteration HTML reports you've seen in my negotiation RL runs — the ones that show each trajectory's buyer/seller conversation, including a collapsible `💭 Thinking` block for reasoning models.

This file is written so you can copy the pattern into your own project; it does not assume you know the negotiation code.

---

## 1. The Package

Everything comes from **`tinker_cookbook`** (the client library that wraps the Tinker training/sampling API). Two modules do all the work:

| Module | Purpose |
|---|---|
| `tinker_cookbook.utils.logtree` | Scope-based HTML trace writer (nested `<section>` tree + auto-styled CSS). |
| `tinker_cookbook.utils.logtree_formatters` | Pre-built `ConversationFormatter` that renders a `list[Message]` with role-colored bubbles and thinking/tool-call parts. |

Install with tinker-cookbook (pulled in as a dependency for any Tinker RL/SL project). Source paths for reference:

- `tinker-cookbook/tinker_cookbook/utils/logtree.py`
- `tinker-cookbook/tinker_cookbook/utils/logtree_formatters.py`
- `tinker-cookbook/tinker_cookbook/renderers/base.py` (for `Message`, `get_text_content`)

You don't need to write any CSS. `ConversationFormatter` ships its own stylesheet; `logtree` deduplicates and inlines it into the final HTML.

---

## 2. The Three API Calls You Actually Need

```python
from tinker_cookbook.utils import logtree
from tinker_cookbook.utils.logtree_formatters import ConversationFormatter
```

- `logtree.init_trace(title, path=...)` — context manager that opens an HTML document and writes it to `path` on exit (or on exception, if `write_on_error=True`, which is the default).
- `logtree.scope_header(title)` — nests a `<section>` with an auto-leveled `<h2>/<h3>/...` heading. Use these to structure the report (per iteration → per group → per trajectory → buyer/seller).
- `logtree.log_formatter(ConversationFormatter(messages=...))` — dumps a full conversation inside the current scope.
- `logtree.optional_enable_logging(enable: bool)` — context manager that silently drops every `logtree.*` call inside it when `enable=False`. This is how I log only the first N groups without sprinkling `if` checks everywhere.

Minimum viable example (project-agnostic):

```python
from tinker_cookbook.utils import logtree
from tinker_cookbook.utils.logtree_formatters import ConversationFormatter

messages = [
    {"role": "system",    "content": "You are a helpful assistant."},
    {"role": "user",      "content": "Hi!"},
    {"role": "assistant", "content": "Hello, how can I help?"},
]

with logtree.init_trace("My Eval Report", path="report.html"):
    with logtree.scope_header("Trajectory 0"):
        logtree.log_formatter(ConversationFormatter(messages=messages))
```

That produces a standalone `report.html` you can open in a browser.

---

## 3. Thinking vs. Non-Thinking: the Content Shape

This is the one trick that trips people up. In `tinker_cookbook`, a `Message["content"]` has **two possible shapes**, depending on whether the renderer/model produced structured reasoning:

```python
# Non-thinking model (e.g. Qwen3-Instruct, GPT-4o): plain string
{"role": "assistant", "content": "Sure, the answer is 42."}

# Thinking model (e.g. Qwen3-Thinking, GPT-5 with reasoning_effort): list of typed parts
{"role": "assistant", "content": [
    {"type": "thinking", "thinking": "The user asked ... let me reason ..."},
    {"type": "text",     "text":     "Sure, the answer is 42."},
]}
```

`ConversationFormatter` handles **both shapes automatically**. See
`tinker-cookbook/tinker_cookbook/utils/logtree_formatters.py:16-57`:

```python
def _render_content_html(content: Content) -> str:
    if isinstance(content, str):
        return f'<span class="lt-text-part">{html.escape(content)}</span>'

    parts_html = []
    for part in content:
        if part["type"] == "text":
            parts_html.append(f'<span class="lt-text-part">{html.escape(part["text"])}</span>')
        elif part["type"] == "thinking":
            escaped = html.escape(part["thinking"])
            parts_html.append(
                f'<details class="lt-thinking-part">'
                f"<summary>💭 Thinking</summary>"
                f"<pre>{escaped}</pre>"
                f"</details>"
            )
        elif part["type"] == "tool_call":
            ...
        elif part["type"] == "image":
            ...
```

So: **if you want the HTML to show a collapsible 💭 Thinking block, you must feed the raw list-of-parts content into `ConversationFormatter`.** If you feed a plain string, there's nothing to render.

### How to strip thinking (for parsing / training) vs. keep it (for HTML)

`tinker_cookbook` also provides a helper that flattens the list-of-parts into a single string (dropping thinking/tool-call parts):

```python
from tinker_cookbook.renderers.base import get_text_content

text_only = get_text_content({"role": "assistant", "content": raw_list_or_str})
# text_only is always a plain str, safe to pass to a regex parser / next-turn prompt.
```

This split — plain text for the parser/next-turn prompt vs. raw list for the HTML log — is the core of how I keep thinking out of the training signal while still seeing it in the report.

---

## 4. The Pattern I Use: Two Parallel Transcripts

In `tink_rl/env.py`, the environment keeps **two conversation histories** that grow turn-by-turn in parallel:

```python
# tink_rl/env.py:140-144 (docstring)
# _messages               : list[dict]  — buyer/parser view; assistant content is
#                                         flattened (no structured thinking parts).
# _messages_with_thinking : list[dict]  — parallel history with raw assistant content
#                                         from the renderer (str or list of parts).
#                                         Used only for logtree; next_messages still
#                                         uses _messages.
```

Inside `step()` (one turn of the env), both get appended:

```python
# tink_rl/env.py:314-320
raw_assistant_content = message.get("content")      # could be str or list[parts]
if raw_assistant_content is None:
    raw_assistant_content = ""
content = get_text_content({"role": "assistant", "content": raw_assistant_content})

# Single append site for both transcripts.
self._messages.append({"role": "assistant", "content": content})                  # flattened
self._messages_with_thinking.append({"role": "assistant", "content": raw_assistant_content})
```

The seller side mirrors the same pattern (`tink_rl/seller.py:232-237`):

```python
parsed_message, _success = c.renderer.parse_response(tokens)
raw = parsed_message.get("content") or ""
text = get_text_content({"role": "assistant", "content": raw})
self._messages.append({"role": "assistant", "content": text})
self._messages_with_thinking.append({"role": "assistant", "content": raw})
```

At episode end, only the with-thinking version is logged:

```python
# tink_rl/env.py:1114-1125
with logtree.scope_header("Buyer — With thinking conversation"):
    logtree.log_formatter(
        ConversationFormatter(messages=cast(Sequence[Message], messages_with_thinking))
    )
with logtree.scope_header("Seller — With thinking conversation"):
    logtree.log_formatter(
        ConversationFormatter(messages=cast(Sequence[Message], _seller._messages_with_thinking))
    )
```

**Takeaway for your project:** whenever you get a model response that might be structured, stash the raw content immediately. Don't flatten and then try to un-flatten later — the thinking text is lost once `get_text_content` runs.

---

## 5. Wiring It All Together at the Top Level

My eval loop opens exactly one trace per iteration and then selectively enables logging only for the first `num_groups_to_log` groups. The actual mechanism lives in `tinker_cookbook.rl.train._get_logtree_scope` (reproduced here so you don't need to go digging):

```python
# tinker-cookbook/tinker_cookbook/rl/train.py:146-168
@contextmanager
def _get_logtree_scope(
    log_path: str | None, num_groups_to_log: int, f_name: str, scope_name: str
):
    if log_path is None or num_groups_to_log <= 0:
        yield
        return

    logtree_path      = os.path.join(log_path, f"{f_name}.html")
    logtree_json_path = os.path.join(log_path, f"{f_name}_logtree.json")
    trace = None
    try:
        with logtree.init_trace(scope_name, path=logtree_path) as trace:
            logtree.log_text(_LOGTREE_EXPLANATION)
            yield
    finally:
        if trace is not None:
            logtree.write_trace_json(trace, logtree_json_path)
```

Two files per iteration: `{prefix}.html` (human-readable) and `{prefix}_logtree.json` (same tree as JSON, useful for programmatic post-hoc analysis).

My API-buyer eval loop uses it like this (`tink_rl/eval.py:546-560`):

```python
step     = eval_iteration
prefix   = f"eval_{eval_tag}_iteration_{step:06d}"

with _get_logtree_scope(
    log_path=train_cfg.log_path,
    num_groups_to_log=num_groups_to_log,   # e.g. 5 → log first 5 specs
    f_name=prefix,
    scope_name=f"API buyer eval {buyer_api_model} iteration {step:06d}",
):
    ...  # run all rollouts; only the first N have logging enabled (see below)
```

Inside each rollout, I gate on the group index with `optional_enable_logging` so that rollouts past the budget cost nothing (logtree calls short-circuit):

```python
# tink_rl/eval.py:413-424
enable_logtree = spec_idx < num_groups_to_log

async def _one_rollout(g: int) -> dict:
    with logtree.optional_enable_logging(enable=enable_logtree):
        with logtree.scope_header(
            f"Trajectory {g} Episode (spec {spec_idx}, product {spec.product_index})"
        ):
            env = NegotiationMessageEnv(spec, tinker_seller_completer=tinker_seller_completer)
            result = await _eval_one_episode_api(buyer, env, episode_label=f"spec{spec_idx}/g{g}")
    ...
```

Nesting you end up with in the HTML:

```
<h1> API buyer eval … iteration 000010          ← init_trace title
  <h2> Trajectory 0 Episode (spec 0, product …) ← scope_header per rollout
    <h3> Buyer — With thinking conversation     ← scope_header from env._make_terminal
      <ConversationFormatter output>
    <h3> Seller — With thinking conversation
      <ConversationFormatter output>
  <h2> Trajectory 1 Episode …
    …
```

Training-side uses exactly the same mechanism — `tinker_cookbook.rl.train` wraps each iteration in `_get_logtree_scope(... f_name=f"train_iteration_{step:06d}" ...)`, so the `train_iteration_*.html` files have the same structure.

---

## 6. Example HTML to Send as Reference

Open this file in a browser — it has the full eval hierarchy (`<h1>` iteration → `<h2>` per trajectory → `<h3>` Buyer/Seller conversations), inlined CSS, ~400 conversation blocks:

```
/p/rlprojects/tinker/AI-Negotiation-Benchmark/tink_rl_runs/
  2026-03-28-16-42-Qwen3-30B-A3B-Instruct-2507-Qwen3-30B-A3B-Instruct-2507/
    eval_test_iteration_000040.html
```

(~820 KB, self-contained.) The buyer/seller in that run are both Qwen3-Instruct (non-thinking), so the assistant content is plain string and you won't see 💭 Thinking blocks. The same code path auto-produces the collapsible block whenever the renderer emits list-of-parts content for a thinking/reasoning model — no extra wiring needed on your side.

Adjacent `train_iteration_*.html` files in the same directory use the identical mechanism (just with a different `f_name` prefix).

---

## 7. Checklist to Replicate in Your Project

1. `pip install tinker-cookbook` (or vendor the two files in section 1 — `logtree.py` has no Tinker-specific imports; `logtree_formatters.py` only imports `Message`/`Content` types from `tinker_cookbook.renderers.base`).
2. In your env/agent, keep **two** message lists side by side:
   - the flattened one (`get_text_content(...)`) → use for parsing, next-turn prompts, training loss.
   - the raw one → use only for logging.
3. At the top of each eval/train iteration, wrap the whole thing in `logtree.init_trace(title, path="iter_N.html")`.
4. Around each trajectory/group you care about, wrap in `logtree.scope_header(name)`. Gate with `logtree.optional_enable_logging(enable)` so that past-budget groups are silently skipped.
5. At terminal state, call `logtree.log_formatter(ConversationFormatter(messages=raw_messages))`. One call per conversation you want to show.
6. Done — `init_trace` writes the HTML on context exit. No manual close, no CSS to copy, and thinking parts render themselves when present.
