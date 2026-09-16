#!/usr/bin/env bash
# EXP1-Q30 · bind_evidence --check 的负向控制 (注入缺陷 ⇒ 必须判红)。
# 缺陷注入 = 把 scratch 登记表副本里**首条 frozen 行**的 artifact_sha12 改成 deadbeef0001,
#   然后跑 --check: 期望 rc=2 且 stdout 含 VIOLATION。检出 ⇒ 印 NC_DETECTED 且 rc=0。
# 纪律: 只动 scratch 副本 (真登记表零写入); 退出码语义分类 (0=检出, 1=未检出/异常)。
set -u
cd "$(dirname "$0")/../../.." || exit 99
S=eval/capability/exp1-q30/scratch
mkdir -p "$S"
python3 - "$S/nc_reg.json" <<'PY' || exit 1
import json, re, sys
out = sys.argv[1]
raw = open('docs/verification-registry.json', encoding='utf-8', newline='').read()
doc = json.loads(raw)
row = next(r for r in doc['rows']
           if r.get('evidence_generated_with', {}).get('pin_status') == 'frozen'
           and re.fullmatch(r'[0-9a-f]{12}', str(r['evidence_generated_with'].get('artifact_sha12') or '')))
pin = row['evidence_generated_with']['artifact_sha12']
if raw.count('"artifact_sha12": "%s"' % pin) < 1:
    print('NC_SETUP_FAIL: pin token 未找到'); sys.exit(1)
open(out, 'w', encoding='utf-8', newline='').write(
    raw.replace('"artifact_sha12": "%s"' % pin, '"artifact_sha12": "deadbeef0001"', 1))
print('NC_INJECTED row=%s pin=%s -> deadbeef0001' % (row['id'], pin))
PY
python3 eval/capability/bind_evidence.py --check --registry "$S/nc_reg.json" > "$S/nc_bind.log" 2>&1
rc=$?
if [ "$rc" != "2" ]; then echo "NC_NOT_DETECTED (rc=$rc, 期望 2)"; tail -3 "$S/nc_bind.log"; exit 1; fi
if ! grep -q "VIOLATION" "$S/nc_bind.log"; then echo "NC_NO_VIOLATION_LINE"; exit 1; fi
echo "NC_DETECTED (rc=2 + VIOLATION 命中; 明细: $S/nc_bind.log)"
exit 0
