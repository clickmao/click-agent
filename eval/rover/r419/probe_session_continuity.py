#!/usr/bin/env python3
"""R419 §3 决定性微实验: 同 --session-id 跨两次进程调用, 链是否续上下文?

判据(预注册): turn2 回复出现 `4271` ⇒ 续上下文成立; 否则不成立。
诚实边界: 单次单例; 若 turn2 未出现数字, 须再跑一次以排除「模型没答对」而非「没上下文」
(第二次判据改为问「我上一条问了什么」的语义复述)。
"""
import os
import subprocess
import sys
import time

ROOT = "/home/agentuser/AgentFramework"
BIN ="/tmp/pub_r414/agenthost"
sys.path.insert(0, ROOT + "/eval/probe")
import run_probe as RP  # noqa: E402

env = RP.load_env_local()
env["AGENTFRAMEWORK_PY_RUN"] = "1"
env["PYTHONDONTWRITEBYTECODE"] = "1"
sid = "r419-cont-%s" % time.strftime("%m%d%H%M%S")
turns = ["记住数字 4271，只回「好」。", "我刚才让你记住什么数字？只回数字。"]
outs = []
for i, t in enumerate(turns, 1):
    t0 = time.time()
    p = subprocess.run([BIN, "-q", t, "--output-mode", "text", "--session-id", sid],
                       capture_output=True, text=True, timeout=600, cwd=ROOT, env=env)
    outs.append(p.stdout or "")
    print("[turn %d] exit=%s secs=%.1f len=%d" % (i, p.returncode, time.time() - t0, len(outs[-1])), flush=True)
    print("---- turn %d tail ----" % i)
    print(outs[-1][-700:], flush=True)

hit = "4271" in outs[-1]
print("VERDICT_SESSION_CONTINUITY=%s (4271 hit=%s) sid=%s" % ("PASS" if hit else "FAIL", hit, sid))
