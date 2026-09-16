#!/usr/bin/env python3
"""R491 候选②⑥: 陈旧残留进程 (orphan) 收口 —— 起手闸内存阈值与残留进程的关系专项。

语言无关: 只做 /proc 事实判定, 不涉及任何语言分支/文件后缀。

**R491 首次真跑的假阳性 (器具自身的教训, 全部保留在 rack 里)**:
  初版 O2 写「PPid 不在自身/祖先链上」、O3 写「累计 CPU == 0」⇒ 4 个真残留全被判 REFUSE:
    · O2 假阳性真因: 夹具进程被 **hermes gateway (pid 1140, PR_SET_CHILD_SUBREAPER)** 收养,
      而 gateway 恰是**本会话的祖先** ⇒ 判据把「收养者」误认成「驱动者」。
    · O3 假阳性真因: 这些进程**起跑时确实干过活** (R489 在体差分 22..25 tick) ⇒ 「累计 tick != 0」
      不等于「现在在跑」。语义应是「**窗口内无活动**」。
  修法 = O2' 只拒「父亲是**本轮的活跃驱动者**」(cmdline 命中驱动器模式) + O3' **3 秒采样窗**内 CPU tick 与
  ESTABLISHED socket 双零 + O4' cwd 悬空或落在**非本轮**的 run 目录。

判据 (fail-closed, 任一不满足即 REFUSE, 只打印不杀):
  T1 命中目标集合 (agenthost --frontend-api <port∈白名单> / python3 /tmp/cxprobe/stub*.py / --lsp 显式开启时的 LSP 孤儿);
  T2 自身及全部祖先链上的 pid 永不杀 (R483/R484 教训: 禁 pgrep -f 直喂 kill);
  T3 采样窗 (默认 3 s) 内 CPU tick 增量 == 0 **且** ESTABLISHED == 0;
  T4 父亲 cmdline **不**命中活跃驱动器模式 (run_arm|run_rest|drive_task|relay_real|preflight|stub driver);
  T5 cwd 悬空, 或 cwd 落在 eval/rover/<rN>/(run-|rundata-) 且 rN != 本轮轮号;
  T6 已运行 > 60 s (刚起的作业不碰)。

用法:
  python3 reap_orphans.py --scan
  python3 reap_orphans.py --apply --out <json> [--lsp] [--window 3]
退出码: 0 干净 / 1 apply 后仍有残留 / 2 存在 REFUSE 项 (未收)。
"""
import argparse
import json
import os
import re
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RND = "r491"
DRIVER_RE = re.compile(r"run_arm|run_rest|drive_task|relay_real|preflight_gate|teardown_assert")
STUB_RE = re.compile(r"/tmp/cxprobe/stub2?\.py")
LSP_RE = re.compile(r"pyright-langserver|langserver")
BUILD_NODE_RE = re.compile(r"MSBuild\.dll")


def _read(path):
    try:
        return Path(path).read_text()
    except OSError:
        return ""


def stat_of(pid):
    raw = _read("/proc/%d/stat" % pid)
    if not raw:
        return None
    r = raw.rsplit(")", 1)[1].split()
    return {"state": r[0], "ppid": int(r[1]), "ticks": int(r[11]) + int(r[12])}


def cmdline(pid):
    try:
        return Path("/proc/%d/cmdline" % pid).read_bytes().decode("utf-8", "replace").replace("\0", " ").strip()
    except OSError:
        return ""


def rss_kb(pid):
    for l in _read("/proc/%d/status" % pid).splitlines():
        if l.startswith("VmRSS:"):
            return int(l.split()[1])
    return 0


def started_secs(pid):
    """/proc/<pid>/stat field 22 (starttime, ticks since boot) → 相对 uptime 的秒数。"""
    raw = _read("/proc/%d/stat" % pid)
    upt = _read("/proc/uptime")
    if not raw or not upt:
        return -1
    try:
        start = int(raw.rsplit(")", 1)[1].split()[19])
        hz = os.sysconf("SC_CLK_TCK")
        return int(float(upt.split()[0]) - start / hz)
    except (ValueError, IndexError):
        return -1


