#!/usr/bin/env python3
"""R475 中继 v2 自检 — 零真实调用 (本地假上游), 只验「证据面」是否真的落盘。

判据 (预注册):
  S1 请求面 `sampling` 逐字段等于请求体取值 (max_tokens/temperature/stream/... 缺 ⇒ null 不猜)
  S2 读数面 `finish_reason` / `choices_n` / `content_len` / `reasoning_len` / `reasoning_tokens` 逐条正确
  S3 空正文 (content_len==0 ∧ choices_n>0) ⇒ `empty_body=true`; 正常答复 ⇒ `false`
  S4 恒等式 `prompt_tokens == hit + miss` 当场判: 成立 ⇒ true; 破坏 (hit+miss≠prompt) ⇒ **false 且计数+1**
  S5 预算闸: 越限 ⇒ 402 + 落盘 `blocked=true` (fail-closed, 不转发)
  S6 非 200 ⇒ `body_head` 截断落盘, 且**不含** Authorization/key 任何片段
退出码: 0 = 全过; 1 = 任一 FAIL。
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
RELAY = os.path.join(HERE, "relay_real_r475.py")
WORK = "/tmp/r475_relay_selftest"
KEY_SENTINEL = "sk-SENTINEL-DO-NOT-LOG"
UP_HITS = []


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


PORT_UP = free_port()
PORT_RELAY = free_port()
PROCS = []

CANNED = [
    {  # 1 正常
        "code": 200,
        "body": {"id": "a", "choices": [{"index": 0, "finish_reason": "stop",
                                         "message": {"role": "assistant", "content": "你好"}}],
                 "usage": {"prompt_tokens": 100, "completion_tokens": 5,
                           "prompt_cache_hit_tokens": 64, "prompt_cache_miss_tokens": 36}},
    },
    {  # 2 空正文 + 推理吃满预算
        "code": 200,
        "body": {"id": "b", "choices": [{"index": 0, "finish_reason": "length",
                                         "message": {"role": "assistant", "content": "",
                                                     "reasoning_content": "想" * 50}}],
                 "usage": {"prompt_tokens": 200, "completion_tokens": 5,
                           "prompt_cache_hit_tokens": 128, "prompt_cache_miss_tokens": 72,
                           "completion_tokens_details": {"reasoning_tokens": 5}}},
    },
    {  # 3 恒等式被破坏
        "code": 200,
        "body": {"id": "c", "choices": [{"index": 0, "finish_reason": "stop",
                                         "message": {"role": "assistant", "content": "x"}}],
                 "usage": {"prompt_tokens": 300, "completion_tokens": 3,
                           "prompt_cache_hit_tokens": 100, "prompt_cache_miss_tokens": 100}},
    },
    {  # 4 上游 400 (body_head 面)
        "code": 400,
        "body": {"error": {"message": "bad request", "type": "invalid_request_error"}},
    },
]


class Upstream(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        UP_HITS.append(json.loads(raw or b"{}"))
        item = CANNED[min(len(UP_HITS) - 1, len(CANNED) - 1)]
        b = json.dumps(item["body"], ensure_ascii=False).encode("utf-8")
        self.send_response(item["code"])
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


def post(port, body):
    req = urllib.request.Request("http://127.0.0.1:%d/v1/chat/completions" % port,
                                 data=json.dumps(body).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def wait_health(port, timeout=8.0):
    """中继就绪 = /health 可答 (禁盲睡)。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/health" % port, timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


