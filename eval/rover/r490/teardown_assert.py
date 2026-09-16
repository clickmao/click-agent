#!/usr/bin/env python3
# R489 候选⑤: 夹具 teardown 断言 (进程组回收 + 端口断言) —— 语言无关: 只读 /proc 与内核 socket 表,
#   不按语言/文件名分类, 只看「本臂命名空间」与「本臂端口」两条事实。
#
# 背景: R488 收尾事件 = R486 夹具泄漏 4 个 agenthost; 清场时 `pgrep -f 'llama-server'` 匹配到自身 shell
#   导致自杀一次。⇒ 本器具: ① 一律走 /proc 逐 pid 扫描 (不用 pgrep -f); ② 显式排除自身 + 全祖先链;
#   ③ 跳过 shell 解释器 argv0 (bash -lc 的 cmdline 会把命令正文当参数, 属"只是提到"而非"是");
#   ④ 端口断言绑**本臂端口** (监听残留 = 必然泄漏); ⑤ 两个负控各造一种残留, 断言必红 (fail-closed)。
import argparse
import json
import os
import socket
import subprocess
import sys
import time

SHELLS = {"bash", "sh", "dash", "zsh", "-bash", "timeout", "env", "python3", "python"}


def ancestors(pid: int) -> set[int]:
    out = {pid}
    cur = pid
    for _ in range(64):
        try:
            stat = open(f"/proc/{cur}/stat", encoding="utf-8").read()
            ppid = int(stat.rsplit(")", 1)[1].split()[1])
        except Exception:
            break
        if ppid <= 1 or ppid in out:
            break
        out.add(ppid)
        cur = ppid
    return out


def proc_cmdline(pid: str) -> str:
    try:
        raw = open(f"/proc/{pid}/cmdline", "rb").read()
    except Exception:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()


def proc_rss_mb(pid: str) -> float:
    try:
        for line in open(f"/proc/{pid}/status", encoding="utf-8"):
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024.0
    except Exception:
        pass
    return 0.0


def proc_cwd(pid: str) -> str:
    try:
        return os.readlink(f"/proc/{pid}/cwd")
    except Exception:
        return ""


def scan(arm: str, port_tokens: list[str]) -> list[dict]:
    """返回与本臂命名空间/端口相关的残留进程 (已排除自身与祖先, 且跳过 shell argv0 的"提及"匹配)。"""
    me = ancestors(os.getpid())
    hits = []
    for pid in sorted(os.listdir("/proc")):
        if not pid.isdigit() or int(pid) in me:
            continue
        cmd = proc_cmdline(pid)
        if not cmd:
            continue
        argv0 = os.path.basename(cmd.split(" ")[0])
        cwd = proc_cwd(pid)
        matched_by = None
        # 命名空间: 运行目录 / 归档目录 / 臂键 出现在 **cwd** 或 cmdline 的**非 argv0 段**
        if arm and (f"rundata-{arm}" in cwd or f"run-{arm}" in cwd):
            matched_by = "cwd_namespace"
        elif argv0 not in SHELLS and arm and (f"rundata-{arm}" in cmd or f"run-{arm}" in cmd):
            matched_by = "cmdline_namespace"
        elif argv0 not in SHELLS and any(t in cmd for t in port_tokens):
            matched_by = "cmdline_port"
        if matched_by:
            hits.append({"pid": int(pid), "matched_by": matched_by, "argv0": argv0, "rss_mb": round(proc_rss_mb(pid), 1), "cwd": cwd, "cmd": cmd[:160]})
    return hits