def self_and_ancestors():
    pids, pid = set(), os.getpid()
    for _ in range(64):
        if pid <= 0 or pid in pids:
            break
        pids.add(pid)
        st = stat_of(pid)
        if not st:
            break
        pid = st["ppid"]
    return pids


def established(pid):
    fd_dir = "/proc/%d/fd" % pid
    if not os.path.isdir(fd_dir):
        return 0
    inodes = set()
    for fd in os.listdir(fd_dir):
        try:
            t = os.readlink(os.path.join(fd_dir, fd))
        except OSError:
            continue
        m = re.match(r"socket:\[(\d+)\]", t)
        if m:
            inodes.add(m.group(1))
    if not inodes:
        return 0
    n = 0
    for f in ("/proc/net/tcp", "/proc/net/tcp6"):
        for ln in _read(f).splitlines()[1:]:
            p = ln.split()
            if len(p) > 9 and p[9] in inodes and p[3] == "01":
                n += 1
    return n


def is_target(pid, cmd, ports, lsp, cwd=""):
    if "agenthost" in cmd:
        m = re.search(r"--frontend-api\s+(\d+)", cmd)
        if m and int(m.group(1)) in ports:
            return "agenthost:%s" % m.group(1)
    # stub 的 cmdline 是相对路径 (`python3 stub.py 48510`, cwd=/tmp/cxprobe) ⇒ 需 cwd 参与判定
    if STUB_RE.search(cmd) or (re.search(r"\bstub2?\.py\b", cmd) and "cxprobe" in cwd):
        return "cxprobe_stub"
    if lsp and LSP_RE.search(cmd):
        return "lsp_orphan"
    # R491 候选⑥: build-server 残留节点 —— 实测 `dotnet build-server shutdown` 报 done 后
    # pid 1774221 (`MSBuild.dll /nodemode:1 /nodeReuse:true`, RSS 178 MB) 仍存活, 起手闸据此判红
    # (blocker_causes 同报「内存不足」+「build-server 残留」⇒ 归因不唯一)。同一套 T2..T6 判据收口。
    if BUILD_NODE_RE.search(cmd):
        return "msbuild_node"
    return ""


def mem_available_mb():
    for line in _read("/proc/meminfo").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    return -1


def inventory(ports, lsp):
    me = self_and_ancestors()
    rows = []
    for e in os.listdir("/proc"):
        if not e.isdigit():
            continue
        pid = int(e)
        if pid in me:
            continue
        cmd = cmdline(pid)
        if not cmd:
            continue
        try:
            _cwd = os.readlink("/proc/%d/cwd" % pid)
        except OSError:
            _cwd = ""
        kind = is_target(pid, cmd, ports, lsp, _cwd)
        if not kind:
            continue
        st = stat_of(pid)
        if not st:
            continue
        rows.append({"pid": pid, "kind": kind, "cmd": cmd[:200], "ppid": st["ppid"],
                     "ppid_cmd": cmdline(st["ppid"])[:160], "rss_kb": rss_kb(pid),
                     "ticks_at_t0": st["ticks"], "established": established(pid),
                     "cwd": "", "age_s": started_secs(pid)})
    # 采样窗
    return rows


