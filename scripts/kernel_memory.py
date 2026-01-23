import os
import numpy as np
import matplotlib.pyplot as plt

os.makedirs("assets", exist_ok=True)

def make_disturbance_decay_figure(
    out="assets/concept_disturbance_decay_metric.png",
    nyears=35,
    event_year=5,
    tau=8.0,          # decay timescale (years)
):
    t = np.arange(nyears)  # 0..nyears-1

    # Time since disturbance (TSLD)
    tsld = np.maximum(0, t - event_year)

    # Decay metric: 1 at event year, then exp(-TSLD/tau)
    metric = np.zeros_like(t, dtype=float)
    metric[t >= event_year] = np.exp(-tsld[t >= event_year] / tau)

    fig, ax = plt.subplots(1, 1, figsize=(8.6, 4.8), constrained_layout=True)

    # Metric curve
    ax.plot(t, metric, linewidth=5)
    ax.fill_between(t, metric, 0, alpha=0.18)

    # Event marker
    ax.axvline(event_year, linestyle=":", linewidth=3)
    ax.text(event_year + 0.5, 0.5, "disturbance\noccurs", va="top", fontweight="bold", fontsize=13)

    # Annotations
    ax.annotate(
        "metric = 1",
        xy=(event_year, 1.0),
        xytext=(event_year + 4, 0.92),
        arrowprops=dict(arrowstyle="->", linewidth=2),
        fontsize=12,
        fontweight="bold"
    )

    # Show tau at ~1/e point
    t_tau = int(round(event_year + tau))
    if t_tau < nyears:
        ax.scatter([t_tau], [np.exp(-1)], s=70, zorder=5)
        ax.annotate(
            r"after $\tau$ years: $e^{-1}$",
            xy=(t_tau, np.exp(-1)),
            xytext=(t_tau + 3, 0.55),
            arrowprops=dict(arrowstyle="->", linewidth=2),
            fontsize=12,
            fontweight="bold"
        )

    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Time (years)", fontsize=14)
    ax.set_ylabel("Disturbance decay metric", fontsize=14)
    ax.set_title("Disturbance memory: 1 at event, decays to 0 with time since disturbance",
                 fontsize=15, fontweight="bold")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=12)

    plt.savefig(out, dpi=220, bbox_inches="tight")
    plt.close()
    print("Wrote:", out)

if __name__ == "__main__":
    make_disturbance_decay_figure()
