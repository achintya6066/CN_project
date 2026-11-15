import csv, re, statistics

def stats(label):
    rows = list(csv.DictReader(open(f"results/{label}.csv")))
    t = [float(r["t"]) for r in rows]
    loss = [float(r["loss_pct"]) for r in rows]
    rtt = [float(r["rtt_avg_ms"]) if r["rtt_avg_ms"] else None for r in rows]
    def avg(lo, hi):
        v = [x for ti, x in zip(t, rtt) if x is not None and lo <= ti <= hi]
        return f"{statistics.mean(v):.1f} ms" if v else "no reply"
    return {
        "mean_loss": f"{sum(loss)/len(loss):.1f}%",
        "worst": f"{max(loss):.0f}%",
        "wl": f"{sum(x > 0 for x in loss)}/{len(loss)}",
        "before": avg(0, 11),
        "during": avg(14, 26),
        "after": avg(32, 999),
    }

b, d = stats("baseline"), stats("dynamic")
table = f"""| Scenario | Mean loss | Worst window loss | Windows with loss | RTT before failure | RTT during failure (s1-s2 down) | RTT after restore |
|---|---|---|---|---|---|---|
| Static baseline | {b['mean_loss']} | {b['worst']} | {b['wl']} | {b['before']} | {b['during']} | {b['after']} |
| Dynamic (SDN reroute) | {d['mean_loss']} | {d['worst']} | {d['wl']} | {d['before']} | {d['during']} | {d['after']} |
"""
print(table)
s = open("README.md").read()
new, n = re.subn(r"\| Scenario \|.*?\| Dynamic[^\n]*\n", lambda m: table, s, flags=re.S)
if n:
    open("README.md", "w").write(new)
    print(">>> README.md updated")
else:
    print(">>> Table not found in README.md, paste the table above manually")
