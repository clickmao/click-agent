#!/usr/bin/env python3
"""R484 探针: 微步骤隔离问询 → 本地 r1 可行性 (prereg_r484.json 已先落盘)。

两臂同题同判据:
  local  = 产品同参 llama-server (LlamaServerHost.BuildArgumentList 对齐: -c 4608 -np 1 f32 KV --flash-attn off --jinja)
  remote = https://api.deepseek.com/v1/chat/completions, model/sampling 取 R482 记录值
输入 sha 钉在 prereg 里; llama-server 在 finally 必回收。不打印任何密钥。
"""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = ROOT / "eval/rover/r482/calls-Arole.jsonl"
SRC_SHA = "89f53b568fd08e46147a03bf783c5d62230ebb175f23f434dfac5c5aa8ee0941"
OUT = HERE / "micro_local_probe.json"
LOG = HERE / "server-probe.log"
GGUF = "/home/agentuser/.agentframework/models/qwen2.5-3b-instruct-q4km.gguf"
BIN = "/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server"
PORT = 48711
CTX = 4608
CJK = re.compile(r"[\u4e00-\u9fff]")
BOILER = ("作为一个AI", "作为AI", "作为一个 AI", "我无法回答", "无法提供", "cannot assist", "I cannot")
NEG = ("不对", "不是", "错误", "≠", "并不", "其实", "应为", "应该是")
ARITH = re.compile(r"(\d+)\s*(?:加|＋|\+)\s*(\d+)\s*等于\s*(\d+)")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def key():
    v = os.environ.get("AGENTFRAMEWORK_KEYS_DEEPSEEK", "")
    if not v:
        for ln in (ROOT / ".env.local").read_text().splitlines():
            if ln.strip().startswith("AGENTFRAMEWORK_KEYS_DEEPSEEK="):
                v = ln.split("=", 1)[1].strip().strip('"')
    return v


