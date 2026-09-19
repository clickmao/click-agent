#!/usr/bin/env bash
# R578 · 产品参数档装载烟测 + 产品形状单判: config/base/models.yaml local 段 (ctx=4608) + LFM2.5-VL-3B-Q4_K_M
# 变量 = 仅权重 (argv/端口/上下文/线程 与 R577 同形状), 以保跨轮可比
BIN=/tmp/llama-full/build/bin/llama-server
M=$HOME/.agentframework/models/lfm25vl3b/LFM2.5-VL-3B-Q4_K_M.gguf
P=48795
LOG=/tmp/r578_p_ctx4608_lfm.log

"$BIN" -m "$M" --host 127.0.0.1 --port $P -c 4608 -t 2 -np 1 \
  --cache-type-k f32 --cache-type-v f32 --flash-attn off --jinja -b 512 -ub 512 > "$LOG" 2>&1 &
PID=$!
ready=no
for i in $(seq 1 60); do
  sleep 3
  if curl -sf -m 3 "http://127.0.0.1:$P/health" > /dev/null; then ready=yes; break; fi
done
echo "ready=$ready  wait_s=$(( i * 3 ))"
echo "health=$(curl -s -m 5 http://127.0.0.1:$P/health)"
free -m | head -2
RSS=$(ps -o rss= -p "$(pgrep -f "port $P" | head -1)" 2>/dev/null | tr -d ' ')
[ -n "$RSS" ] && echo "llama-server RSS = $(( RSS / 1024 )) MB"

echo "--- (a) R577 同款平凡请求 (跨轮可比锚点) ---"
curl -s -m 180 "http://127.0.0.1:$P/v1/chat/completions" -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Answer with one letter only: S"}],"max_tokens":32,"temperature":0}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('choices:',json.dumps(d.get('choices',[{}])[0].get('message',{}),ensure_ascii=False)[:200]); print('usage:',d.get('usage'))"

echo "--- (b) 产品形状单判 (语料第 1 条 verbatim, raw /completion 路径) ---"
python3 - "$P" <<'PY'
import json, sys, urllib.request
P = sys.argv[1]
c = json.load(open("/tmp/r462_corpus.json", encoding="utf-8"))
it = c[0]
body = json.dumps({"prompt": it["msg"], "n_predict": 32, "temperature": 0,
                   "cache_prompt": False, "n_probs": 0}).encode()
req = urllib.request.Request(f"http://127.0.0.1:{P}/completion", data=body,
                             headers={"Content-Type": "application/json"})
d = json.load(urllib.request.urlopen(req, timeout=300))
got = (d.get("content") or "").strip()
print("want=%r got=%r ok=%s" % (it["want"], got[:40], got.strip().startswith(it["want"])))
print("usage:", d.get("usage") or d.get("tokens_predicted"))
PY

echo "--- (c) 产品形状单判 (同条, chat/jinja 路径 = 产品真实调用形态) ---"
python3 - "$P" <<'PY'
import json, sys, urllib.request
P = sys.argv[1]
c = json.load(open("/tmp/r462_corpus.json", encoding="utf-8"))
it = c[0]
body = json.dumps({"messages": [{"role": "user", "content": it["msg"]}],
                   "max_tokens": 32, "temperature": 0}).encode()
req = urllib.request.Request(f"http://127.0.0.1:{P}/v1/chat/completions", data=body,
                             headers={"Content-Type": "application/json"})
d = json.load(urllib.request.urlopen(req, timeout=300))
m = d.get("choices", [{}])[0].get("message", {})
got = (m.get("content") or "").strip()
print("want=%r got=%r ok=%s" % (it["want"], got[:40], got.strip().startswith(it["want"])))
print("usage:", d.get("usage"))
PY

kill "$PID" 2>/dev/null
sleep 2
echo "alive=$(pgrep -cx llama-server)"
echo "killed; log tail:"; tail -3 "$LOG" | cut -c1-160
