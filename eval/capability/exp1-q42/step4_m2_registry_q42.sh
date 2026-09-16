#!/usr/bin/env bash
# EXP1-Q42 step 4 (M2): 登记三条 exp1q41.* 能力 + 定向重审 + 声明刷新 + 归属审计
set -u
cd /home/agentuser/AgentFramework
D=eval/capability/exp1-q42
REG=docs/verification-registry.json

echo "REG_SHA_BEFORE=$(sha256sum "$REG" | cut -c1-16)"
echo "CLASSIFIED_SHA_BEFORE=$(sha256sum eval/capability/exp1-q41/replay_q41_scopeA_classified.json | cut -c1-16)"

echo "--- 证据再生 (确定性校验) ---"
python3 eval/capability/exp1-q41/classify_q41.py > "$D/classify_q41_regen.txt" 2>&1; echo "classify_rc=$?"
tail -4 "$D/classify_q41_regen.txt" | cut -c1-200
echo "CLASSIFIED_SHA_AFTER=$(sha256sum eval/capability/exp1-q41/replay_q41_scopeA_classified.json | cut -c1-16)"

echo "--- 追加登记行 ---"
python3 "$D/append_rows_q42.py"; echo "append_rc=$?"

echo "--- 定向重审 (仅本轮 4 行) ---"
python3 eval/capability/bind_evidence.py --apply --round EXP1-Q42 --run-record "$D/bind_run_q42.json" \
  --only exp1q41.tail-lf-gate-promoted-default-on,exp1q41.tail-lf-replay-falsepositive-zero,exp1q41.drift-notice-paired-controls,exp1q40.commit-face-tail-lf-gate \
  > "$D/bind_apply_q42.txt" 2>&1; echo "bind_rc=$?"
grep -E "AUDITED|RE_AUDITED|TOUCHED|UNCHANGED|SKIP|rows|rc=" "$D/bind_apply_q42.txt" | tail -12 | cut -c1-200

echo "--- 登记表改动量 (归属审计: 应仅为加行 + 4 行重审字段) ---"
git diff --numstat -- "$REG"
echo "REG_SHA_AFTER=$(sha256sum "$REG" | cut -c1-16)"

echo "--- 声明一致性 (decl_sweep, 只刷 version/instrument_sha12) ---"
python3 eval/capability/decl_sweep.py > "$D/decl_check_q42.txt" 2>&1; echo "decl_check_rc=$?"
tail -5 "$D/decl_check_q42.txt" | cut -c1-200
