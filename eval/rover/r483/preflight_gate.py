#!/usr/bin/env python3
"""R483: 真机测量起手闸 (器具化) —— R482 红闸误归因的直接修复。

语言无关: 只做进程/内存/工作树事实判定, 不涉及任何语言或文件后缀分支。
背景: R482 R 臂首跑 `MemAvailable=2590 < 2650` 被闸, 沉降等待后仍红, 真因是
      本方 `dotnet test` 遗留的 `VBCSCompiler` (RSS ~206 MB)。 ⇒ 起手前必须
      先 shutdown 构建服务器再判定, 否则闸会给出"环境不足"的假归因。
三态: rc=0 PASS / rc=2 GATE_BLOCKED (给阻塞物清单) / rc=3 MISS (缺 dotnet 可执行)。
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "eval" / "rover" / "r483" / "preflight.json"
GATE_MB = 2650
WATCH = ("llama-server", "VBCSCompiler", "MSBuild", "dotnet")


def mem_available_mb():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    return -1


def scan_procs():
    """返回 [(pid, name, rss_mb)]: 命中 WATCH 的进程 (排除自身)。"""
    me = os.getpid()
    hits = []
    for pe in Path("/proc").iterdir():
        if not pe.name.isdigit() or int(pe.name) == me:
            continue
        try:
            raw = (pe / "cmdline").read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        if not raw:
            continue
        cmd = raw.replace("\x00", " ").strip()
        for w in WATCH:
            if w in cmd:
                try:
                    rss = int([l for l in (pe / "status").read_text().splitlines()
                               if l.startswith("VmRSS:")][0].split()[1]) // 1024
                except (OSError, IndexError):
                    rss = -1
                hits.append({"pid": int(pe.name), "watch": w, "rss_mb": rss, "cmd": cmd[:120]})
                break
    return hits


def recent_src_writes(window_s):
    now = time.time()
    n = 0
    for p in (ROOT / "src").rglob("*"):
        try:
            if p.is_file() and now - p.stat().st_mtime <= window_s:
                n += 1
        except OSError:
            continue
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--no-shutdown", action="store_true", help="跳过 build-server shutdown (对照用)")
    ap.add_argument("--settle-max", type=int, default=40, help="沉降等待上限秒")
    ap.add_argument("--gate-mb", type=int, default=GATE_MB)
    ap.add_argument("--nc-block", action="store_true", help="负控: 把门槛抬到不可达 ⇒ 须 rc=2")
    a = ap.parse_args(argv)

    dotnet = Path(os.environ.get("DOTNET_ROOT", Path.home() / ".dotnet")) / "dotnet"
    if not dotnet.is_file():
        print("MISS: 找不到 dotnet 可执行:", dotnet)
        return 3
    gate = 10 ** 6 if a.nc_block else a.gate_mb

    rec = {"round": "R483", "gate_mb": gate, "shutdown_done": False, "settle_s": 0,
           "mem_available_mb": None, "blockers": [], "recent_src_writes_120s": None}
    if not a.no_shutdown:
        try:
            subprocess.run([str(dotnet), "build-server", "shutdown"], capture_output=True, timeout=90)
            rec["shutdown_done"] = True
        except subprocess.TimeoutExpired:
            rec["shutdown_done"] = False

    t0 = time.time()
    while True:
        mem = mem_available_mb()
        procs = scan_procs()
        blockers = [p for p in procs if p["watch"] != "dotnet"]
        if mem >= gate and not blockers:
            break
        if time.time() - t0 >= a.settle_max:
            break
        time.sleep(2)

    rec["settle_s"] = round(time.time() - t0, 1)
    rec["mem_available_mb"] = mem_available_mb()
    rec["blockers"] = [p for p in scan_procs() if p["watch"] != "dotnet"]
    rec["recent_src_writes_120s"] = recent_src_writes(120)
    ok = rec["mem_available_mb"] >= gate and not rec["blockers"]
    rec["verdict"] = "PASS" if ok else "GATE_BLOCKED"
    if not ok:
        rec["blocker_cause"] = ("build-server 残留" if any(p["watch"] in ("VBCSCompiler", "MSBuild")
                                                          for p in rec["blockers"]) else
                                "内存不足" if rec["mem_available_mb"] < gate else "其他进程")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(rec, ensure_ascii=False))
    print("out", a.out)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
