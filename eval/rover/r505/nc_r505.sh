#!/usr/bin/env bash
# R505 负控 (机械派生自 r504/nc_r504.sh; 全部本地, 不吃真机窗): 仪器判别力两端 + fail-closed + 预注册三态 + solver 自检
# 产出: $D/nc-r505.json; 并把「首跑前检查」写回 prereg (checks_prefirstrun, 不改判据条目)
set -uo pipefail
REPO=/home/agentuser/AgentFramework
D=${R505_ENV:-/tmp/r505_nc}
PRE=eval/rover/r505/prereg_r505.json
PY=python3
cd "$REPO" || exit 3
mkdir -p "$D/logs" "$D/prereg-tamper"
KEEP="$D/prereg-tamper/keep.json"
restore() { [ -f "$KEEP" ] && cp "$KEEP" "$PRE"; }
trap restore EXIT                      # 预注册临时替换必须可复原 (逐字节)
nc() { echo "[R505-NC] $*"; }
cp "$PRE" "$KEEP"

# --- NC4/NC5 solver 自检 -------------------------------------------------------
$PY eval/rover/r504/codex_solver_r504.py --selftest > "$D/logs/nc4-solver-selftest.txt" 2>&1; nc4=$?
$PY eval/rover/r504/codex_solver_r504.py --dry-run > "$D/logs/nc5-solver-dryrun.json" 2>&1; nc5=$?
nc "NC4 solver selftest rc=$nc4 (期望0); NC5 dry-run rc=$nc5 (期望0)"

# --- NC1 仪器判别力两端 (固定 json_mini 小题集) ---------------------------------
$PY eval/probe/run_probe.py --kind program --families json_mini --n 1 --seed 20260917 \
  --solver oracle --dump-tasks eval/rover/r505/taskset-r505nc.json --tag r505nc-oracle \
  > "$D/logs/nc1-oracle.txt" 2>&1; o_rc=$?
$PY eval/probe/run_probe.py --tasks eval/rover/r505/taskset-r505nc.json \
  --solver mutation:json_loose --tag r505nc-loose > "$D/logs/nc1-loose.txt" 2>&1; m_rc=$?
OJSON=$(ls -t data/probe/probe-*r505nc-oracle*.json 2>/dev/null | head -1)
MJSON=$(ls -t data/probe/probe-*r505nc-loose*.json 2>/dev/null | head -1)
nc "NC1 oracle rc=$o_rc / mutation:json_loose rc=$m_rc"

# --- NC1b 仪器判别力 (游戏族 life_k: oracle 1.0 ∧ life_wrap 0 整题全对) -----------
$PY eval/probe/run_probe.py --kind program --families life_k --n 1 --seed 20260917 \
  --solver oracle --dump-tasks eval/rover/r505/taskset-r505nc-game.json --tag r505nc-game-oracle \
  > "$D/logs/nc1b-game-oracle.txt" 2>&1; go_rc=$?
$PY eval/probe/run_probe.py --tasks eval/rover/r505/taskset-r505nc-game.json \
  --solver mutation:life_wrap --tag r505nc-game-wrap > "$D/logs/nc1b-game-wrap.txt" 2>&1; gw_rc=$?
GOJSON=$(ls -t data/probe/probe-*r505nc-game-oracle*.json 2>/dev/null | head -1)
GWJSON=$(ls -t data/probe/probe-*r505nc-game-wrap*.json 2>/dev/null | head -1)
nc "NC1b 游戏族 oracle rc=$go_rc / mutation:life_wrap rc=$gw_rc"

# --- NC1c 仪器判别力 (R504 新游戏族 sub_game: oracle 1.0 ∧ sub_greedy 0 整题全对) ----
$PY eval/probe/run_probe.py --kind program --families sub_game --n 2 --seed 20260917 \
  --solver oracle --dump-tasks eval/rover/r505/taskset-r505nc-subgame.json --tag r505nc-sub-oracle \
  > "$D/logs/nc1c-sub-oracle.txt" 2>&1; so_rc=$?
