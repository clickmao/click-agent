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

# R491 候选⑥: 起手闸内存阈值 × **陈旧 build 节点残留**。
# 本机实测 (2026-09-16): `dotnet build-server shutdown` 返回成功且 rec.shutdown_done=True,
# 但 pid 1774221 (`MSBuild.dll /nodemode:1 /nodeReuse:true`, RSS 178 MB, 年龄 2202 s) 仍存活
# ⇒ 闸只能红 (MemAvailable 2610 < 2650), 且归因面并列两条 (内存不足 + build-server 残留)。
# ⇒ 闸的「shutdown」不是收口面: 需按只读 /proc 事实 fail-closed 收口, 否则闸会把
#   陈旧残留报成「环境不足」(即 R482 那类假归因的第二次现身)。
REAP_MIN_AGE_S = 60.0        # O2: 节点年龄下限 —— 年轻节点可能正被 live 构建使用 ⇒ 拒收
REAP_IDLE_SAMPLE_S = 3.0     # O3: 静默采样窗, 累计 CPU 零增量才算闲置
BUILD_NODE_WATCH = ("VBCSCompiler", "MSBuild")
DRIVER_WORDS = ("run_arm_real_", "run_rest_", "dotnet test", "dotnet publish",
                "agentframework.tests.csproj")

# R557: 自身工具子进程 (宿主会话按需拉起的语言服务) —— 起手闸内存面的**自排除闭合**。
# 背景 (R556 §4 已登记、R557 复现): 闸红给出 "内存不足", 而 MemAvailable 被压低的原因是本侧宿主
#   (gateway) 按需拉起的 `bash-language-server` (实测 RSS 168 MB, 年龄 67 s)。
#   它不是「对侧作业/未知竞争负载」, 而是本侧可停驻、按需自动重启的工具进程 ⇒ 与 build 节点收口同族
#   (R491 ⑥: shutdown 不是收口面 ⇒ 需按只读 /proc 事实 fail-closed 收口)。
#   **判据必须绑定血统**: 只收口「PPid 链可达本闸自身血统 (self_and_ancestors)」的进程 —— 别的作业
#   拉起的同类服务不属于本闸的收口面 (拒收并逐条记因)。
#   负控: `--keep-own-tools` ⇒ 复现修前行为 (有工具进程且内存不足时须仍 GATE_BLOCKED)。
#   收口面刻意**不含**执行内核类进程 (hermes_kernel_*): 它们是本会话的执行面, 停驻会造成额外扰动;
#   且实测不收起也已足够越过门槛 (168 MB ≫ 余量缺额 46 MB)。
OWN_TOOL_WATCH = ("bash-language-server", "pyright", "pylsp", "typescript-language-server",
                  "yaml-language-server", "json-language-server", "lua-language-server",
                  "vscode-languageserver", "rust-analyzer", "gopls")
# 解释器托管的语言服务 (实测: `node .../pyright-langserver --stdio` ⇒ argv0='node') ⇒ 词面在 argv[1..]。
# 与「shell 只是提到字串」的旧假阳性不同: 此处 argv[1] **就是**工具本体路径, 且另有血统闸 (T2) 兜底。
INTERP_ARGV0 = ("node", "nodejs", "python", "python3", "deno", "bun", "dotnet")


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


def rss_of(pid):
    try:
        return int([l for l in Path("/proc/%d/status" % pid).read_text().splitlines()
                    if l.startswith("VmRSS:")][0].split()[1]) // 1024
    except (OSError, IndexError):
        return -1


def _stat_after_comm(pid):
    """`/proc/<pid>/stat` 去掉 comm(可含空格/括号) 后的字段表。"""
    return Path("/proc/%d/stat" % pid).read_text().rsplit(")", 1)[1].split()


def _cpu_ticks(pid):
    """累计 CPU 刻度 (utime+stime); 读不到返回 None (fail-closed: None ⇒ 拒收)。"""
    try:
        f = _stat_after_comm(pid)
        return int(f[11]) + int(f[12])
    except (OSError, IndexError, ValueError):
        return None


