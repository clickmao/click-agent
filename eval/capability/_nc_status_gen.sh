#!/usr/bin/env bash
# L2 负控: 注入一行坏 registry (evidence_path 分号串联) ⇒ status_gen --check 必须判 FAIL 且非零退出。
set -u
TMP="$(mktemp -d)"
python3 - "$TMP/bad.json" <<'PY'
import json,sys,pathlib
src=json.loads(pathlib.Path("docs/verification-registry.json").read_text(encoding="utf-8"))
src.setdefault("rows",[]).append({"id":"nc.injected.bad","capability":"负控注入行","level":"L2",
  "evidence_cmd":"true","evidence_path":"eval/a;eval/b","negative_control":"n/a","covers":["src/agent/IndustrialAgentV2.cs"],
  "owner_round":"R444"})
pathlib.Path(sys.argv[1]).write_text(json.dumps(src,ensure_ascii=False,indent=1),encoding="utf-8")
PY
python3 eval/capability/status_gen.py --check --registry "$TMP/bad.json" --out "$TMP/status-nc.json" > "$TMP/log.txt" 2>&1
rc=$?
grep -q "nc.injected.bad" "$TMP/log.txt" || { echo "[nc] 未点出注入行"; rm -rf "$TMP"; exit 7; }
grep -q "CHECK: FAIL" "$TMP/log.txt" || { echo "[nc] 未判 FAIL"; rm -rf "$TMP"; exit 7; }
echo "[nc status_gen] rc=$rc (期望非零 = 注入坏行被拒)"
rm -rf "$TMP"
exit $rc
