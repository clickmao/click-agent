#!/usr/bin/env bash
# R502 负控 (全部本地, 不吃真机窗): 仪器判别力两端 + fail-closed + 预注册三态 + solver 自检
# 产出: $D/nc-r502.json; 并把「首跑前检查」写回 prereg (checks_prefirstrun, 不改判据条目)
set -uo pipefail
REPO=/home/agentuser/AgentFramework
D=${R502_ENV:-/tmp/r502_env}
PRE=eval/rover/r502/prereg_r502.json
PY=python3
cd "$REPO" || exit 3
mkdir -p "$D/logs" "$D/prereg-tamper"
KEEP="$D/prereg-tamper/keep.json"
restore() { [ -f "$KEEP" ] && cp "$KEEP" "$PRE"; }
trap restore EXIT                      # 预注册临时替换必须可复原 (逐字节)
nc() { echo "[R502-NC] $*"; }
cp "$PRE" "$KEEP"

# --- NC4/NC5 solver 自检 -------------------------------------------------------
$PY eval/rover/r502/codex_solver_r502.py --selftest > "$D/logs/nc4-solver-selftest.txt" 2>&1; nc4=$?
$PY eval/rover/r502/codex_solver_r502.py --dry-run > "$D/logs/nc5-solver-dryrun.json" 2>&1; nc5=$?
nc "NC4 solver selftest rc=$nc4 (期望0); NC5 dry-run rc=$nc5 (期望0)"

# --- NC1 仪器判别力两端 (固定 json_mini 小题集) ---------------------------------
$PY eval/probe/run_probe.py --kind program --families json_mini --n 1 --seed 20260917 \
  --solver oracle --dump-tasks eval/rover/r502/taskset-r502nc.json --tag r502nc-oracle \
  > "$D/logs/nc1-oracle.txt" 2>&1; o_rc=$?
$PY eval/probe/run_probe.py --tasks eval/rover/r502/taskset-r502nc.json \
  --solver mutation:json_loose --tag r502nc-loose > "$D/logs/nc1-loose.txt" 2>&1; m_rc=$?
OJSON=$(ls -t data/probe/probe-*r502nc-oracle*.json 2>/dev/null | head -1)
MJSON=$(ls -t data/probe/probe-*r502nc-loose*.json 2>/dev/null | head -1)
nc "NC1 oracle rc=$o_rc / mutation:json_loose rc=$m_rc"

# --- NC1b 仪器判别力 (游戏族 life_k: oracle 1.0 ∧ life_wrap 0 整题全对) -----------
$PY eval/probe/run_probe.py --kind program --families life_k --n 1 --seed 20260917 \
  --solver oracle --dump-tasks eval/rover/r502/taskset-r502nc-game.json --tag r502nc-game-oracle \
  > "$D/logs/nc1b-game-oracle.txt" 2>&1; go_rc=$?
$PY eval/probe/run_probe.py --tasks eval/rover/r502/taskset-r502nc-game.json \
  --solver mutation:life_wrap --tag r502nc-game-wrap > "$D/logs/nc1b-game-wrap.txt" 2>&1; gw_rc=$?
GOJSON=$(ls -t data/probe/probe-*r502nc-game-oracle*.json 2>/dev/null | head -1)
GWJSON=$(ls -t data/probe/probe-*r502nc-game-wrap*.json 2>/dev/null | head -1)
nc "NC1b 游戏族 oracle rc=$go_rc / mutation:life_wrap rc=$gw_rc"

# --- NC2 缺侧 fail-closed (judge 必须 rc=3) ------------------------------------
$PY eval/rover/r502/judge_contrast_r502.py --codex "$OJSON" --prereg "$PRE" \
  > "$D/logs/nc2-judge-missing-side.txt" 2>&1; nc2=$?
nc "NC2 缺 agent 侧 judge rc=$nc2 (期望3)"

