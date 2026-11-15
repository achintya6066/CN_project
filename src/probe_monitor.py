#!/usr/bin/env python3
"""Continuous UDP prober. Every window of 10 probes it logs loss/RTT/jitter to CSV
and reports the window to the SDN controller over a unix datagram socket.
Usage: python3 probe_monitor.py <dst_ip> [duration_s] [out.csv]"""
import socket, struct, time, sys, json, csv, os, statistics

dst = sys.argv[1]
duration = int(sys.argv[2]) if len(sys.argv) > 2 else 40
out = sys.argv[3] if len(sys.argv) > 3 else "results/manual.csv"
CTRL = "/tmp/sdn_ctrl.sock"

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(0.3)
ctl = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
f = open(out, "w", newline=""); w = csv.writer(f)
w.writerow(["t", "loss_pct", "rtt_avg_ms", "jitter_ms"])
start = time.time(); seq = 0
while time.time() - start < duration:
    rtts, lost = [], 0
    for _ in range(10):
        seq += 1; t0 = time.perf_counter()
        s.sendto(struct.pack("!I", seq), (dst, 9999))
        try:
            while True:
                d, _ = s.recvfrom(1024)
                if struct.unpack("!I", d[:4])[0] == seq:
                    rtts.append((time.perf_counter() - t0) * 1000); break
        except socket.timeout:
            lost += 1
        time.sleep(0.1)
    loss = 100.0 * lost / 10
    avg = statistics.mean(rtts) if rtts else None
    jit = statistics.pstdev(rtts) if len(rtts) > 1 else 0
    t = round(time.time() - start, 1)
    print(f"t={t}s loss={loss}% rtt={avg} jitter={jit}", flush=True)
    w.writerow([t, loss, round(avg, 2) if avg else "", round(jit, 2)]); f.flush()
    try:
        ctl.sendto(json.dumps({"dst": dst, "loss_pct": loss, "rtt_ms": avg}).encode(), CTRL)
    except OSError:
        pass
