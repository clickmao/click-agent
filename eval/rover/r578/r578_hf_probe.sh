#!/usr/bin/env bash
# R578 · LFM2.5-VL-3B 权重同源取证 (HF LFS oid vs 本机 sha256)
LOCAL=$(sha256sum "$HOME/.agentframework/models/lfm25vl3b/LFM2.5-VL-3B-Q4_K_M.gguf" | cut -d' ' -f1)
echo "local_sha256 = $LOCAL"
echo "manifest     = $(head -1 "$HOME/.agentframework/models/lfm25vl3b/SHA256SUMS" | cut -d' ' -f1)"
for R in LiquidAI/LFM2.5-VL-3B-GGUF LiquidAI/LFM2.5-VL-3B-Instruct-GGUF LiquidAI/LFM2.5-VL-3B; do
  echo "=== repo: $R ==="
  curl -s -m 40 "https://huggingface.co/api/models/$R" -w "\nhttp=%{http_code}\n" \
    | python3 -c "import sys,json;
raw=sys.stdin.read(); tail=raw.strip().splitlines()[-1]
try:
  d=json.loads(raw[:raw.rstrip().rfind('}')+1])
  print('id',d.get('id'),'gated',d.get('gated'),'license',(d.get('cardData') or {}).get('license'))
  print('files',[f['rfilename'] for f in (d.get('siblings') or []) if f['rfilename'].lower().endswith('.gguf')][:8])
  print('sha', (d.get('siblings') or [{}])[0].get('lfs',{}))
except Exception as e: print('parse_fail',e)
print('http', tail.split('=')[-1])" 2>/dev/null
done
echo "=== resolve 头 (LFS oid) ==="
for U in "https://huggingface.co/LiquidAI/LFM2.5-VL-3B-GGUF/resolve/main/LFM2.5-VL-3B-Q4_K_M.gguf" "https://hf-mirror.com/LiquidAI/LFM2.5-VL-3B-GGUF/resolve/main/LFM2.5-VL-3B-Q4_K_M.gguf"; do
  echo "--- $U"
  curl -sL -m 60 -r 0-0 -D - -o /dev/null -w "http=%{http_code} size_dl=%{size_download}\n" "$U" 2>&1 | grep -iE "^(x-linked-etag|x-linked-size|content-range|http=)" | head -5
done