def _age_s(pid):
    """进程年龄(秒) = now - (btime + starttime/CLK_TCK)。读不到返回 None。"""
    try:
        start = int(_stat_after_comm(pid)[19])
        bt = int([l for l in Path("/proc/stat").read_text().splitlines()
                  if l.startswith("btime")][0].split()[1])
        return max(0.0, time.time() - (bt + start / os.sysconf("SC_CLK_TCK")))
    except (OSError, IndexError, ValueError, KeyError):
        return None


def _listening_inodes():
    """全系统 LISTEN 套接字 inode 集 (tcp/tcp6)。"""
    inos = set()
    for f in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            lines = Path(f).read_text().splitlines()[1:]
        except OSError:
            continue
        for l in lines:
            p = l.split()
            if len(p) > 9 and p[3] == "0A":
                inos.add(p[9])
    return inos


def _pid_listening(pid, listen_inodes):
    try:
        fds = list(Path("/proc/%d/fd" % pid).iterdir())
    except OSError:
        return False
    for fd in fds:
        try:
            t = os.readlink(fd)
        except OSError:
            continue
        if t.startswith("socket:[") and t[8:-1] in listen_inodes:
            return True
    return False


def _has_live_driver_ancestor(pid, max_hops=8):
    """O5: PPid 链上存在本轮作业驱动器 ⇒ 该节点可能正被使用, 拒收。"""
    cur = pid
    for _ in range(max_hops):
        try:
            ppid = int(_stat_after_comm(cur)[1])
        except (OSError, IndexError, ValueError):
            return False
        if ppid <= 1:
            return False
        try:
            cmd = Path("/proc/%d/cmdline" % ppid).read_bytes().decode("utf-8", "replace").replace("\x00", " ")
        except OSError:
            return False
        if any(w in cmd for w in DRIVER_WORDS):
            return True
        cur = ppid
    return False


def reap_stale_build_nodes(min_age_s=REAP_MIN_AGE_S, sample_s=REAP_IDLE_SAMPLE_S):
    """R491 候选⑥: 按**只读 /proc 事实** fail-closed 收口陈旧 build 节点。

    判据 (任一不满足 ⇒ 拒收, 不杀):
      O1 本体是 build 节点 (argv0 非 shell, cmdline 命中 BUILD_NODE_WATCH);
      O2 年龄 ≥ min_age_s;
      O3 静默: 采样窗内累计 CPU 零增量;
      O4 不持有监听套接字;
      O5 PPid 链上无本轮作业驱动器。
    返回 {candidates, reaped[], refused[{...,reasons[]}]} —— 拒收原因必须逐条可审计。
    """
    listen = _listening_inodes()
    me, anc = os.getpid(), self_and_ancestors()
    cands, t0 = [], {}
    for pe in Path("/proc").iterdir():
        if not pe.name.isdigit():
            continue
        pid = int(pe.name)
        if pid == me or pid in anc:
            continue
        try:
            cmd = pe.joinpath("cmdline").read_bytes().decode("utf-8", "replace").replace("\x00", " ").strip()
        except OSError:
            continue
        if not cmd:
            continue
        if os.path.basename(cmd.split(" ")[0]) in SHELLS:
            continue
        if not any(w in cmd for w in BUILD_NODE_WATCH):
            continue
        t0[pid] = _cpu_ticks(pid)
        cands.append({"pid": pid, "cmd": cmd[:120], "age_s": _age_s(pid), "rss_mb": rss_of(pid),
                      "listening": _pid_listening(pid, listen)})
    time.sleep(sample_s)
    reaped, refused = [], []
    for c in cands:
        pid = c["pid"]
        c1 = _cpu_ticks(pid)
        c0 = t0.get(pid)
        reasons = []
        if c0 is None or c1 is None:
            reasons.append("O3_CPU读数不可得")
        elif c1 != c0:
            reasons.append("O3_CPU活跃(%d→%d)" % (c0, c1))
        if c["age_s"] is None or c["age_s"] < min_age_s:
            reasons.append("O2_年龄不足(%.0fs<%.0fs)" % (c["age_s"] or -1.0, min_age_s))
        if c["listening"]:
            reasons.append("O4_持有监听套接字")
        if _has_live_driver_ancestor(pid):
            reasons.append("O5_本轮驱动器在世")
        if reasons:
            refused.append(dict(c, reasons=reasons))
            continue
        try:
            os.kill(pid, 15)
            time.sleep(1.0)
            try:
                os.kill(pid, 0)
                os.kill(pid, 9)
                time.sleep(0.5)
            except OSError:
                pass
            reaped.append(c)
        except OSError as e:
            refused.append(dict(c, reasons=["O6_信号失败:%s" % e]))
    return {"min_age_s": min_age_s, "sample_s": sample_s, "candidates": len(cands),
            "reaped": reaped, "refused": refused}


