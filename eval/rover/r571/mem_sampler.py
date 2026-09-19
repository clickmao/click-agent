#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R571 运行窗口内存采样器 **v2** (后台; 由 runner 起、收尾按 pid 杀)。

v1 只落 `mem_available_mb`。v2 **加一列 `own_rss_mb` = 本运行「血统」进程的 RSS 合计**
(血统 = ① 采样器父进程(即 runner)的**全部后代** ② 命令行里含本运行根或端口的进程),
用于把「运行窗口内 MemAvailable 下降」拆成 **自体成本** vs **外来压力**。

为什么必须拆 (R570 实证, 承重): R570 postcheck 报 `in_min=2539 < GATE 2650` ⇒ 该窗读数
被标「参考(门越线)」。但逐样本时间轴显示该下降是**阶跃**(t≈120s 起 −230MB, 持续到
t≈780s) 且与**本运行最长的那个真值窗 (w144, 672s)** 边界对齐 ⇒ 第一嫌疑是**自体**
(被测/中继自身的内存), 不是外来干扰。不拆开就无法判定, 只能两难: 要么误标污染, 要么
放宽门槛。本件不改门槛 —— 只把**归属**做成可读的一列。

写 JSONL: {ts, elapsed_s, mem_available_mb, own_rss_mb, own_n, own_pids, own_src}。
被 SIGTERM 时也已落盘 (逐行 flush), 不依赖退出时写盘 (R412 纪律: 被杀也不能丢证据)。
向后兼容: 缺 `own_rss_mb` 字段的旧样本 (如 R570) 在消费侧按 **0** 处理 ⇒ v2 判据退化为
v1 判据 ⇒ **旧判决不被静默翻案** (R570 postcheck 仍 rc=2)。
"""
import io
import json
import os
import sys
import time

out = sys.argv[1]
period = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
root = sys.argv[3] if len(sys.argv) > 3 else ""
port = sys.argv[4] if len(sys.argv) > 4 else ""
RUNNER_PID = os.getppid()
SELF = os.getpid()


def read_mem_available_mb():
    for ln in io.open("/proc/meminfo", encoding="utf-8", errors="replace"):
        if ln.startswith("MemAvailable:"):
            return int(ln.split()[1]) // 1024
    return None


def _stat(pid):
    try:
        raw = io.open("/proc/%d/stat" % pid, encoding="utf-8", errors="replace").read()
        rp = raw.rfind(")")
        if rp < 0:
            return None
        f = raw[rp + 2:].split()
        return {"state": f[0], "ppid": int(f[1])}
    except Exception:  # noqa: BLE001
        return None


def _rss_kb(pid):
    try:
        for ln in io.open("/proc/%d/status" % pid, encoding="utf-8", errors="replace"):
            if ln.startswith("VmRSS:"):
                return int(ln.split()[1])
    except Exception:  # noqa: BLE001
        pass
    return 0


def _cmdline(pid):
    try:
        return io.open("/proc/%d/cmdline" % pid, "rb").read().decode("utf-8", "replace").replace("\0", " ")
    except Exception:  # noqa: BLE001
        return ""


def own_pids():
    """血统集合: runner 后代 (树上) ∪ 命令行含运行根/端口的进程 (被 setsid 重父化者也能捞回)。"""
    kids = {}
    alive = []
    for e in os.listdir("/proc"):
        if not e.isdigit():
            continue
        pid = int(e)
        if pid == SELF:
            continue
        st = _stat(pid)
        if st is None:
            continue
        alive.append(pid)
        kids.setdefault(st["ppid"], []).append(pid)
    tree, stack = set(), [RUNNER_PID]
    while stack:
        cur = stack.pop()
        for c in kids.get(cur, []):
            if c not in tree:
                tree.add(c)
                stack.append(c)
    cl = set()
    if root or port:
        for pid in alive:
            c = _cmdline(pid)
            if (root and root in c) or (port and port in c):
                cl.add(pid)
    return tree, cl


t0 = time.time()
fh = io.open(out, "a", encoding="utf-8")
while True:
    tree, cl = own_pids()
    own = sorted((tree | cl) - {SELF})
    rss = sum(_rss_kb(p) for p in own) // 1024
    src = "tree+cmdline" if (tree and cl) else ("tree" if tree else ("cmdline" if cl else "none"))
    fh.write(json.dumps({"ts": round(time.time(), 1), "elapsed_s": round(time.time() - t0, 1),
                         "mem_available_mb": read_mem_available_mb(),
                         "own_rss_mb": rss, "own_n": len(own), "own_pids": own[:8],
                         "own_src": src}) + "\n")
    fh.flush()
    time.sleep(period)
