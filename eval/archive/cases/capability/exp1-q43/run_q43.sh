#!/usr/bin/env bash
# EXP1-Q43 证据收集 (零冲突轮: 不跑 dotnet / 不碰产品源码 / 不占主线轮号 R508)
# 用法: bash eval/capability/exp1-q43/run_q43.sh
set -u
cd /home/agentuser/AgentFramework
D=eval/capability/exp1-q43

echo "=== [1] after 真机读数 (来源② 换口径后) ==="
python3 scripts/capability_cycle_status.py > $D/status_after_q43.json 2> $D/status_after_q43.stderr
echo "STEP_EXIT_probe_after=$?"

echo "=== [2] 判定器自检 (夹具 + 负控) ==="
python3 scripts/capability_cycle_status.py --selftest > $D/selftest_q43.txt 2>&1
echo "STEP_EXIT_selftest_or_assert=$?"
echo "PASS=$(grep -c '^PASS' $D/selftest_q43.txt) FAIL=$(grep -c '^FAIL' $D/selftest_q43.txt)"

echo "=== [3] 逐字段前后对比 + 预注册判据 P1..P6 ==="
python3 $D/diff_q43.py > $D/verdict_q43.json 2> $D/verdict_q43.stderr
echo "STEP_EXIT_verdict=$?"

echo "=== [4] 结果 ==="
python3 -c "
import json;d=json.load(open('$D/verdict_q43.json',encoding='utf-8-sig'))
print('rc=%s failed=%s' % (d.get('rc'), d.get('failed')))
print('after.master=', json.dumps(d.get('after',{}).get('master_diag'),ensure_ascii=False))
print('new_items=', json.dumps(d.get('new_items_from_src2'),ensure_ascii=False)[:400])
"
echo "Q43_DONE"
exit 0
