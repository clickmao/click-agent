#!/usr/bin/env bash
# R578 · 产品形状核查: 同一 453 字 verbatim prompt 走两条路径 (bench 的 /completion 与产品的 /v1/chat/completions)
BIN=/tmp/llama-full/build/bin/llama-server
M=$HOME/.agentframework/models/lfm25vl3b/LFM2.5-VL-3B-Q4_K_M.gguf
P=48796
LOG=/tmp/r578_shape.log

"$BIN" -m "$M" --host 127.0.0.1 --port $P -c 4608 -t 2 -np 1 \
  --cache-type-k f32 --cache-type-v f32 --flash-attn off --jinja -b 512 -ub 512 > "$LOG" 2>&1 &
PID=$!
for i in $(seq 1 60); do sleep 3; curl -sf -m 3 "http://127.0.0.1:$P/health" >/dev/null && break; done
echo "health=$(curl -s -m 5 http://127.0.0.1:$P/health)"
python3 - "$P" <<'PY'
import json, sys, urllib.request, re
P = sys.argv[1]
c = json.load(open("/tmp/r462_corpus.json", encoding="utf-8"))
EXP = {"skip": "S", "pass(real:rule)": "P"}
# 取 2 条 S(ack) + 2 条 P, 逐条两路径
sel = [x for x in c if x["want"] == "skip" and x["family"] == "ack"][:2] + \
      [x for x in c if x["want"] != "skip"][:2]

def post(path, body, timeout=300):
    req = urllib.request.Request(f"http://127.0.0.1:{P}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))

def letter(s):
    m = re.search(r"[SP]", s or "")
    return m.group(0) if m else (s or "")[:8]

print(f"{'i':>3} {'family':<10} {'want':<16} {'/completion':<12} {'/v1/chat(产品)':<20} ok_raw ok_chat  tok")
for k, it in enumerate(sel, 1):
    exp = EXP[it["want"]]
    d1 = post("/completion", {"prompt": it["prompt"], "n_predict": 32, "samplers": ["temperature"],
                              "temperature": 0, "seed": 0, "cache_prompt": False})
    g1 = (d1.get("content") or "").strip()
    d2 = post("/v1/chat/completions", {"messages": [{"role": "user", "content": it["prompt"]}],
                                       "max_tokens": 32, "temperature": 0})
    msg = d2.get("choices", [{}])[0].get("message", {})
    g2 = (msg.get("content") or "").strip()
    rc = msg.get("reasoning_content")
    if not g2 and rc:
        g2 = "<reasoning_content>" + rc[:24]
    u = d2.get("usage") or {}
    print(f"{k:>3} {it['family']:<10} {it['want']:<16} {letter(g1):<12} {letter(g2)[:18]:<20} "
          f"{str(letter(g1)==exp):<6} {str(letter(g2)==exp):<7} {u.get('completion_tokens')}/{u.get('prompt_tokens')}")
    print(f"    prompt_sha16={it.get('prompt_sha16','-')} msg={it['msg']!r}")
PY
kill "$PID" 2>/dev/null; sleep 2; echo "alive=$(pgrep -cx llama-server)"
