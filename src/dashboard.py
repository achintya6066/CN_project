#!/usr/bin/env python3
"""Small local dashboard for the latest UDP probe metrics."""
import json, os
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
METRICS = os.environ.get("NDT_METRICS_FILE", "data/latest_metrics.json")
HTML = """
<!doctype html><html><head><meta charset="utf-8"><title>Network Diagnostics</title>
<style>
body{font-family:Arial,sans-serif;background:#f2f5f8;color:#17202a;margin:35px}
main{max-width:900px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px}
.card{background:white;padding:20px;border-radius:12px;box-shadow:0 2px 10px #0001}
.big{font-size:25px;font-weight:bold}.muted{color:#667085}pre{white-space:pre-wrap}
</style></head><body><main><h1>Network Diagnostic Dashboard</h1>
<p class="muted">Latest UDP probe measurements</p>
{% if d %}<section class="grid">
<div class="card">Destination<div class="big">{{d.destination}}</div></div>
<div class="card">Packet loss<div class="big">{{d.packet_loss_percent}}%</div></div>
<div class="card">Average RTT<div class="big">{{d.rtt_avg_ms if d.rtt_avg_ms is not none else "N/A"}} ms</div></div>
<div class="card">Received / Sent<div class="big">{{d.received}} / {{d.sent}}</div></div>
</section><div class="card"><h3>RTT samples (ms)</h3><pre>{{d.rtt_samples_ms}}</pre>
<p class="muted">{{d.timestamp_utc}}</p></div>
{% else %}<div class="card">No metrics yet. Run the UDP client first.</div>{% endif %}
<div class="card"><a href="/api/metrics">Metrics JSON API</a></div></main></body></html>
"""

def read_metrics():
    try:
        with open(METRICS, encoding="utf-8") as f: return json.load(f)
    except (OSError, json.JSONDecodeError): return None

@app.route("/")
def home():
    return render_template_string(HTML, d=read_metrics())

@app.route("/api/metrics")
def api_metrics():
    return jsonify(read_metrics() or {"status": "no data"})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
