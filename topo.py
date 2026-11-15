"""Mininet topology: h1 - s1 =(fast s2 | slow s3)= s4 - h2, remote Ryu controller.
  sudo python3 topo.py                  -> interactive CLI
  sudo python3 topo.py auto <label>     -> automated link-failure experiment
"""
import sys, time, os
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")

net = Mininet(controller=RemoteController, link=TCLink, switch=OVSSwitch)
net.addController("c0", ip="127.0.0.1", port=6653)
h1 = net.addHost("h1", ip="10.0.0.1/24", mac="00:00:00:00:00:01")
h2 = net.addHost("h2", ip="10.0.0.2/24", mac="00:00:00:00:00:02")
s1, s2, s3, s4 = [net.addSwitch(f"s{i}", protocols="OpenFlow13", failMode="secure") for i in range(1, 5)]
net.addLink(h1, s1, port2=1)
net.addLink(h2, s4, port2=1)
net.addLink(s1, s2, port1=2, port2=1, delay="5ms")    # fast path
net.addLink(s2, s4, port1=2, port2=2, delay="5ms")
net.addLink(s1, s3, port1=3, port2=1, delay="20ms")   # slow path
net.addLink(s3, s4, port1=2, port2=3, delay="20ms")
net.start()
net.waitConnected()
h1.cmd("arp -s 10.0.0.2 00:00:00:00:00:02")
h2.cmd("arp -s 10.0.0.1 00:00:00:00:00:01")
time.sleep(2)
net.pingAll()

if len(sys.argv) > 2 and sys.argv[1] == "auto":
    label = sys.argv[2]
    res = os.path.join(ROOT, "results"); os.makedirs(res, exist_ok=True)
    h2.cmd(f"python3 {SRC}/udp_server.py &")
    time.sleep(1)
    h1.cmd(f"python3 {SRC}/probe_monitor.py 10.0.0.2 45 {res}/{label}.csv > {res}/{label}.log 2>&1 &")
    time.sleep(12); print(">>> FAILING link s1-s2");  net.configLinkStatus("s1", "s2", "down")
    time.sleep(15); print(">>> RESTORING link s1-s2"); net.configLinkStatus("s1", "s2", "up")
    time.sleep(20)
else:
    CLI(net)
net.stop()