def port_listeners(ports: list[int]) -> list[dict]:
    """用内核 socket 表 (无 ss/依赖) 判定本臂端口是否仍被监听。"""
    wanted = set(ports)
    out = []
    for tab in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            rows = open(tab, encoding="utf-8").read().splitlines()[1:]
        except Exception:
            continue
        for row in rows:
            f = row.split()
            if len(f) < 4 or f[3] != "0A":  # 0A = LISTEN
                continue
            local = f[1]
            try:
                port = int(local.split(":")[1], 16)
            except Exception:
                continue
            if port in wanted:
                out.append({"port": port, "state": "LISTEN", "inode": f[9] if len(f) > 9 else ""})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="")
    ap.add_argument("--api-port", type=int, default=0)
    ap.add_argument("--relay-port", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reap", action="store_true",
                    help="先按命名空间收口 (TERM→8s→KILL) 再断言; 用于夹具 teardown (R489 B 臂实测: "
                         "llama-server 非 host 直接子进程 ⇒ pkill -P 漏杀 ⇒ 必须按命名空间收口)")
    ap.add_argument("--nc-listener", action="store_true", help="负控: 占住 api 端口 ⇒ 断言必红")
    ap.add_argument("--nc-proc", action="store_true", help="负控: 造一个带臂名的残留进程 ⇒ 断言必红")
    ap.add_argument("--selftest", action="store_true",
                    help="三例自检: 端口负控 / 命名空间负控 / **收口端到端** (造真残留→--reap→复断言干净); "
                         "结果落 --out, rc=0 全过 / 2 有失")
    a = ap.parse_args()

    if a.selftest:
        import tempfile
        sub = [sys.executable, os.path.abspath(__file__)]
        res = {}

        def run(args_tag, extra, ports):
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
                out = tf.name
            p = subprocess.run(sub + ["--arm", args_tag, "--api-port", str(ports[0]),
                                      "--relay-port", str(ports[1]), "--out", out] + extra,
                               capture_output=True, text=True)
            doc = json.load(open(out, encoding="utf-8"))
            os.unlink(out)
            return p.returncode, doc

        rc, doc = run("NCTEST1", ["--nc-listener"], (48981, 48980))
        res["nc_listener"] = {"rc": rc, "verdict": doc["verdict"], "expect_rc": 0,
                              "ok": rc == 0 and doc["verdict"] == "residual"}
        rc, doc = run("NCTEST2", ["--nc-proc"], (48983, 48982))
        res["nc_proc"] = {"rc": rc, "verdict": doc["verdict"], "expect_rc": 0,
                          "ok": rc == 0 and doc["verdict"] == "residual"}
        d = "/tmp/rundata-REAPTEST"
        os.makedirs(d, exist_ok=True)
        sleeper = subprocess.Popen(["/bin/sleep", "60"], cwd=d)
        try:
            time.sleep(0.5)
            rc, doc = run("REAPTEST", ["--reap"], (48985, 48984))
            # "存活" 必须排除僵尸 (Z/X): 收口后子进程可能尚未被其父 wait ⇒ /proc/<pid> 仍在但已非活体
            try:
                st = open(f"/proc/{sleeper.pid}/stat", encoding="utf-8").read().rsplit(")", 1)[1].split()[0]
                alive = st not in ("Z", "X")
            except Exception:
                alive = False
            res["reap_e2e"] = {"rc": rc, "verdict": doc["verdict"], "reaped_pids": doc["reaped_pids"],
                               "residual_after": len(doc["residual_procs"]), "sleeper_alive": alive,
                               "ok": rc == 0 and doc["verdict"] == "clean" and not alive and bool(doc["reaped_pids"])}
        finally:
            try:
                sleeper.kill()
            except Exception:
                pass
            try:
                os.rmdir(d)
            except Exception:
                pass
        ok = all(v["ok"] for v in res.values())
        out_doc = {"arm": "SELFTEST", "ts_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                   "checks": res, "verdict": "PASS" if ok else "FAIL",
                   "note": "端口负控/命名空间负控 = 检测器必红; reap_e2e = 收口器真能把残留收干净"}
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(out_doc, fh, ensure_ascii=False, indent=1)
        print(json.dumps({k: v for k, v in res.items()}, ensure_ascii=False))
        print("[teardown-selftest]", out_doc["verdict"], "->", a.out)
        return 0 if ok else 2

    ports = [a.api_port, a.relay_port]
    if not a.arm or not a.api_port or not a.relay_port:
        ap.error("非 --selftest 时必须给 --arm/--api-port/--relay-port")
    holder = None
    if a.nc_listener:
        holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        holder.bind(("127.0.0.1", a.api_port))
        holder.listen(1)
    sleeper = None
    ncdir = f"/tmp/rundata-{a.arm}"
    if a.nc_proc:
        os.makedirs(ncdir, exist_ok=True)
        sleeper = subprocess.Popen(["/bin/sleep", "60"], cwd=ncdir)

    try:
        time.sleep(0.3)
        pre = scan(a.arm, [str(p) for p in ports])
        reaped, survivors = [], []
        if a.reap and pre:
            for h in pre:
                try:
                    os.kill(h["pid"], 15)          # SIGTERM
                except Exception:
                    pass
                reaped.append(h["pid"])
            t0 = time.time()
            while time.time() - t0 < 8.0:
                time.sleep(0.4)
                if not scan(a.arm, [str(p) for p in ports]):
                    break
            survivors = scan(a.arm, [str(p) for p in ports])
            for h in survivors:
                try:
                    os.kill(h["pid"], 9)           # SIGKILL
                except Exception:
                    pass
            time.sleep(0.5)
        procs = scan(a.arm, [str(p) for p in ports])
        listeners = port_listeners(ports)
        verdict = "clean" if (not procs and not listeners) else "residual"
        doc = {
            "arm": a.arm,
            "ts_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "ports": {"api": a.api_port, "relay": a.relay_port},
            "checks": {
                "no_arm_process": not procs,
                "no_arm_port_listener": not listeners,
            },
            "residual_before_reap": pre,
            "reaped_pids": reaped,
            "reap_survivors_killed": [h["pid"] for h in survivors],
            "residual_procs": procs,
            "listeners": listeners,
            "verdict": verdict,
            "self_exclusion": {"self_pid": os.getpid(), "excluded_pids": sorted(ancestors(os.getpid()))},
            "negative_controls": {"nc_listener": a.nc_listener, "nc_proc": a.nc_proc},
        }
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)
        print(f"[teardown] arm={a.arm} verdict={verdict} procs={len(procs)} listeners={len(listeners)}")
        if a.nc_listener or a.nc_proc:
            # 负控期望 = 红; 红 ⇒ rc=0 (负控通过), 绿 ⇒ rc=2 (负控失效)
            print(f"[teardown] NEGATIVE_CONTROL_EXPECT_RED got={verdict} => " + ("PASS" if verdict == "residual" else "FAIL"))
            return 0 if verdict == "residual" else 2
        return 0 if verdict == "clean" else 2
    finally:
        if holder is not None:
            holder.close()
        if sleeper is not None:
            sleeper.kill()
            sleeper.wait()


if __name__ == "__main__":
    sys.exit(main())