def finalize(rows, window, rnd):
    for r in rows:
        try:
            r["cwd"] = os.readlink("/proc/%d/cwd" % r["pid"])
        except OSError:
            r["cwd"] = ""
    time.sleep(window)
    reasons_map = {}
    for r in rows:
        st = stat_of(r["pid"])
        if st is None:
            r["verdict"] = "GONE"
            continue
        r["ticks_after_window"] = st["ticks"]
        r["established_after_window"] = established(r["pid"])
        reasons = []
        ppid_cmd = r["ppid_cmd"]
        if DRIVER_RE.search(ppid_cmd):
            reasons.append("T4_ppid_is_live_driver")
        if st["ticks"] - r["ticks_at_t0"] != 0 or r["established_after_window"] != 0:
            reasons.append("T3_activity_in_window(ticks+%d,est=%d)" % (st["ticks"] - r["ticks_at_t0"], r["established_after_window"]))
        cwd = r["cwd"]
        cwd_gone = (cwd == "" or not os.path.exists(cwd))
        m = re.search(r"/eval/rover/(r\d+)/", cwd)
        cwd_foreign_round = bool(m) and m.group(1) != rnd
        cwd_exempt = r["kind"] == "msbuild_node" and (cwd in (str(ROOT), "", "/", str(Path.home() / ".dotnet")) or cwd.startswith(str(Path.home() / ".dotnet")))   # 构建节点 cwd=SDK/仓库根
        if not (cwd_gone or cwd_foreign_round or cwd_exempt):
            reasons.append("T5_cwd_live_same_round:%s" % cwd)
        r["cwd_exempt"] = cwd_exempt
        if r["age_s"] >= 0 and r["age_s"] < 60:
            reasons.append("T6_too_young(%ds)" % r["age_s"])
        r["cwd_gone"] = cwd_gone
        r["cwd_foreign_round"] = cwd_foreign_round
        r["reasons"] = reasons
        r["verdict"] = "ORPHAN_REAPABLE" if not reasons else "REFUSE"
        reasons_map[r["pid"]] = r["verdict"]
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--ports", default="48960,48961,48962,48963")
    ap.add_argument("--window", type=int, default=3)
    ap.add_argument("--lsp", action="store_true", help="同时把闲置 LSP 孤儿纳入 (惰性可重建, R489 先例)")
    ap.add_argument("--round", default=RND)
    a = ap.parse_args(argv)
    ports = [int(x) for x in a.ports.split(",") if x.strip()]
    mem0 = mem_available_mb()
    rows = inventory(ports, a.lsp)
    rows = finalize(rows, a.window, a.round)
    killable = [r for r in rows if r["verdict"] == "ORPHAN_REAPABLE"]
    refused = [r for r in rows if r["verdict"] == "REFUSE"]
    killed = []
    if a.apply:
        for r in killable:
            try:
                os.kill(r["pid"], signal.SIGTERM)
                killed.append(r["pid"])
            except OSError as e:
                r["kill_error"] = str(e)
        time.sleep(1.5)
        for pid in killed:
            st = stat_of(pid)
            if st is not None:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        time.sleep(1.0)
    rows2 = inventory(ports, a.lsp)
    led = {
        "round": a.round.upper(), "generated_at": time.strftime("%F %T%z"), "mode": "apply" if a.apply else "scan",
        "mem_available_mb_before": mem0, "mem_available_mb_after": mem_available_mb(),
        "criteria": {"T2": "self+ancestors never killed", "T3": "window=%ds ticks delta 0 AND established 0" % a.window,
                     "T4": "ppid cmdline not a live driver", "T5": "cwd dangling or foreign round", "T6": "age >= 60s"},
        "false_positives_of_first_pass": [
            "T2'='ppid not in self chain' 假阳性: 收养者=hermes gateway(1140) 是自身祖先",
            "T3'='lifetime ticks == 0' 假阳性: R489 在体差分已产生 22..25 tick",
        ],
        "before": rows, "after": rows2,
        "killed_pids": killed, "rss_kb_reaped": sum(r["rss_kb"] for r in killable),
        "refused_pids": [r["pid"] for r in refused],
    }
    if a.out:
        Path(a.out).write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: led[k] for k in ("mem_available_mb_before", "mem_available_mb_after", "rss_kb_reaped",
                                         "killed_pids", "refused_pids")}, ensure_ascii=False))
    for r in rows:
        print("  %-16s pid=%-8d rss=%6dKB age=%5ds est=%d %-16s %s | %s" % (
            r["verdict"], r["pid"], r["rss_kb"], r["age_s"], r["established"], r["kind"],
            ",".join(r.get("reasons", [])) or "-", r["cmd"][:80]))
    print("[after] 仍命中目标集合: %d 项" % len(rows2))
    if refused:
        return 2
    if a.apply and rows2:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
