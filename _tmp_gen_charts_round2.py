"""Generate charts for Round 2 prompt comparison (prompts_new vs prompts_old_backup vs prior runs)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUT = Path("charts/round2")
OUT.mkdir(parents=True, exist_ok=True)

# ======== ALL RUNS (11 total: 7 prior + 4 new) ========
# Prior 7 runs (from round 1):
#   0: Kimi old_prompt (fewshot_kimi_second, prompts.py pre-revision)  34%
#   1: Kimi prompts.py (fewshot_kimi_prompts)                          41%
#   2: Kimi agn_instr (fewshot_kimi_agn)                               35%
#   3: Qwen235 prompts.py (fewshot_qwen235_prompts)                    35%
#   4: Qwen235 agn_instr (fewshot_qwen235_agn)                         31%
#   5: Qwen30 prompts.py (fewshot_qwen30_prompts)                      33%
#   6: Qwen30 agn_instr (fewshot_qwen30_agn)                           31%
# New 4 runs:
#   7: Kimi old_backup (fewshot_kimi_oldbackup, prompts_old_backup.py) 36%
#   8: Kimi new_prompt (fewshot_kimi_newprompt, prompts_new.py)        42%
#   9: Qwen235 new_prompt (fewshot_qwen235_newprompt)                  44%
#  10: Qwen30 new_prompt (fewshot_qwen30_newprompt)                    25%

# ======== Focus: 4 new + relevant prior runs for comparison ========
# We'll compare across prompt versions for each model:
#   Kimi:    old_prompt(34%) | prompts.py(41%) | old_backup(36%) | new_prompt(42%)
#   Qwen235: prompts.py(35%) | new_prompt(44%)
#   Qwen30:  prompts.py(33%) | new_prompt(25%)

classes = ["SN", "AGN", "VS", "asteroid", "bogus"]
CLASS_COLORS = {"SN": "#EF5350", "AGN": "#AB47BC", "VS": "#42A5F5",
                "asteroid": "#FFA726", "bogus": "#78909C"}

# ---- New 4 runs data ----
NEW_LABELS = ["Kimi\nold_backup", "Kimi\nnew_prompt", "Qwen235\nnew_prompt", "Qwen30\nnew_prompt"]
NEW_COLORS = ["#9E9E9E", "#2196F3", "#4CAF50", "#FF9800"]

new_5class  = [0.36, 0.42, 0.44, 0.25]
new_stage1  = [0.77, 0.79, 0.83, 0.80]
new_stage2  = [0.65, 0.66, 0.69, 0.51]
new_stage3  = [0.41, 0.54, 0.50, 0.36]
new_macro_f1= [0.4112, 0.4406, 0.476, 0.2834]

new_sn  = [0.45, 0.50, 0.60, 0.20]
new_agn = [0.00, 0.00, 0.05, 0.00]
new_vs  = [0.95, 0.95, 0.90, 0.80]
new_ast = [0.20, 0.50, 0.40, 0.25]
new_bog = [0.20, 0.15, 0.25, 0.00]

new_sn_f1  = [0.6207, 0.6667, 0.7273, 0.3077]
new_vs_f1  = [0.6129, 0.6552, 0.6207, 0.5424]
new_agn_f1 = [0.0, 0.0, 0.08, 0.0]

new_msrs = [4.36, 4.44, 4.7567, 4.6633]
new_pearson = [0.2013, 0.067, -0.0778, 0.058]

# ---- All prompt versions for Kimi (4 runs) ----
KIMI_LABELS = ["old_prompt\n(prompts.py\npre-rev)", "prompts.py\n(rev)", "old_backup", "new_prompt"]
KIMI_COLORS = ["#888888", "#1565C0", "#9E9E9E", "#2196F3"]
kimi_5class = [0.34, 0.41, 0.36, 0.42]
kimi_stage1 = [0.77, 0.80, 0.77, 0.79]
kimi_stage2 = [0.65, 0.64, 0.65, 0.66]
kimi_stage3 = [0.39, 0.47, 0.41, 0.54]
kimi_macro_f1 = [0.3429, 0.511, 0.4112, 0.4406]
kimi_sn  = [0.30, 0.80, 0.45, 0.50]
kimi_agn = [0.00, 0.00, 0.00, 0.00]
kimi_vs  = [0.95, 0.95, 0.95, 0.95]
kimi_ast = [0.30, 0.05, 0.20, 0.50]
kimi_bog = [0.15, 0.25, 0.20, 0.15]

# ---- 3 models, new_prompt only ----
M3_LABELS = ["Kimi-K2.5", "Qwen3-235B", "Qwen3-30B"]
M3_COLORS = ["#2196F3", "#4CAF50", "#FF9800"]
m3_5class = [0.42, 0.44, 0.25]
m3_sn  = [0.50, 0.60, 0.20]
m3_agn = [0.00, 0.05, 0.00]
m3_vs  = [0.95, 0.90, 0.80]
m3_ast = [0.50, 0.40, 0.25]
m3_bog = [0.15, 0.25, 0.00]

plt.rcParams.update({"font.size": 11, "figure.dpi": 150})

# =========================================================================
# Chart R1: 5-Class Accuracy — 4 new runs
# =========================================================================
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(NEW_LABELS))
bars = ax.bar(x, new_5class, color=NEW_COLORS, edgecolor="white", width=0.6)
for b, v in zip(bars, new_5class):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.005, f"{v:.0%}", ha="center", va="bottom", fontsize=11)
ax.set_xticks(x); ax.set_xticklabels(NEW_LABELS, fontsize=9)
ax.set_ylabel("5-Class Accuracy"); ax.set_title("Round 2: Final 5-Class Accuracy")
ax.set_ylim(0, 0.55); ax.axhline(y=0.20, color="grey", linestyle="--", alpha=0.4, label="Random baseline (20%)")
ax.legend(fontsize=9); fig.tight_layout()
fig.savefig(OUT / "R01_5class_accuracy.png"); plt.close()

# =========================================================================
# Chart R2: Stage-wise accuracy — 4 new runs
# =========================================================================
fig, ax = plt.subplots(figsize=(10, 5))
w = 0.18; x = np.arange(len(NEW_LABELS))
ax.bar(x-1.5*w, new_stage1, w, label="Stage 1", color="#42A5F5")
ax.bar(x-0.5*w, new_stage2, w, label="Stage 2", color="#66BB6A")
ax.bar(x+0.5*w, new_stage3, w, label="Stage 3", color="#FFA726")
ax.bar(x+1.5*w, new_5class, w, label="5-Class", color="#EF5350")
ax.set_xticks(x); ax.set_xticklabels(NEW_LABELS, fontsize=9)
ax.set_ylabel("Accuracy"); ax.set_title("Round 2: Stage-wise Accuracy"); ax.set_ylim(0, 1.0)
ax.legend(fontsize=9); fig.tight_layout()
fig.savefig(OUT / "R02_stagewise_accuracy.png"); plt.close()

# =========================================================================
# Chart R3: Per-class accuracy heatmap — 4 new runs
# =========================================================================
data = np.array([new_sn, new_agn, new_vs, new_ast, new_bog])
fig, ax = plt.subplots(figsize=(9, 4.5))
im = ax.imshow(data, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)
ax.set_xticks(np.arange(len(NEW_LABELS))); ax.set_xticklabels(NEW_LABELS, fontsize=8)
ax.set_yticks(np.arange(len(classes))); ax.set_yticklabels(classes, fontsize=10)
for i in range(len(classes)):
    for j in range(len(NEW_LABELS)):
        color = "white" if data[i,j] > 0.5 else "black"
        ax.text(j, i, f"{data[i,j]:.0%}", ha="center", va="center", fontsize=10, color=color)
ax.set_title("Round 2: Per-Class Accuracy Heatmap")
fig.colorbar(im, ax=ax, shrink=0.8, label="Accuracy"); fig.tight_layout()
fig.savefig(OUT / "R03_perclass_heatmap.png"); plt.close()

# =========================================================================
# Chart R4: Per-class accuracy grouped bar — 3 models, new_prompt
# =========================================================================
fig, ax = plt.subplots(figsize=(10, 5.5))
w = 0.25; x = np.arange(len(classes))
for i, (model, color) in enumerate(zip(M3_LABELS, M3_COLORS)):
    vals = [m3_sn[i], m3_agn[i], m3_vs[i], m3_ast[i], m3_bog[i]]
    bars = ax.bar(x + (i-1)*w, vals, w, label=model, color=color, edgecolor="white")
    for b, v in zip(bars, vals):
        if v > 0: ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.01, f"{v:.0%}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(classes, fontsize=12)
ax.set_ylabel("Accuracy"); ax.set_title("Per-Class Accuracy by Model (prompts_new)")
ax.set_ylim(0, 1.12); ax.legend(fontsize=10); ax.grid(axis="y", alpha=0.2)
fig.tight_layout(); fig.savefig(OUT / "R04_perclass_3models_newprompt.png"); plt.close()

# =========================================================================
# Chart R5: Kimi across all 4 prompt versions — 5-class + stages
# =========================================================================
fig, ax = plt.subplots(figsize=(10, 5))
dims = ["Stage 1", "Stage 2", "Stage 3", "5-Class", "Macro F1"]
x_d = np.arange(len(dims))
for idx, (lbl, color) in enumerate(zip(KIMI_LABELS, KIMI_COLORS)):
    vals = [kimi_stage1[idx], kimi_stage2[idx], kimi_stage3[idx], kimi_5class[idx], kimi_macro_f1[idx]]
    ax.plot(x_d, vals, "o-", color=color, linewidth=2, markersize=7, label=lbl.replace("\n"," "))
ax.set_xticks(x_d); ax.set_xticklabels(dims, fontsize=10)
ax.set_ylabel("Score"); ax.set_title("Kimi-K2.5: Metric Progression Across 4 Prompt Versions")
ax.set_ylim(0.25, 0.85); ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.3)
fig.tight_layout(); fig.savefig(OUT / "R05_kimi_4prompts_cascade.png"); plt.close()

# =========================================================================
# Chart R6: Kimi per-class accuracy across 4 prompts
# =========================================================================
fig, ax = plt.subplots(figsize=(10, 5.5))
w = 0.2; x = np.arange(len(classes))
for i, (lbl, color) in enumerate(zip(KIMI_LABELS, KIMI_COLORS)):
    vals = [kimi_sn[i], kimi_agn[i], kimi_vs[i], kimi_ast[i], kimi_bog[i]]
    ax.bar(x + (i-1.5)*w, vals, w, label=lbl.replace("\n"," "), color=color, edgecolor="white")
ax.set_xticks(x); ax.set_xticklabels(classes, fontsize=11)
ax.set_ylabel("Accuracy"); ax.set_title("Kimi-K2.5: Per-Class Accuracy Across 4 Prompt Versions")
ax.set_ylim(0, 1.15); ax.legend(fontsize=7, ncol=2); fig.tight_layout()
fig.savefig(OUT / "R06_kimi_4prompts_perclass.png"); plt.close()

# =========================================================================
# Chart R7: Macro F1 — 4 new runs
# =========================================================================
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(np.arange(len(NEW_LABELS)), new_macro_f1, color=NEW_COLORS, edgecolor="white", width=0.6)
for b, v in zip(bars, new_macro_f1):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.005, f"{v:.3f}", ha="center", va="bottom", fontsize=10)
ax.set_xticks(np.arange(len(NEW_LABELS))); ax.set_xticklabels(NEW_LABELS, fontsize=9)
ax.set_ylabel("Macro F1"); ax.set_title("Round 2: Stage 3 Macro F1"); ax.set_ylim(0, 0.6)
fig.tight_layout(); fig.savefig(OUT / "R07_macro_f1.png"); plt.close()

# =========================================================================
# Chart R8: Asteroid accuracy — all prompt versions comparison (highlight improvement)
# =========================================================================
AST_LABELS = ["Kimi\nold_prompt", "Kimi\nprompts.py", "Kimi\nold_backup", "Kimi\nnew_prompt",
              "Q235\nprompts.py", "Q235\nnew_prompt", "Q30\nprompts.py", "Q30\nnew_prompt"]
AST_COLORS = ["#888888", "#1565C0", "#9E9E9E", "#2196F3", "#388E3C", "#4CAF50", "#E65100", "#FF9800"]
ast_vals = [0.30, 0.05, 0.20, 0.50, 0.00, 0.40, 0.00, 0.25]

fig, ax = plt.subplots(figsize=(11, 5))
bars = ax.bar(np.arange(len(AST_LABELS)), ast_vals, color=AST_COLORS, edgecolor="white", width=0.7)
for b, v in zip(bars, ast_vals):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.005, f"{v:.0%}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(np.arange(len(AST_LABELS))); ax.set_xticklabels(AST_LABELS, fontsize=8)
ax.set_ylabel("Accuracy"); ax.set_title("Asteroid Classification Accuracy Across All Runs")
ax.set_ylim(0, 0.65); fig.tight_layout()
fig.savefig(OUT / "R08_asteroid_all_runs.png"); plt.close()

# =========================================================================
# Chart R9: SN accuracy — all prompt versions
# =========================================================================
SN_LABELS = AST_LABELS
sn_vals = [0.30, 0.80, 0.45, 0.50, 0.75, 0.60, 0.85, 0.20]
fig, ax = plt.subplots(figsize=(11, 5))
bars = ax.bar(np.arange(len(SN_LABELS)), sn_vals, color=AST_COLORS, edgecolor="white", width=0.7)
for b, v in zip(bars, sn_vals):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.01, f"{v:.0%}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(np.arange(len(SN_LABELS))); ax.set_xticklabels(SN_LABELS, fontsize=8)
ax.set_ylabel("Accuracy"); ax.set_title("SN Classification Accuracy Across All Runs")
ax.set_ylim(0, 1.05); fig.tight_layout()
fig.savefig(OUT / "R09_sn_all_runs.png"); plt.close()

# =========================================================================
# Chart R10: 5-Class accuracy — all prompt versions
# =========================================================================
ALL_LABELS = AST_LABELS
acc_vals = [0.34, 0.41, 0.36, 0.42, 0.35, 0.44, 0.33, 0.25]
fig, ax = plt.subplots(figsize=(11, 5))
bars = ax.bar(np.arange(len(ALL_LABELS)), acc_vals, color=AST_COLORS, edgecolor="white", width=0.7)
for b, v in zip(bars, acc_vals):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.005, f"{v:.0%}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(np.arange(len(ALL_LABELS))); ax.set_xticklabels(ALL_LABELS, fontsize=8)
ax.set_ylabel("5-Class Accuracy"); ax.set_title("5-Class Accuracy Across All Prompt Versions")
ax.set_ylim(0, 0.55); ax.axhline(y=0.20, color="grey", linestyle="--", alpha=0.4, label="Random (20%)")
ax.legend(fontsize=9); fig.tight_layout()
fig.savefig(OUT / "R10_5class_all_runs.png"); plt.close()

# =========================================================================
# Chart R11: Radar — 3 models on new_prompt per-class accuracy
# =========================================================================
from math import pi
N = 5; angles = [n/float(N)*2*pi for n in range(N)]; angles += angles[:1]
fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
for idx, (name, color) in enumerate(zip(M3_LABELS, M3_COLORS)):
    vals = [m3_sn[idx], m3_agn[idx], m3_vs[idx], m3_ast[idx], m3_bog[idx]]
    vals += vals[:1]
    ax.plot(angles, vals, "o-", linewidth=2, label=name, color=color, markersize=5)
    ax.fill(angles, vals, alpha=0.08, color=color)
ax.set_xticks(angles[:-1]); ax.set_xticklabels(classes, fontsize=11)
ax.set_ylim(0, 1.1); ax.set_title("Model Comparison on prompts_new", fontsize=12, pad=20)
ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=10)
fig.tight_layout(); fig.savefig(OUT / "R11_radar_3models_newprompt.png", bbox_inches="tight"); plt.close()

# =========================================================================
# Chart R12: Pie — where AGN go (4 new runs)
# =========================================================================
agn_cm = {
    "Kimi old_backup":   [0, 0, 20, 0, 0],
    "Kimi new_prompt":   [0, 0, 19, 1, 0],
    "Qwen235 new_prompt":[0, 1, 19, 0, 0],
    "Qwen30 new_prompt": [0, 0, 12, 8, 0],
}
pie_colors = [CLASS_COLORS[c] for c in classes]
fig, axes = plt.subplots(1, 4, figsize=(16, 4))
for ax, (rn, preds) in zip(axes, agn_cm.items()):
    nonzero = [(classes[i], preds[i], pie_colors[i]) for i in range(5) if preds[i] > 0]
    if not nonzero:
        ax.text(0.5, 0.5, "N/A", ha="center", va="center", fontsize=14); ax.set_title(rn, fontsize=9, fontweight="bold"); continue
    lbls = [f"{n}\n({v}/20)" for n, v, _ in nonzero]
    vals = [v for _, v, _ in nonzero]; cols = [c for _, _, c in nonzero]
    ax.pie(vals, labels=lbls, colors=cols, autopct="%1.0f%%", startangle=90, textprops={"fontsize": 9})
    ax.set_title(rn, fontsize=9, fontweight="bold")
fig.suptitle("Where Do True AGN Get Classified? (Round 2)", fontsize=12, y=1.02)
fig.tight_layout(); fig.savefig(OUT / "R12_agn_pie.png", bbox_inches="tight"); plt.close()

# =========================================================================
# Chart R13: Pie — where asteroids go (4 new runs)
# =========================================================================
ast_cm = {
    "Kimi old_backup":   [7, 0, 5, 4, 4],
    "Kimi new_prompt":   [4, 0, 2, 10, 4],
    "Qwen235 new_prompt":[7, 0, 3, 8, 2],
    "Qwen30 new_prompt": [8, 0, 7, 5, 0],
}
fig, axes = plt.subplots(1, 4, figsize=(16, 4))
for ax, (rn, preds) in zip(axes, ast_cm.items()):
    nonzero = [(classes[i], preds[i], pie_colors[i]) for i in range(5) if preds[i] > 0]
    lbls = [f"{n}\n({v}/20)" for n, v, _ in nonzero]
    vals = [v for _, v, _ in nonzero]; cols = [c for _, _, c in nonzero]
    ax.pie(vals, labels=lbls, colors=cols, autopct="%1.0f%%", startangle=90, textprops={"fontsize": 9})
    ax.set_title(rn, fontsize=9, fontweight="bold")
fig.suptitle("Where Do True Asteroids Get Classified? (Round 2)", fontsize=12, y=1.02)
fig.tight_layout(); fig.savefig(OUT / "R13_asteroid_pie.png", bbox_inches="tight"); plt.close()

# =========================================================================
# Chart R14: prompts.py vs new_prompt (delta) for each model
# =========================================================================
fig, ax = plt.subplots(figsize=(8, 5))
models_delta = ["Kimi-K2.5", "Qwen3-235B", "Qwen3-30B"]
d_5class = [0.42-0.41, 0.44-0.35, 0.25-0.33]
d_sn = [0.50-0.80, 0.60-0.75, 0.20-0.85]
d_ast = [0.50-0.05, 0.40-0.00, 0.25-0.00]
d_vs = [0.95-0.95, 0.90-0.80, 0.80-0.75]
x_m = np.arange(len(models_delta)); w = 0.18
ax.bar(x_m-1.5*w, d_5class, w, label="5-Class Acc", color="#EF5350")
ax.bar(x_m-0.5*w, d_sn, w, label="SN", color="#42A5F5")
ax.bar(x_m+0.5*w, d_ast, w, label="Asteroid", color="#FFA726")
ax.bar(x_m+1.5*w, d_vs, w, label="VS", color="#66BB6A")
ax.set_xticks(x_m); ax.set_xticklabels(models_delta, fontsize=10)
ax.set_ylabel("Accuracy Change"); ax.set_title("Impact of prompts_new vs prompts.py (delta)")
ax.axhline(y=0, color="black", linewidth=0.5); ax.legend(fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "R14_newprompt_delta.png"); plt.close()

print("Round 2 charts saved:")
for f in sorted(OUT.glob("*.png")): print(f"  {f.name}")
