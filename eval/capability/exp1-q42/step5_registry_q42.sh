#!/usr/bin/env bash
# EXP1-Q42 step 5: 复原被重跑改动的归档 + 证据校验器 + 追加登记 + 定向重审 + 全表 check
set -u
cd /home/agentuser/AgentFramework
D=eval/capability/exp1-q42
REG=docs/verification-registry.json

echo "--- 复原含 HEAD 字段的 classified 归档 (其重跑字节漂移已留痕于本目录) ---"
git checkout -- eval/capability/exp1-q41/replay_q41_scopeA_classified.json
echo "restored_sha=$(sha256sum eval/capability/exp1-q41/replay_q41_scopeA_classified.json | cut -c1-16)"

echo "--- 输入不变证据校验器 ---"
python3 "$D/verify_replay_archive_q42.py"; echo "verify_rc=$?"

echo "--- 追加登记行 (形态由现盘反解) ---"
python3 "$D/append_rows_q42.py"; echo "append_rc=$?"

echo "--- 定向重审 (本轮 4 行) ---"
python3 eval/capability/bind_evidence.py --apply --round EXP1-Q42 --run-record "$D/bind_run_q42.json" \
  --only exp1q41.tail-lf-gate-promoted-default-on,exp1q41.tail-lf-replay-falsepositive-zero,exp1q41.drift-notice-paired-controls,exp1q40.commit-face-tail-lf-gate \
  > "$D/bind_apply_q42.txt" 2>&1; echo "bind_apply_rc=$?"
grep -E "SER_ASSERT|ONLY_SCOPE|UNCHANGED|TOUCHED|IDEMPOTENT|rows=" "$D/bind_apply_q42.txt" | tail -8 | cut -c1-200

echo "--- 登记表改动量 (numstat; 归属审计) ---"
git diff --numstat -- "$REG"

echo "--- 全表 check (应与现盘一致; 违规应清零) ---"
python3 eval/capability/bind_evidence.py --check > "$D/bind_check_q42.txt" 2>&1; echo "bind_check_rc=$?"
grep -E "FROZEN_EVIDENCE_DRIFT|VIOLATION|SER|R2E|CHECKED_WITH" "$D/bind_check_q42.txt" | head -12 | cut -c1-200

echo "--- 声明一致性 ---"
python3 eval/capability/decl_sweep.py > "$D/decl_check_q42b.txt" 2>&1; echo "decl_rc=$?"; tail -2 "$D/decl_check_q42b.txt" | cut -c1-160