$PY eval/probe/run_probe.py --tasks eval/rover/r505/taskset-r505nc-subgame.json \
  --solver mutation:sub_greedy --tag r505nc-sub-greedy > "$D/logs/nc1c-sub-greedy.txt" 2>&1; sg_rc=$?
SOJSON=$(ls -t data/probe/probe-*r505nc-sub-oracle*.json 2>/dev/null | head -1)
SGJSON=$(ls -t data/probe/probe-*r505nc-sub-greedy*.json 2>/dev/null | head -1)
nc "NC1c 新游戏族 oracle rc=$so_rc / mutation:sub_greedy rc=$sg_rc"

# --- NC1d 仪器判别力 (R504 新游戏族 nim_multi 多堆 Nim: oracle 1.0 ∧ nim_greedy 0 整题全对) --
$PY eval/probe/run_probe.py --kind program --families nim_multi --n 2 --seed 20260917 \
  --solver oracle --dump-tasks eval/rover/r505/taskset-r505nc-nim.json --tag r505nc-nim-oracle \
  > "$D/logs/nc1d-nim-oracle.txt" 2>&1; no_rc=$?
$PY eval/probe/run_probe.py --tasks eval/rover/r505/taskset-r505nc-nim.json \
  --solver mutation:nim_greedy --tag r505nc-nim-greedy > "$D/logs/nc1d-nim-greedy.txt" 2>&1; ng_rc=$?
NOJSON=$(ls -t data/probe/probe-*r505nc-nim-oracle*.json 2>/dev/null | head -1)
NGJSON=$(ls -t data/probe/probe-*r505nc-nim-greedy*.json 2>/dev/null | head -1)
nc "NC1d 新游戏族 nim_multi oracle rc=$no_rc / mutation:nim_greedy rc=$ng_rc"

# --- NC1e 仪器判别力 (R504 新游戏族 wythoff: oracle 1.0 ∧ wyth_greedy 0 整题全对) ---------
$PY eval/probe/run_probe.py --kind program --families wythoff --n 2 --seed 20260917 \
  --solver oracle --dump-tasks eval/rover/r505/taskset-r505nc-wyth.json --tag r505nc-wyth-oracle \
  > "$D/logs/nc1e-wyth-oracle.txt" 2>&1; wo_rc=$?
$PY eval/probe/run_probe.py --tasks eval/rover/r505/taskset-r505nc-wyth.json \
  --solver mutation:wyth_greedy --tag r505nc-wyth-greedy > "$D/logs/nc1e-wyth-greedy.txt" 2>&1; wg_rc=$?
WOJSON=$(ls -t data/probe/probe-*r505nc-wyth-oracle*.json 2>/dev/null | head -1)
WGJSON=$(ls -t data/probe/probe-*r505nc-wyth-greedy*.json 2>/dev/null | head -1)
nc "NC1e 新游戏族 wythoff oracle rc=$wo_rc / mutation:wyth_greedy rc=$wg_rc"

# --- NC1f 仪器判别力 (R504 见证型 witness_crt: oracle 1.0 ∧ 错见证判红 1/1) --------------
$PY eval/probe/run_probe.py --kind math --families witness_crt --n 2 --seed 20260917 \
  --solver oracle --dump-tasks eval/rover/r505/taskset-r505nc-crt.json --tag r505nc-crt-oracle \
  > "$D/logs/nc1f-crt-oracle.txt" 2>&1; co_rc=$?
$PY eval/probe/run_probe.py --tasks eval/rover/r505/taskset-r505nc-crt.json \
  --solver mutation:wrongfinal --tag r505nc-crt-wrong > "$D/logs/nc1f-crt-wrong.txt" 2>&1; cw_rc=$?