def post(url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json", **headers})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    return d, time.time() - t0


def call(url, msgs, model, samp, headers, timeout):
    body = {"model": model, "messages": msgs}
    for k in ("temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty"):
        if samp.get(k) is not None:
            body[k] = samp[k]
    body.setdefault("max_tokens", 512)
    body["stream"] = False
    try:
        d, dt = post(url, body, headers, timeout)
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}", "latency_s": None, "body_sent": body}
    ch = (d.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    content = msg.get("content") or ""
    usage = d.get("usage") or {}
    return {"error": None, "latency_s": round(dt, 2), "content": content, "len": len(content),
            "finish_reason": ch.get("finish_reason"), "usage": usage,
            "empty_body": content.strip() == ""}


def criteria(q, a):
    qn = re.sub(r"\s+", "", q)
    an = re.sub(r"\s+", "", a)
    echo = len(qn) >= 10 and qn in an
    return {
        "non_empty": an != "",
        "len_le_400": len(a) <= 400,
        "not_echo": not echo,
        "no_boiler": not any(b.replace(" ", "") in an for b in BOILER),
        "has_cjk": bool(CJK.search(a)),
    }


def arith_check(q, a):
    m = ARITH.search(q)
    if not m:
        return None
    s = str(int(m.group(1)) + int(m.group(2)))
    return {"expected": s, "stated": m.group(3), "has_expected": s in a,
            "has_neg": any(n in a for n in NEG)}


def wait_health(deadline):
    url = f"http://127.0.0.1:{PORT}/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1)
    return False


def main():
    assert sha256(SRC) == SRC_SHA, "输入未钉住: calls-Arole.jsonl 已变"
    recs = [json.loads(l) for l in SRC.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    sample = [r for r in recs if r.get("n_messages") == 2 and "微步骤隔离问询" in json.dumps(r["messages"], ensure_ascii=False)]
    print(f"[sample] n={len(sample)} seqs={[r.get('seq') for r in sample]}")

    k = key()
    rec_out = {"round": "R484", "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "input": {"path": str(SRC.relative_to(ROOT)), "sha256": SRC_SHA},
               "gguf": {"path": GGUF, "sha256": sha256(GGUF)},
               "server_args": ["-m", GGUF, "--host", "127.0.0.1", "--port", str(PORT), "-c", str(CTX),
                               "-np", "1", "--cache-type-k", "f32", "--cache-type-v", "f32",
                               "--flash-attn", "off", "--jinja"],
               "remote_ok": bool(k), "calls": [], "setup_blocked": None}
    args = rec_out["server_args"]
    proc = None
    try:
        proc = subprocess.Popen([BIN] + args, stdout=open(LOG, "wb"), stderr=subprocess.STDOUT)
        if not wait_health(time.time() + 120):
            rec_out["setup_blocked"] = "llama-server 120s 内未就绪 (见 server-probe.log)"
            print("[fatal]", rec_out["setup_blocked"])
            return rec_out
        print("[server] ready pid=%d" % proc.pid)
        headers_r = {"Authorization": f"Bearer {k}"} if k else {}
        for r in sample:
            msgs = r["messages"]
            q = msgs[-1]["content"]
            samp = r.get("sampling") or {}
            loc = call(f"http://127.0.0.1:{PORT}/v1/chat/completions", msgs, "local-m3b", samp, {}, 240)
            rem = call("https://api.deepseek.com/v1/chat/completions", msgs, r.get("model", "deepseek-flash"), samp, headers_r, 120) if k else {"error": "no-key"}
            row = {"seq": r.get("seq"), "model_rec": r.get("model"), "sampling_rec": samp,
                   "q": q[:200], "arith": ARITH.search(q) is not None,
                   "local": loc, "remote": rem,
                   "crit_local": criteria(q, loc.get("content", "")) if not loc.get("error") else None,
                   "crit_remote": criteria(q, rem.get("content", "")) if not rem.get("error") else None,
                   "arith_local": arith_check(q, loc.get("content", "")) if not loc.get("error") else None,
                   "arith_remote": arith_check(q, rem.get("content", "")) if not rem.get("error") else None}
            rec_out["calls"].append(row)
            print(f"  seq{r.get('seq')} local(len={loc.get('len')}, {loc.get('latency_s')}s, err={loc.get('error')}) "
                  f"remote(len={rem.get('len')}, {rem.get('latency_s')}s, err={rem.get('error')})")
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(20)
            except subprocess.TimeoutExpired:
                proc.kill()
        rec_out["cleanup"] = {"llama_server_killed": proc is not None, "alive_after": proc.poll() if proc else None}

    cl = [c for c in rec_out["calls"] if c["crit_local"]]
    H = {}
    H["H1"] = f"{sum(1 for c in cl if c['crit_local']['non_empty'])}/{len(cl)}"
    H["H2"] = f"{sum(1 for c in cl if all(c['crit_local'].values()))}/{len(cl)}"
    band = [c for c in cl if c["remote"].get("len")]
    H["H3"] = (f"{sum(1 for c in band if 0.25 * c['remote']['len'] <= c['local']['len'] <= 3 * c['remote']['len'])}/{len(band)}"
               if band else "remote 不可用 ⇒ 未测")
    al = [c for c in cl if c["arith_local"] is not None]
    H["H4"] = {"local": f"{sum(1 for c in al if c['arith_local']['has_expected'] and c['arith_local']['has_neg'])}/{len(al)}",
               "remote": f"{sum(1 for c in al if c['arith_remote'] and c['arith_remote']['has_expected'] and c['arith_remote']['has_neg'])}/{len(al)}"}
    lat = [c["local"]["latency_s"] for c in cl if c["local"].get("latency_s")]
    H["H5"] = f"max_latency={max(lat) if lat else None}s / n={len(lat)}"
    rec_out["summary"] = H
    print("[summary]", json.dumps(H, ensure_ascii=False))
    OUT.write_text(json.dumps(rec_out, ensure_ascii=False, indent=1))
    print("[out]", OUT)
    return rec_out


if __name__ == "__main__":
    main()
