import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUT = Path("charts/fewshots")
OUT.mkdir(parents=True, exist_ok=True)

classes = ["SN", "AGN", "VS", "asteroid", "bogus"]
models = ["Kimi-K2.5", "Qwen3-235B", "Qwen3-30B"]
colors = ["#2196F3", "#4CAF50", "#FF9800"]

# Per-class accuracy (default prompt only)
sn_acc  = [0.80, 0.75, 0.85]
agn_acc = [0.00, 0.05, 0.00]
vs_acc  = [0.95, 0.80, 0.75]
ast_acc = [0.05, 0.00, 0.00]
bog_acc = [0.25, 0.15, 0.05]

fig, ax = plt.subplots(figsize=(10, 5.5))
x = np.arange(len(classes))
width = 0.25

for i, (model, color) in enumerate(zip(models, colors)):
    vals = [sn_acc[i], agn_acc[i], vs_acc[i], ast_acc[i], bog_acc[i]]
    bars = ax.bar(x + (i - 1) * width, vals, width, label=model, color=color, edgecolor="white")
    for b, v in zip(bars, vals):
        if v > 0:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01,
                    f"{v:.0%}", ha="center", va="bottom", fontsize=9)

ax.set_xticks(x)
ax.set_xticklabels(classes, fontsize=12)
ax.set_ylabel("Accuracy", fontsize=11)
ax.set_title("Per-Class Accuracy by Model (Default Prompt)", fontsize=13)
ax.set_ylim(0, 1.12)
ax.legend(fontsize=10)
ax.grid(axis="y", alpha=0.2)
fig.tight_layout()
fig.savefig(OUT / "33_perclass_accuracy_3models.png")
plt.close()
print("Saved charts/fewshots/33_perclass_accuracy_3models.png")