COJSON=$(ls -t data/probe/probe-*r505nc-crt-oracle*.json 2>/dev/null | head -1)
CMJSON=$(ls -t data/probe/probe-*r505nc-crt-wrong*.json 2>/dev/null | head -1)
nc "NC1f 见证型 witness_crt oracle rc=$co_rc / mutation:wrongfinal rc=$cw_rc"

# --- NC2 缺侧 fail-closed (judge 必须 rc=3) ------------------------------------
$PY eval/rover/r505/judge_contrast_r505.py --codex "$OJSON" --prereg "$PRE" \
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
$PY eval/rover/r505/make_prereg_r505.py --check > "$D/logs/nc3-uniform.txt" 2>&1; nc3a=$?
cp "$D/prereg-tamper/drift.json" "$PRE"
$PY eval/rover/r505/make_prereg_r505.py --check > "$D/logs/nc3-drift.txt" 2>&1; nc3b=$?
cp "$D/prereg-tamper/missing.json" "$PRE"
$PY eval/rover/r505/make_prereg_r505.py --check > "$D/logs/nc3-missing.txt" 2>&1; nc3c=$?
cp "$KEEP" "$PRE"
rm -f "$KEEP"   # 关掉 EXIT trap 复原（否则 trap 会在退出时覆盖汇总写回）
$PY eval/rover/r505/make_prereg_r505.py --check > "$D/logs/nc3-restored.txt" 2>&1; nc3d=$?
nc "NC3 预注册 rc: uniform=$nc3a(0) drift=$nc3b(1) missing=$nc3c(3) restored=$nc3d(0)"

# --- 汇总 + 写回首跑前检查 ------------------------------------------------------
$PY - "$D/nc-r505.json" "$OJSON" "$MJSON" "$GOJSON" "$GWJSON" "$SOJSON" "$SGJSON" \
  "$NOJSON" "$NGJSON" "$WOJSON" "$WGJSON" "$COJSON" "$CMJSON" \
  "$nc4" "$nc5" "$nc2" "$nc3a" "$nc3b" "$nc3c" "$nc3d" "$PRE" <<'PY'
import json, sys
args = sys.argv[1:]
out, pre_p = args[0], args[-1]
(o, m, go, gw, so, sg, no, ng, wo, wg, co, cm) = args[1:13]
nc4, nc5, nc2, nc3a, nc3b, nc3c, nc3d = args[13:20]


def whole(p):
    d = json.load(open(p, encoding='utf-8-sig'))
    pt = d.get('per_task') or []
    return sum(1 for t in pt if t.get('mode') == 'ok'), len(pt)


def cases(p):
    """用例级读数 (整题判红但用例级>0 是正常的: 贪心在多数局面与最优手同值)。"""
    d = json.load(open(p, encoding='utf-8-sig'))
    ps = sum(int((t.get('passed') or 0)) for t in (d.get('per_task') or []))
    ts = sum(int((t.get('total') or 0)) for t in (d.get('per_task') or []))
    return ps, ts