def _in_own_lineage(pid, own, max_hops=12):
    """pid 的 PPid 链是否可达 `own` (本闸自身血统) —— 只认血统, 不认「同名同形」。"""
    cur = pid
    for _ in range(max_hops):
        try:
            ppid = int(_stat_after_comm(cur)[1])
        except (OSError, IndexError, ValueError):
            return False
        if ppid <= 1:
            return False
        if ppid in own:
            return True
        cur = ppid
    return False


def reap_own_tool_children(min_age_s=REAP_MIN_AGE_S, sample_s=REAP_IDLE_SAMPLE_S):
    """R557: 收口**本侧宿主**按需拉起的工具子进程 (语言服务), 使内存面判据不被自身工具压低。

    判据 (任一不满足 ⇒ 拒收, 不杀 —— 与 build 节点收口同形, 原因逐条可审计):
      T1 本体 ∈ OWN_TOOL_WATCH 且 argv0 非 shell;
      T2 PPid 链可达本闸自身血统 (self_and_ancestors) ⇒ 属本侧工具, 非对侧作业;
      T3 年龄 ≥ min_age_s; T4 采样窗内累计 CPU 零增量;
      T5 不持有监听套接字; T6 PPid 链上无本轮作业驱动器。
    """
    listen = _listening_inodes()
    me, anc = os.getpid(), self_and_ancestors()
    cands, t0 = [], {}
    for pe in Path("/proc").iterdir():
        if not pe.name.isdigit():
            continue
        pid = int(pe.name)
        if pid == me or pid in anc:
            continue
        try:
            raw = (pe / "cmdline").read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        if not raw:
            continue
        cmd = raw.replace("\x00", " ").strip()
        argv0 = os.path.basename(raw.split("\x00")[0].strip())
        if argv0 in SHELLS:
            continue
        tool = argv0 if argv0 in OWN_TOOL_WATCH else None
        if tool is None and argv0 in INTERP_ARGV0:
            tool = next((w for w in OWN_TOOL_WATCH if w in cmd), None)
        if tool is None:
            continue
        if not _in_own_lineage(pid, anc):
            continue
        t0[pid] = _cpu_ticks(pid)
        cands.append({"pid": pid, "tool": tool, "argv0": argv0, "cmd": cmd[:120], "age_s": _age_s(pid),
                      "rss_mb": rss_of(pid), "listening": _pid_listening(pid, listen)})
    time.sleep(sample_s)
    reaped, refused = [], []
    for c in cands:
        pid = c["pid"]
        c1, c0 = _cpu_ticks(pid), t0.get(pid)
        reasons = []
        if c0 is None or c1 is None:
            reasons.append("T4_CPU读数不可得")
        elif c1 != c0:
            reasons.append("T4_CPU活跃(%d→%d)" % (c0, c1))
        if c["age_s"] is None or c["age_s"] < min_age_s:
            reasons.append("T3_年龄不足(%.0fs<%.0fs)" % (c["age_s"] or -1.0, min_age_s))
        if c["listening"]:
            reasons.append("T5_持有监听套接字")
        if _has_live_driver_ancestor(pid):
            reasons.append("T6_本轮驱动器在世")
        if reasons:
            refused.append(dict(c, reasons=reasons))
            continue
        try:
            os.kill(pid, 15)
            time.sleep(1.0)
            try:
                os.kill(pid, 0)
                os.kill(pid, 9)
                time.sleep(0.5)
            except OSError:
                pass
            reaped.append(c)
        except OSError as e:
            refused.append(dict(c, reasons=["T7_信号失败:%s" % e]))
    return {"min_age_s": min_age_s, "sample_s": sample_s, "candidates": len(cands),
            "reaped": reaped, "refused": refused,
            "note": "本侧工具进程可停驻, 宿主按需自动重启; 判据绑血统 (PPid 链达 self_and_ancestors)"}


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
    ap.add_argument("--nc-both", action="store_true",
                    help="负控(候选④): 门槛抬到不可达 + 不排除 shell ⇒ mem 因与 proc 因**同时**成立, "
                         "须并列报出 2 条 (禁二选一)")
    ap.add_argument("--round", default="R484", help="记录里的轮号标签")
    ap.add_argument("--keep-stale-nodes", action="store_true",
                    help="对照/负控(R491 ⑥): 不收口陈旧 build 节点 ⇒ 复现修前行为, 有残留时须 rc=2")
    ap.add_argument("--keep-own-tools", action="store_true",
                    help="对照/负控(R557): 不收口本侧工具子进程 (语言服务) ⇒ 复现修前行为, "
                         "工具进程压低内存时须仍 GATE_BLOCKED")
    a = ap.parse_args(argv)

    dotnet = Path(os.environ.get("DOTNET_ROOT", Path.home() / ".dotnet")) / "dotnet"
    if not dotnet.is_file():
        print("MISS: 找不到 dotnet 可执行:", dotnet)
        return 3
    gate = 10 ** 6 if (a.nc_block or a.nc_both) else a.gate_mb

    skip_shells = not (a.nc_selfmatch or a.nc_both)
    rec = {"round": a.round, "gate_mb": gate, "shutdown_done": False, "settle_s": 0,
           "mem_available_mb": None, "blockers": [], "blocker_causes": [],
           "recent_src_writes_120s": None,
           "shell_skip": skip_shells, "legacy_self_only": a.nc_selfmatch or a.nc_both,
           "self_ancestors": sorted(self_and_ancestors()),
           "shells_skipped_n": None}
    if not a.no_shutdown:
        try:
            subprocess.run([str(dotnet), "build-server", "shutdown"], capture_output=True, timeout=90)
            rec["shutdown_done"] = True
        except subprocess.TimeoutExpired:
            rec["shutdown_done"] = False
    # R491 ⑥: shutdown 不是收口面 (本机实测残留 178 MB 节点) ⇒ 追加 fail-closed 收口, 再判内存。
    if not a.keep_stale_nodes:
        rec["build_node_reap"] = reap_stale_build_nodes()
    else:
        rec["build_node_reap"] = {"skipped": True, "why": "--keep-stale-nodes (复现修前行为)"}
    # R557: 本侧工具子进程收口 (语言服务) —— 与 build 节点收口同形, 先收口再判内存。
    if not a.keep_own_tools:
        rec["own_tool_reap"] = reap_own_tool_children()
    else:
        rec["own_tool_reap"] = {"skipped": True, "why": "--keep-own-tools (复现修前行为)"}

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
        # R487 候选④ 精确化: 多因**并列**, 禁二选一。
        #   修前 (R483/R484) 是一条三元表达式 ⇒ mem 因与 build-server 因同时成立时只报一条,
        #   R484 附注已记录该失真 (真因被措辞掩盖)。现在: 全因入 blocker_causes;
        #   legacy blocker_cause 单因时词面不变, 多因时以 '+' 连接 (不静默丢因, 不改既有单因语义)。
        causes = []
        if rec["mem_available_mb"] < gate:
            causes.append("内存不足")
        if any(p["watch"] in ("VBCSCompiler", "MSBuild") for p in rec["blockers"]):
            causes.append("build-server 残留")
        if any(p["watch"] not in ("VBCSCompiler", "MSBuild") for p in rec["blockers"]):
            causes.append("其他进程")
        rec["blocker_causes"] = causes
        rec["blocker_cause"] = (causes[0] if len(causes) == 1 else "+".join(causes)) if causes else "未判定"
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(rec, ensure_ascii=False))
    print("out", a.out)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
