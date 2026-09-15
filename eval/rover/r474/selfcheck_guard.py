#!/usr/bin/env python3
"""R474 预算闸负控 (零成本, 不外发): cap=0 的中继必须回 402 且不产生任何转发记录。

判据 G1: HTTP 状态 == 402
判据 G2: usage-*.jsonl 里只有 blocked 行, 无 status>0 的转发行
判据 G3: 中继进程在收到请求后仍存活 (fail-closed 而非崩溃)
判据 G4 (正控): cap=1 的中继对同一请求**会尝试转发** (以非法 key 打不可达上游 ⇒ 502/400x,
        证明「拦」不是恒真 —— 该路径不产生真实计费: 上游 = 本地黑洞端口)

只读/零成本: 不触碰真端点。
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "/tmp/r474_guard_selfcheck"
os.makedirs(OUT, exist_ok=True)
BODY = json.dumps({"model": "deepseek-flash",
                   "messages": [{"role": "user", "content": "selfcheck"}],
                   "max_tokens": 1}).encode("utf-8")


def wait_port(port, t=10.0):
    t0 = time.time()
    while time.time() - t0 < t:
        s = socket.socket()
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except Exception:
            time.sleep(0.2)
        finally:
            s.close()
    return False


def start(tag, port, cap_calls, upstream, cap_cny=0.0, key="dummy-selfcheck"):
    log = open(os.path.join(OUT, "relay-%s.log" % tag), "ab")
    env = dict(os.environ)
    env["R474_UPSTREAM_KEY"] = key
    p = subprocess.Popen([sys.executable, "-u", os.path.join(HERE, "relay_real.py"),
                          str(port), str(cap_calls), str(cap_cny), OUT, tag, upstream],
                         stdout=log, stderr=log, env=env)
    ok = wait_port(port)
    return p, ok


def post(port):
    req = urllib.request.Request("http://127.0.0.1:%d/v1/chat/completions" % port,
                                 data=BODY, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()[:200].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200].decode("utf-8", "replace")
    except Exception as e:
        return -1, type(e).__name__ + ":" + str(e)[:120]


def rows(tag):
    p = os.path.join(OUT, "usage-%s.jsonl" % tag)
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


results = {}

# 负控: cap=0 + 黑洞上游 (就算漏也不会打到真端点)
p, up = start("guard0", 48121, 0, "http://127.0.0.1:9/v1/chat/completions")
results["G0_负控中继启动"] = up
code, body = post(48121)
results["G1_HTTP==402"] = (code == 402)
results["G1_body"] = body
r = rows("guard0")
results["G2_无转发行"] = (len(r) >= 1 and all(x.get("blocked") for x in r))
results["G2_rows"] = r
time.sleep(0.3)
results["G3_进程存活"] = (p.poll() is None)
p.terminate()
p.wait(timeout=5)

# 正控: cap=1 + 黑洞上游 ⇒ 必经转发路径 (上游连不上 ⇒ 宿主侧收到 502), 证明「拦」非恒真
p2, up2 = start("guard1", 48122, 1, "http://127.0.0.1:9/v1/chat/completions", cap_cny=1.0)
results["G4_正控中继启动"] = up2
code2, body2 = post(48122)
results["G4_正控非402"] = (code2 != 402)
results["G4_body"] = body2
r2 = rows("guard1")
results["G4_正控有转发尝试"] = any(not x.get("blocked") for x in r2)
time.sleep(0.3)
p2.terminate()
p2.wait(timeout=5)

results["verdict"] = "PASS" if all([results["G0_负控中继启动"], results["G1_HTTP==402"],
                                    results["G2_无转发行"], results["G3_进程存活"],
                                    results["G4_正控中继启动"], results["G4_正控非402"],
                                    results["G4_正控有转发尝试"]]) else "FAIL"
out = os.path.join(HERE, "selfcheck_guard.json")
json.dump(results, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in results.items() if k != "G2_rows"}, ensure_ascii=False, indent=1))
print("wrote", out)
sys.exit(0 if results["verdict"] == "PASS" else 1)
