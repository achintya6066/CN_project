"""Ryu OpenFlow 1.3 controller: installs flows on a chosen h1<->h2 path and
reroutes on link-down events or when the socket application reports high loss.

Run:  DYNAMIC=1 ryu-manager controller.py     (dynamic rerouting)
      DYNAMIC=0 ryu-manager controller.py     (static baseline, never reroutes)
"""
import os, json, time, socket
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub

DYNAMIC = os.environ.get("DYNAMIC", "1") == "1"
LOSS_THRESHOLD = 30.0
SOCK = "/tmp/sdn_ctrl.sock"
H1, H2 = "00:00:00:00:00:01", "00:00:00:00:00:02"
# (switch, next_switch) -> output port on switch
PORT = {(1,2):2,(2,1):1,(2,4):2,(4,2):2,(1,3):3,(3,1):1,(3,4):2,(4,3):3}
NBR = {(sw, p): n for (sw, n), p in PORT.items()}
HOSTPORT = {1: 1, 4: 1}
PATHS = {"fast": [1, 2, 4], "slow": [1, 3, 4]}    # in order of preference


class DiagController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.dps, self.current = {}, None
        self.failed, self.bad, self.last_change = set(), {}, 0
        self.down_ports = set()
        self.logger.info("Controller mode: %s", "DYNAMIC" if DYNAMIC else "STATIC BASELINE")
        hub.spawn(self._listen)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features(self, ev):
        dp = ev.msg.datapath
        self.dps[dp.id] = dp
        if len(self.dps) == 4 and self.current is None:
            self.install("fast", "initial path")

    def install(self, name, why):
        path = PATHS[name]
        for dp in self.dps.values():
            for mac in (H1, H2):
                self.delete(dp, mac)
        self.add_path(path, H2)
        self.add_path(path[::-1], H1)
        self.current, self.last_change = name, time.time()
        self.logger.info("[%s] %s -> using %s path %s", time.strftime("%H:%M:%S"), why, name, path)

    def add_path(self, path, dst_mac):
        for i, sw in enumerate(path):
            out = HOSTPORT[sw] if i == len(path) - 1 else PORT[(sw, path[i + 1])]
            dp = self.dps[sw]; p = dp.ofproto_parser
            inst = [p.OFPInstructionActions(dp.ofproto.OFPIT_APPLY_ACTIONS, [p.OFPActionOutput(out)])]
            dp.send_msg(p.OFPFlowMod(datapath=dp, priority=10,
                                     match=p.OFPMatch(eth_dst=dst_mac), instructions=inst))

    def delete(self, dp, mac):
        p, o = dp.ofproto_parser, dp.ofproto
        dp.send_msg(p.OFPFlowMod(datapath=dp, command=o.OFPFC_DELETE, out_port=o.OFPP_ANY,
                                 out_group=o.OFPG_ANY, match=p.OFPMatch(eth_dst=mac)))

    def reroute(self, why):
        if not DYNAMIC:
            self.logger.info("static mode: no reroute (%s)", why); return
        now = time.time()
        for name, path in PATHS.items():
            if any(frozenset(e) in self.failed for e in zip(path, path[1:])): continue
            if self.bad.get(name, 0) > now: continue
            if name != self.current:
                self.install(name, why)
            return
        self.logger.warning("no healthy path available")

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status(self, ev):
        msg = ev.msg; dpid = msg.datapath.id; port = msg.desc.port_no
        o = msg.datapath.ofproto
        nbr = NBR.get((dpid, port))
        if nbr is None or self.current is None: return
        down = bool(msg.desc.state & o.OFPPS_LINK_DOWN) or bool(msg.desc.config & o.OFPPC_PORT_DOWN)
        (self.down_ports.add if down else self.down_ports.discard)((dpid, port))
        self.failed = {frozenset((d, NBR[(d, p)])) for (d, p) in self.down_ports if (d, p) in NBR}
        self.logger.info("[%s] LINK s%d-s%d %s", time.strftime("%H:%M:%S"), dpid, nbr, "DOWN" if down else "UP")
        self.reroute("link s%d-s%d %s" % (dpid, nbr, "down" if down else "up"))

    def _listen(self):
        """Receives probe reports from the socket application (unix datagram socket)."""
        if os.path.exists(SOCK): os.remove(SOCK)
        s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        s.bind(SOCK); os.chmod(SOCK, 0o777)
        s.setblocking(False)
        while True:
            try:
                data, _ = s.recvfrom(4096)
            except BlockingIOError:
                hub.sleep(0.1); continue
            try:
                r = json.loads(data)
            except Exception:
                continue
            self.logger.info("probe report: loss=%s%% rtt=%s", r.get("loss_pct"), r.get("rtt_ms"))
            if (r.get("loss_pct", 0) >= LOSS_THRESHOLD and self.current
                    and time.time() - self.last_change > 5):
                self.bad[self.current] = time.time() + 30
                self.reroute("probe loss %.0f%%" % r["loss_pct"])