def main():
    os.makedirs(WORK, exist_ok=True)
    for f in ("calls-t.jsonl", "usage-t.jsonl", "calls-t2.jsonl", "usage-t2.jsonl"):
        p = os.path.join(WORK, f)
        if os.path.exists(p):
            os.remove(p)
    up = ThreadingHTTPServer(("127.0.0.1", PORT_UP), Upstream)
    threading.Thread(target=up.serve_forever, daemon=True).start()
    env = dict(os.environ, R475_UPSTREAM_KEY=KEY_SENTINEL, R475_UPSTREAM="http://127.0.0.1:%d/v1/chat/completions" % PORT_UP)
    relay = subprocess.Popen([sys.executable, "-u", RELAY, str(PORT_RELAY), "3", "1.0", WORK, "t",
                              "http://127.0.0.1:%d/v1/chat/completions" % PORT_UP],
                             env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    PROCS.append(relay)
    if not wait_health(PORT_RELAY):
        print("RELAY_NOT_READY", relay.poll(), relay.stdout.read() if relay.stdout else "")
        sys.exit(1)
    results = {}

    def req(tmp, max_tokens):
        return {"model": "deepseek-flash", "temperature": 0.3 if tmp else None, "max_tokens": max_tokens,
                "stream": False, "top_p": 0.9, "messages": [{"role": "user", "content": "hi"}]}

    post(PORT_RELAY, req(True, 2048))          # → canned 1
    post(PORT_RELAY, req(False, 4096))         # → canned 2
    post(PORT_RELAY, req(True, 512))           # → canned 3
    s4, _ = post(PORT_RELAY, req(True, 512))   # → canned 4 (400) 之后 relay 已到 max_calls=3?
    time.sleep(0.6)
    health = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/health" % PORT_RELAY, timeout=10).read())

    calls = [json.loads(l) for l in open(os.path.join(WORK, "calls-t.jsonl"), encoding="utf-8")]
    usage = [json.loads(l) for l in open(os.path.join(WORK, "usage-t.jsonl"), encoding="utf-8")]
    relay.terminate()
    flat_usage = open(os.path.join(WORK, "usage-t.jsonl"), encoding="utf-8").read()
    flat_calls = open(os.path.join(WORK, "calls-t.jsonl"), encoding="utf-8").read()

    fwd = [u for u in usage if not u.get("blocked")]
    same = ("max_tokens", "model", "stream", "top_p")
    results["S1_sampling"] = all(
        all(c["sampling"][k] == e[k] for k in same)
        for c, e in zip(calls, ({"max_tokens": 2048, "model": "deepseek-flash", "stream": False, "top_p": 0.9},
                                {"max_tokens": 4096, "model": "deepseek-flash", "stream": False, "top_p": 0.9},
                                {"max_tokens": 512, "model": "deepseek-flash", "stream": False, "top_p": 0.9}))) \
        and calls[0]["sampling"]["temperature"] == 0.3 and calls[1]["sampling"]["temperature"] is None \
        and calls[0]["sampling"]["tools_n"] == 0 and calls[2]["sampling"]["max_tokens"] == 512
    results["S2_choices_facts"] = (
        fwd[0]["finish_reason"] == "stop" and fwd[0]["content_len"] == 2 and fwd[0]["reasoning_len"] == 0
        and fwd[1]["finish_reason"] == "length" and fwd[1]["content_len"] == 0
        and fwd[1]["reasoning_len"] == 50 and fwd[1]["reasoning_tokens"] == 5
        and fwd[2]["finish_reason"] == "stop")
    results["S3_empty_body"] = (fwd[0]["empty_body"] is False and fwd[1]["empty_body"] is True
                                and fwd[2]["empty_body"] is False)
    results["S4_identity"] = (fwd[0]["identity_ok"] is True and fwd[1]["identity_ok"] is True
                              and fwd[2]["identity_ok"] is False and health["identity_bad"] == 1)
    results["S5_budget_gate"] = (s4 == 402 and health["blocked"] == 1 and health["calls"] == 3
                                 and [u for u in usage if u.get("blocked")][0]["reason"] == "max_calls")
    # S6: 上游 4xx ⇒ status/body_head 落盘 (另起一个高预算实例, 真转发), 且无凭据泄漏
    env2 = dict(env)
    relay2 = subprocess.Popen([sys.executable, "-u", RELAY, str(PORT_RELAY), "10", "1.0", WORK, "t2",
                               "http://127.0.0.1:%d/v1/chat/completions" % PORT_UP],
                              env=env2, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    PROCS.append(relay2)
    if not wait_health(PORT_RELAY):
        print("RELAY2_NOT_READY", relay2.poll())
        sys.exit(1)
    s400, _ = post(PORT_RELAY, req(True, 512))
    time.sleep(0.4)
    u2 = [json.loads(l) for l in open(os.path.join(WORK, "usage-t2.jsonl"), encoding="utf-8")]
    relay2.terminate()
    flat2 = open(os.path.join(WORK, "usage-t2.jsonl"), encoding="utf-8").read()
    results["S6_upstream_error_surface"] = (s400 == 400 and u2[0]["status"] == 400
                                            and "bad request" in u2[0].get("body_head", ""))
    results["S7_no_credential_leak"] = (KEY_SENTINEL not in flat_usage and KEY_SENTINEL not in flat_calls
                                        and KEY_SENTINEL not in flat2)
    up.shutdown()

    print(json.dumps({k: bool(v) for k, v in results.items()}, ensure_ascii=False, indent=1))
    print("health:", json.dumps(health, ensure_ascii=False))
    print("identity_bad=%d empty_body=%d calls_forwarded=%d blocked_rows=%d"
          % (health["identity_bad"], health["empty_body"], health["calls"],
             len([u for u in usage if u.get("blocked")])))
    print("READINGS: fwd[1] finish_reason=%s content_len=%s reasoning_len=%s empty_body=%s"
          % (fwd[1]["finish_reason"], fwd[1]["content_len"], fwd[1]["reasoning_len"], fwd[1]["empty_body"]))
    ok = all(results.values())
    print("SELFTEST:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    try:
        main()
    finally:
        for _p in PROCS:                      # 收口: 任何路径都不留监听进程
            try:
                _p.terminate()
            except Exception:
                pass