o_ok, o_n = whole(o)
m_ok, m_n = whole(m)
g_ok, g_n = whole(go)
w_ok, w_n = whole(gw)
s_ok, s_n = whole(so)
sg_ok, sg_n = whole(sg)
n_ok, n_n = whole(no)
ng_ok, ng_n = whole(ng)
wo_ok, wo_n = whole(wo)
wg_ok, wg_n = whole(wg)
c_ok, c_n = whole(co)
cm_ok, cm_n = whole(cm)
rec = {
    'nc1_instrument': {'pass': bool(o_ok == o_n == 1 and m_ok == 0),
                       'oracle_whole_ok': o_ok, 'oracle_n': o_n,
                       'mutation_json_loose_whole_ok': m_ok, 'mutation_n': m_n,
                       'taskset': 'eval/rover/r505/taskset-r505nc.json',
                       'reading': '仪器两端: oracle 1.0 且 mutation 0.0'},
    'nc1b_instrument_game': {'pass': bool(g_ok == g_n == 1 and w_ok == 0),
                             'oracle_whole_ok': g_ok, 'oracle_n': g_n,
                             'mutation_life_wrap_whole_ok': w_ok, 'mutation_n': w_n,
                             'taskset': 'eval/rover/r505/taskset-r505nc-game.json',
                             'reading': '游戏族仪器两端: oracle 1.0 且 life_wrap 0 整题全对'},
    'nc1c_instrument_newgame': {'pass': bool(s_ok == s_n == 2 and sg_ok == 0),
                                'oracle_whole_ok': s_ok, 'oracle_n': s_n,
                                'mutation_sub_greedy_whole_ok': sg_ok, 'mutation_n': sg_n,
                                'taskset': 'eval/rover/r505/taskset-r505nc-subgame.json',
                                'reading': 'sub_game 仪器两端: oracle 2/2 且 sub_greedy 整题 0'},
    'nc1d_instrument_nim': {'pass': bool(n_ok == n_n == 2 and ng_ok == 0),
                            'oracle_whole_ok': n_ok, 'oracle_n': n_n,
                            'oracle_case_ok': cases(no)[0], 'oracle_case_n': cases(no)[1],
                            'mutation_nim_greedy_whole_ok': ng_ok, 'mutation_n': ng_n,
                            'mutation_case_ok': cases(ng)[0], 'mutation_case_n': cases(ng)[1],
                            'taskset': 'eval/rover/r505/taskset-r505nc-nim.json',
                            'reading': 'nim_multi 仪器两端: oracle 2/2 且 nim_greedy 整题 0 (用例级读数单列)'},
    'nc1e_instrument_wythoff': {'pass': bool(wo_ok == wo_n == 2 and wg_ok == 0),
                                'oracle_whole_ok': wo_ok, 'oracle_n': wo_n,
                                'oracle_case_ok': cases(wo)[0], 'oracle_case_n': cases(wo)[1],
                                'mutation_wyth_greedy_whole_ok': wg_ok, 'mutation_n': wg_n,
                                'mutation_case_ok': cases(wg)[0], 'mutation_case_n': cases(wg)[1],
                                'taskset': 'eval/rover/r505/taskset-r505nc-wyth.json',
                                'reading': 'wythoff 仪器两端: oracle 2/2 且 wyth_greedy 整题 0 (用例级读数单列)'},
    'nc1f_instrument_crt': {'pass': bool(c_ok == c_n == 2 and cm_ok == 0),
                            'oracle_whole_ok': c_ok, 'oracle_n': c_n,
                            'mutation_wrong_witness_whole_ok': cm_ok, 'mutation_n': cm_n,
                            'taskset': 'eval/rover/r505/taskset-r505nc-crt.json',
                            'reading': 'witness_crt 判定=逐同余式机检: oracle 2/2 且错见证整题 0'},
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
$PY eval/rover/r505/make_prereg_r505.py --check; rc_pre=$?
$PY - "$D/nc-r505.json" <<'PY'; rc_nc=$?
import json, sys
r = json.load(open(sys.argv[1], encoding='utf-8'))
ok = (r['nc1_instrument']['pass'] and r['nc1b_instrument_game']['pass']
      and r['nc1c_instrument_newgame']['pass']
      and r['nc1d_instrument_nim']['pass'] and r['nc1e_instrument_wythoff']['pass']
      and r['nc1f_instrument_crt']['pass']
      and r['nc2_missing_side_rc'] == 3
      and r['nc4_solver_selftest_rc'] == 0 and r['nc5_solver_dryrun_rc'] == 0
      and r['nc3_prereg_rc'] == {'uniform': 0, 'drift': 1, 'missing': 3, 'restored': 0})
print('NC 总判: %s' % ('OK' if ok else 'FAIL'))
sys.exit(0 if ok else 1)
PY
nc "prereg --check rc=$rc_pre (期望0); NC 总判 rc=$rc_nc (期望0)"
[ "$rc_pre" = "0" ] && [ "$rc_nc" = "0" ]
exit $?
