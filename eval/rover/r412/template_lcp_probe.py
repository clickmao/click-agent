#!/usr/bin/env python3
"""R412 仪器校验: 模板渲染后的公共前缀长度。

为什么要先做这一步: 冒烟里「另一会话的冷请求」报 pn=1 / cache_n=270，
说明该模型模板渲染后两个"不同" prompt 仍共享 ~270 token 的**公共前缀** ⇒
臂的判别力被模板布局抹平。必须先量出分歧点在哪，才能设计有判别力的臂。
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BIN = os.environ["AGENTFRAMEWORK_LLAMA_BIN"]
MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
PORT = 8956
BASE = f"http://127.0.0.1:{PORT}"
CTX = int(os.environ.get("R412_CTX", "2048"))


def post(path, payload, timeout=600):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def wait_health(deadline=180):
    t0 = time.time()
    while time.time() - t0 < deadline:
        try:
            with urllib.request.urlopen(BASE + "/health", timeout=3) as r:
                if json.loads(r.read().decode()).get("status") == "ok":
                    return True
        except Exception:  # noqa: BLE001
            time.sleep(1)
    return False


def tok(content):
    return post("/tokenize", {"content": content})["tokens"]


def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def lcs_len(a, b):
    """贪心最长公共子串长度（近似判别共享片段）。"""
    best = 0
    bset = {}
    for i, t in enumerate(b):
        bset.setdefault(t, []).append(i)
    for i, t in enumerate(a):
        for j in bset.get(t, ())[:8]:
            k = 0
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            best = max(best, k)
    return best


def main():
    P1 = open(os.path.join(ROOT, "eval/rover/r412/prefix-p1.txt"), encoding="utf-8").read().strip()
    P2 = open(os.path.join(ROOT, "eval/rover/r412/prefix-p2.txt"), encoding="utf-8").read().strip()
    Q1 = "用一句话回答: 1+1 等于几?"

    srv = subprocess.Popen([BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT),
                            "-c", str(CTX), "-t", "2", "--cache-type-k", "f32", "--cache-type-v", "f32",
                            "--flash-attn", "off", "-np", "1", "--jinja"],
                           stdout=open(os.path.join(ROOT, "eval/rover/r412/template-lcp-server.log"), "w"),
                           stderr=subprocess.STDOUT)
    try:
        if not wait_health():
            print("SERVER_FAIL", flush=True)
            return
        out = {}
        for mode in ("sys", "user"):
            def render(px):
                msgs = ([{"role": "system", "content": px}, {"role": "user", "content": Q1}] if mode == "sys"
                        else [{"role": "user", "content": px + "\n" + Q1}])
                return post("/apply-template", {"messages": msgs})["prompt"]
            t1, t2 = tok(render(P1)), tok(render(P2))
            out[mode] = {"tokens_P1": len(t1), "tokens_P2": len(t2),
                         "lcp": lcp(t1, t2), "lcp_frac": round(lcp(t1, t2) / min(len(t1), len(t2)), 4),
                         "longest_common_run": lcs_len(t1, t2),
                         "P1_head": t1[:12], "P2_head": t2[:12]}
            print(mode, json.dumps({k: v for k, v in out[mode].items() if k not in ("P1_head", "P2_head")},
                                   ensure_ascii=False), flush=True)
        json.dump(out, open(os.path.join(ROOT, "eval/rover/r412/template-lcp.json"), "w"),
                  ensure_ascii=False, indent=2)
        print("DONE", flush=True)
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=30)
        except Exception:  # noqa: BLE001
            srv.kill()


if __name__ == "__main__":
    sys.exit(main())
