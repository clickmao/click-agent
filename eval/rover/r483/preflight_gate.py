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


SHELLS = ("bash", "sh", "dash", "zsh", "ash", "ksh", "busybox")


def self_and_ancestors():
    """自身 + 全部祖先进程 pid 集 (沿 PPid 链)。

    修 R484 自匹配假阳性: R483 首跑被闸, blocker 是 `rss=3MB` 的 **bash wrapper**,
    其 cmdline 只是**参数里含** `llama-server`(调用方自己的 grep 字面量) —— 被当成了作业。
    ⇒ 判据必须区分「进程**是**被监视程序」与「进程**提到**该字串」。
    """
    pids = set()
    pid = os.getpid()
    for _ in range(64):
        if pid <= 0 or pid in pids:
            break
        pids.add(pid)
        try:
            stat = Path("/proc/%d/stat" % pid).read_text()
            pid = int(stat.rsplit(")", 1)[1].split()[1])   # 跳过 comm(含空格/括号)后取 PPid
        except (OSError, IndexError, ValueError):
            break
    return pids


def scan_procs(skip_shells=True, legacy_self_only=False):
    """返回命中 WATCH 的进程 (排除自身/祖先; 默认再排除 shell 包装进程)。

    为什么排除 shell: 监视对象 (llama-server / VBCSCompiler / MSBuild / dotnet) 都是**可执行本体**,
    而 shell 只会「在参数里提到」它们 ⇒ shell 命中必为假阳性 (调用方命令字面量或日志文本)。
    `--nc-selfmatch`(legacy_self_only=True: 只排除自身、不排除祖先/shell) 即该修复的**负控** ——
    同环境只翻此开关, 须复现 R483 的 GATE_BLOCKED。
    """
    me = os.getpid()
    ancestors = {me} if legacy_self_only else self_and_ancestors()
    hits = []
    for pe in Path("/proc").iterdir():
        if not pe.name.isdigit() or int(pe.name) == me or int(pe.name) in ancestors:
            continue
        try:
            raw = (pe / "cmdline").read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        if not raw:
            continue
        cmd = raw.replace("\x00", " ").strip()
        argv0 = os.path.basename(raw.split("\x00")[0].strip())
        if skip_shells and argv0 in SHELLS:
            continue      # shell 只是「提到」被监视程序 ⇒ 假阳性 (见 --nc-selfmatch 负控)
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


def count_shell_mentions():
    """被排除的 shell 进程里「提到」监视字串的条数 (审计用: 明细可见, 但判决不受其影响)。"""
    n = 0
    for pe in Path("/proc").iterdir():
        if not pe.name.isdigit():
            continue
        try:
            raw = (pe / "cmdline").read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        if not raw:
            continue
        if os.path.basename(raw.split("\x00")[0].strip()) not in SHELLS:
            continue
        cmd = raw.replace("\x00", " ")
        if any(w in cmd for w in WATCH):
            n += 1
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--no-shutdown", action="store_true", help="跳过 build-server shutdown (对照用)")
    ap.add_argument("--settle-max", type=int, default=40, help="沉降等待上限秒")
    ap.add_argument("--gate-mb", type=int, default=GATE_MB)
    ap.add_argument("--nc-block", action="store_true", help="负控: 把门槛抬到不可达 ⇒ 须 rc=2")
    ap.add_argument("--nc-selfmatch", action="store_true",
                    help="负控(修前行为): 不排除 shell 包装进程 ⇒ 自身/旁支 shell 提到监视字串时须 rc=2")
    ap.add_argument("--round", default="R484", help="记录里的轮号标签")
    a = ap.parse_args(argv)

    dotnet = Path(os.environ.get("DOTNET_ROOT", Path.home() / ".dotnet")) / "dotnet"
    if not dotnet.is_file():
        print("MISS: 找不到 dotnet 可执行:", dotnet)
        return 3
    gate = 10 ** 6 if a.nc_block else a.gate_mb

    skip_shells = not a.nc_selfmatch
    rec = {"round": a.round, "gate_mb": gate, "shutdown_done": False, "settle_s": 0,
           "mem_available_mb": None, "blockers": [], "recent_src_writes_120s": None,
           "shell_skip": skip_shells, "legacy_self_only": a.nc_selfmatch,
           "self_ancestors": sorted(self_and_ancestors()),
           "shells_skipped_n": None}
    if not a.no_shutdown:
        try:
            subprocess.run([str(dotnet), "build-server", "shutdown"], capture_output=True, timeout=90)
            rec["shutdown_done"] = True
        except subprocess.TimeoutExpired:
            rec["shutdown_done"] = False

    t0 = time.time()
    while True:
        mem = mem_available_mb()
        procs = scan_procs(skip_shells, a.nc_selfmatch)
        blockers = [p for p in procs if p["watch"] != "dotnet"]
        if mem >= gate and not blockers:
            break
        if time.time() - t0 >= a.settle_max:
            break
        time.sleep(2)

    rec["settle_s"] = round(time.time() - t0, 1)
    rec["mem_available_mb"] = mem_available_mb()
    rec["blockers"] = [p for p in scan_procs(skip_shells, a.nc_selfmatch) if p["watch"] != "dotnet"]
    rec["shells_skipped_n"] = count_shell_mentions()
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
