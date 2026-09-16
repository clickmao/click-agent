#!/usr/bin/env bash
# R502 证据归档: .log/.jsonl 被 gitignore ⇒ 一律转 .txt 入库 (R500 铁律)
set -uo pipefail
REPO=/home/agentuser/AgentFramework
D=${R502_ENV:-/tmp/r502_env}
cd "$REPO" || exit 0
EV=eval/rover/r502/evidence
mkdir -p "$EV"
cp1() { [ -f "$1" ] && cp "$1" "$EV/$2" || echo "[R502-evidence] 缺 $1"; }
cp1 "$D/verdict-r502.json"          verdict-r502.txt
cp1 "$D/nc-r502.json"               nc-r502.txt
cp1 "$D/logs/probe-codex.log"       probe-codex.txt
cp1 "$D/logs/probe-agent.log"       probe-agent.txt
cp1 "$D/logs/codex-audit.jsonl"     codex-audit.txt
cp1 "$D/logs/adapter.log"           adapter.txt
cp1 "$D/logs/nc4-solver-selftest.txt" nc4-solver-selftest.txt
cp1 "$D/logs/nc5-solver-dryrun.json"  nc5-solver-dryrun.txt
cp1 "$D/logs/nc3-drift.txt"         nc3-drift.txt
cp1 "$D/logs/nc3-missing.txt"       nc3-missing.txt
# 负控读数兜底: runner 的 `rm -rf $D` 会抹掉 /tmp 侧 nc-r502.json ⇒ 从**单一真源** prereg 回填
# （prereg.checks_prefirstrun 是本轮首跑前实测并已入库的读数; 只补归档, 不改判据）
if [ ! -f "$D/nc-r502.json" ]; then
  python3 - "$EV/nc-r502.json" <<'PY'
import io, json, sys
pre = json.load(io.open("eval/rover/r502/prereg_r502.json", encoding="utf-8"))
rec = pre.get("checks_prefirstrun")
if not rec:
    print("[R502-evidence] 缺 prereg.checks_prefirstrun ⇒ 不补（fail-closed, 不伪造）")
    sys.exit(0)
rec = {"source": "prereg_r502.json:checks_prefirstrun (首跑前实测; /tmp 侧原文件被 runner 清理)",
       "round": pre.get("round"), **rec}
io.open(sys.argv[1], "w", encoding="utf-8", newline="\n").write(json.dumps(rec, ensure_ascii=False, indent=1) + "\n")
print("[R502-evidence] nc-r502.json 由 prereg 回填（真源: prereg.checks_prefirstrun）")
PY
fi
# adapter 侧 usage 落盘 (side-*.json) 汇总成一行一调用的 txt
if [ -d "$D/adapter" ]; then
  python3 - "$D/adapter" > "$EV/adapter-usage.txt" <<'PY'
import glob, json, os, sys
for p in sorted(glob.glob(os.path.join(sys.argv[1], 'side-*.json'))):
    try:
        d = json.load(open(p, encoding='utf-8'))
    except Exception as e:
        print('%s PARSE_ERR %s' % (os.path.basename(p), e)); continue
    u = ((d.get('response') or {}).get('usage') or {})
    print('%s side=%s in=%s out=%s model=%s' % (
        os.path.basename(p), d.get('side'),
        u.get('prompt_tokens') or u.get('input_tokens'),
        u.get('completion_tokens') or u.get('output_tokens'),
        (d.get('request') or {}).get('model') or ((d.get('request') or {}).get('upstream_request') or {}).get('model')))
PY
fi
ls -l "$EV" | tail -n +2 | awk '{print $5, $9}'
echo "[R502-evidence] -> $EV"