# --- NC3 预注册三态 (篡改 ⇒ 1; 缺件 ⇒ 3; 复原 ⇒ 0) -----------------------------
$PY - "$KEEP" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
t = json.loads(json.dumps(d)); t['files_sha256']['taskset'] = 'deadbeef' * 8
json.dump(t, open(sys.argv[1].replace('keep.json', 'drift.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
m = json.loads(json.dumps(d)); m['files_sha256'].pop('taskset'); m.pop('criteria', None)
json.dump(m, open(sys.argv[1].replace('keep.json', 'missing.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
PY
$PY eval/rover/r502/make_prereg_r502.py --check > "$D/logs/nc3-uniform.txt" 2>&1; nc3a=$?
cp "$D/prereg-tamper/drift.json" "$PRE"
$PY eval/rover/r502/make_prereg_r502.py --check > "$D/logs/nc3-drift.txt" 2>&1; nc3b=$?
cp "$D/prereg-tamper/missing.json" "$PRE"
$PY eval/rover/r502/make_prereg_r502.py --check > "$D/logs/nc3-missing.txt" 2>&1; nc3c=$?
cp "$KEEP" "$PRE"
rm -f "$KEEP"   # 关掉 EXIT trap 复原（否则 trap 会在退出时覆盖汇总写回）
$PY eval/rover/r502/make_prereg_r502.py --check > "$D/logs/nc3-restored.txt" 2>&1; nc3d=$?
nc "NC3 预注册 rc: uniform=$nc3a(0) drift=$nc3b(1) missing=$nc3c(3) restored=$nc3d(0)"

# --- 汇总 + 写回首跑前检查 ------------------------------------------------------
$PY - "$D/nc-r502.json" "$OJSON" "$MJSON" "$GOJSON" "$GWJSON" "$nc4" "$nc5" "$nc2" "$nc3a" "$nc3b" "$nc3c" "$nc3d" "$PRE" <<'PY'
import json, sys
out, ojson, mjson, gojson, gwjson, nc4, nc5, nc2, nc3a, nc3b, nc3c, nc3d, pre_p = sys.argv[1:14]

def whole(p):
    d = json.load(open(p, encoding='utf-8-sig'))
    pt = d.get('per_task') or []
    return sum(1 for t in pt if t.get('mode') == 'ok'), len(pt)

o_ok, o_n = whole(ojson)
m_ok, m_n = whole(mjson)
g_ok, g_n = whole(gojson)
w_ok, w_n = whole(gwjson)
rec = {
    'nc1_instrument': {'pass': bool(o_ok == o_n == 1 and m_ok == 0),
                       'oracle_whole_ok': o_ok, 'oracle_n': o_n,
                       'mutation_json_loose_whole_ok': m_ok, 'mutation_n': m_n,
                       'taskset': 'eval/rover/r502/taskset-r502nc.json',
                       'reading': '仪器两端: oracle 1.0 且 mutation 0.0'},
    'nc1b_instrument_game': {'pass': bool(g_ok == g_n == 1 and w_ok == 0),
                             'oracle_whole_ok': g_ok, 'oracle_n': g_n,
                             'mutation_life_wrap_whole_ok': w_ok, 'mutation_n': w_n,
                             'taskset': 'eval/rover/r502/taskset-r502nc-game.json',
                             'reading': '游戏族仪器两端: oracle 1.0 且 life_wrap 0 整题全对'},
    'nc2_missing_side_rc': int(nc2), 'nc4_solver_selftest_rc': int(nc4),
    'nc5_solver_dryrun_rc': int(nc5),
    'nc3_prereg_rc': {'uniform': int(nc3a), 'drift': int(nc3b),
                      'missing': int(nc3c), 'restored': int(nc3d)},
}
json.dump(rec, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
pre = json.load(open(pre_p, encoding='utf-8'))
pre['checks_prefirstrun'] = rec
json.dump(pre, open(pre_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(rec, ensure_ascii=False, indent=1))
PY

# --- 总判 ----------------------------------------------------------------------
$PY eval/rover/r502/make_prereg_r502.py --check; rc_pre=$?
$PY - "$D/nc-r502.json" <<'PY'; rc_nc=$?
import json, sys
r = json.load(open(sys.argv[1], encoding='utf-8'))
ok = (r['nc1_instrument']['pass'] and r['nc1b_instrument_game']['pass']
      and r['nc2_missing_side_rc'] == 3
      and r['nc4_solver_selftest_rc'] == 0 and r['nc5_solver_dryrun_rc'] == 0
      and r['nc3_prereg_rc'] == {'uniform': 0, 'drift': 1, 'missing': 3, 'restored': 0})
print('NC 总判: %s' % ('OK' if ok else 'FAIL'))
sys.exit(0 if ok else 1)
PY
nc "prereg --check rc=$rc_pre (期望0); NC 总判 rc=$rc_nc (期望0)"
[ "$rc_pre" = "0" ] && [ "$rc_nc" = "0" ]
exit $?
