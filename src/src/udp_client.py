#!/usr/bin/env python3
"""Send UDP probes; calculate round-trip time and observed packet loss."""
import argparse, json, os, socket, statistics, time
from datetime import datetime, timezone

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True)
    p.add_argument("--port", type=int, default=9999)
    p.add_argument("--count", type=int, default=20)
    p.add_argument("--interval", type=float, default=0.2)
    p.add_argument("--timeout", type=float, default=1.0)
    p.add_argument("--output", default="data/latest_metrics.json")
    p.add_argument("--report", action="store_true", help="send the result to the SDN controller (unix socket)")
    a = p.parse_args()
    if a.count < 1 or a.interval < 0 or a.timeout <= 0:
        p.error("count must be positive; interval nonnegative; timeout positive")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(a.timeout)
    samples, received = [], 0
    print(f"Probing {a.host}:{a.port} ({a.count} packets)")
    for seq in range(1, a.count + 1):
        payload = f"NDT|{seq}|{time.time_ns()}".encode()
        start = time.perf_counter()
        try:
            sock.sendto(payload, (a.host, a.port))
            reply, _ = sock.recvfrom(2048)
            if reply == payload:
                ms = (time.perf_counter() - start) * 1000
                samples.append(ms); received += 1
                print(f"Reply seq={seq}: RTT={ms:.3f} ms")
            else:
                print(f"Unexpected response for seq={seq}")
        except socket.timeout:
            print(f"Timeout seq={seq}")
        except OSError as e:
            print(f"Network error seq={seq}: {e}")
        if seq < a.count:
            time.sleep(a.interval)
    sock.close()
    lost = a.count - received
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "destination": a.host, "port": a.port, "sent": a.count,
        "received": received, "lost": lost,
        "packet_loss_percent": round(lost / a.count * 100, 2),
        "rtt_min_ms": round(min(samples), 3) if samples else None,
        "rtt_avg_ms": round(statistics.mean(samples), 3) if samples else None,
        "rtt_max_ms": round(max(samples), 3) if samples else None,
        "rtt_samples_ms": [round(x, 3) for x in samples]
    }
    os.makedirs(os.path.dirname(a.output) or ".", exist_ok=True)
    with open(a.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nSent={a.count} Received={received} Lost={lost}")
    print(f"Observed packet loss={result['packet_loss_percent']}%")
    print(f"RTT min/avg/max={result['rtt_min_ms']}/{result['rtt_avg_ms']}/{result['rtt_max_ms']} ms")
    print(f"Saved: {a.output}")
    if a.report:
        try:
            c = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            c.sendto(json.dumps({"dst": a.host, "loss_pct": result["packet_loss_percent"],
                                 "rtt_ms": result["rtt_avg_ms"]}).encode(), "/tmp/sdn_ctrl.sock")
            print("Reported to controller")
        except OSError as e:
            print(f"Could not report to controller: {e}")

if __name__ == "__main__":
    main()
