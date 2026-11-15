"""Plot baseline vs dynamic results -> results/comparison.png"""
import csv, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def load(l):
    rows = list(csv.DictReader(open(f"results/{l}.csv")))
    return ([float(r["t"]) for r in rows], [float(r["loss_pct"]) for r in rows],
            [float(r["rtt_avg_ms"]) if r["rtt_avg_ms"] else float("nan") for r in rows])

fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
for l in ("baseline", "dynamic"):
    t, loss, rtt = load(l)
    ax[0].plot(t, loss, marker="o", label=l); ax[1].plot(t, rtt, marker="o", label=l)
    print(f"{l}: mean loss {sum(loss)/len(loss):.1f}% | windows with loss: {sum(x > 0 for x in loss)}/{len(loss)}")
ax[0].set_ylabel("Packet loss (%)"); ax[1].set_ylabel("Avg RTT (ms)"); ax[1].set_xlabel("Time (s)")
ax[0].legend(); ax[0].set_title("Link s1-s2 fails at ~12s, restored at ~27s")
plt.savefig("results/comparison.png", dpi=150)
print("Saved results/comparison.png")
