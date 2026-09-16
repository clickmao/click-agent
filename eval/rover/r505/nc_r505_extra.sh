#!/usr/bin/env bash
# R505 新增负控（针对本轮修复的失败模式: 命名空间碰撞 / 判分后覆盖 / 归因器乱凑）
# 产出: $D/nc-extra-r505.json; 并把 3 块写回 prereg.checks_prefirstrun（不改判据条目）
# 全部本地, 不吃真机窗; 不修改任何历史证据（对 R504 证据只读）。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
cd "$REPO" || exit 3
D=${R505_NC_ENV:-/tmp/r505_nc}
PRE=eval/rover/r505/prereg_r505.json
PY=python3
mkdir -p "$D"/{logs,guard,clean,attr}
nc() { echo "[R505-NC+] $*"; }

# --- NC1g 命名空间守卫（H1g-①, 两端: 工作目录占用 / 证据目录占用）---------------
mkdir -p "$D/guard/occupied"; echo x > "$D/guard/occupied/foreign.txt"
R505_ENV="$D/guard/occupied" bash eval/rover/r505/run_contrast_r505.sh guard \
  > "$D/logs/nc1g-dir-occupied.txt" 2>&1; g1=$?
mkdir -p eval/rover/r505/evidence/ncguard; echo x > eval/rover/r505/evidence/ncguard/foreign.txt
R505_ENV="$D/guard/fresh" R505_FORCE=0 bash eval/rover/r505/run_contrast_r505.sh ncguard \
  > "$D/logs/nc1g-evdir-occupied.txt" 2>&1; g2=$?
rm -rf eval/rover/r505/evidence/ncguard
# 「未启动任何作业」的独立取证: 守卫路径下不得出现 adapter 日志/新文件
g1_new=$(ls -A "$D/guard/occupied" | wc -l)          # 只应有 foreign.txt
g2_new=$(ls -A "$D/guard/fresh" 2>/dev/null | wc -l) # fresh 目录不得被创建
nc "NC1g 守卫 rc: D占用=$g1(期望4) EV占用=$g2(期望4); 占用目录文件数=$g1_new(期望1) fresh目录项=$g2_new(期望0)"

# --- NC1h 归因器判别力（H1h, 两端: 已知构成必须归位 / 无消息面必须拒猜）--------
rm -rf "$D/attr/clean"; mkdir -p "$D/attr/clean"
cp /tmp/r504_env/adapter/side-agent-0{10,11,12,13,14,15,16,17}.json "$D/attr/clean"/ 2>/dev/null
$PY eval/rover/r505/attr_calls_r505.py --dir "$D/attr/clean" \
  --out "$D/attr/agent8.json" > "$D/logs/nc1h-agent8.txt" 2>&1; h1=$?
rm -rf "$D/attr/all"; mkdir -p "$D/attr/all"
cp /tmp/r504_env/adapter/side-codex-0{01,02,03}.json "$D/attr/all"/ 2>/dev/null
$PY eval/rover/r505/attr_calls_r505.py --dir "$D/attr/all" \
  --out "$D/attr/codex3.json" > "$D/logs/nc1h-codex3.txt" 2>&1; h2=$?
nc "NC1h 归因器 rc: agent8=$h1(期望0) codex3=$h2(期望2=拒猜)"

# --- NC11 污染检出器两端（H11 + H9 的取证器判别力）-----------------------------
$PY eval/rover/r505/check_usage_replay.py --usage eval/rover/r504/evidence/adapter-usage.txt \
  --dir /tmp/r504_env/adapter --out "$D/nc11-r504-positive.json" > "$D/logs/nc11-pos.txt" 2>&1; p1=$?
rm -rf "$D/clean/dir"; mkdir -p "$D/clean/dir"
cp "$D"/attr/clean/side-agent-*.json "$D/clean/dir"/ 2>/dev/null
$PY eval/rover/r505/manifest_r505.py --dir "$D/clean/dir" --side agent \
  --usage-out "$D/clean/usage.txt" --manifest-out "$D/clean/manifest.json" > "$D/logs/nc11-manifest.txt" 2>&1; p_man=$?
$PY eval/rover/r505/check_usage_replay.py --usage "$D/clean/usage.txt" --dir "$D/clean/dir" \
  --out "$D/nc11-clean.json" > "$D/logs/nc11-clean.txt" 2>&1; p2=$?
$PY - "$D/clean/dir" <<'PY'
import json, sys, glob, os
p = sorted(glob.glob(os.path.join(sys.argv[1], "side-agent-*.json")))[0]
d = json.load(open(p, encoding='utf-8-sig'))
u = d['response']['usage']
u['prompt_tokens'] = int(u.get('prompt_tokens') or 0) + 7      # 注入污染 (只动副本)
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
print("[R505-NC+] 注入污染:", os.path.basename(p), "prompt_tokens += 7")
PY
$PY eval/rover/r505/check_usage_replay.py --usage "$D/clean/usage.txt" --dir "$D/clean/dir" \
  --out "$D/nc11-mutated.json" > "$D/logs/nc11-mutated.txt" 2>&1; p3=$?
nc "NC11 检出器 rc: R504阳性=$p1(期望2) 干净副本=$p2(期望0) 注污副本=$p3(期望2)"

# --- 汇总 + 写回 prereg -------------------------------------------------------
$PY - "$D/nc-extra-r505.json" "$PRE" "$g1" "$g2" "$g1_new" "$g2_new" "$h1" "$h2" "$p1" "$p2" "$p3" \
  "$D/attr/agent8.json" "$D/attr/codex3.json" "$D/nc11-r504-positive.json" "$D/nc11-mutated.json" <<'PY'
import json, sys
(out, pre_p, g1, g2, g1n, g2n, h1, h2, p1, p2, p3, a8, c3, pos, mut) = sys.argv[1:]
a8d = json.load(open(a8, encoding='utf-8'))['sides'].get('agent', {})
c3d = json.load(open(c3, encoding='utf-8'))['sides'].get('codex', {})
posd = json.load(open(pos, encoding='utf-8'))
mutd = json.load(open(mut, encoding='utf-8'))
rec = {
  'nc1g_namespace_guard': {
    'pass': bool(int(g1) == 4 and int(g2) == 4 and int(g1n) == 1 and int(g2n) == 0),
    'rc_dir_occupied': int(g1), 'rc_evidence_occupied': int(g2),
    'files_in_occupied_dir': int(g1n), 'entries_in_fresh_dir': int(g2n),
    'reading': '守卫两端都 rc=4 且未创建/未启动任何作业（占用目录只剩 foreign.txt）'},
  'nc1h_attribution_discrimination': {
    'pass': bool(int(h1) == 0 and a8d.get('calls') == 8 and not a8d.get('unmatched')
                and int(h2) == 2 and c3d.get('calls') == 3 and len(c3d.get('unmatched') or []) == 3),
    'rc_agent8': int(h1), 'agent8_calls': a8d.get('calls'), 'agent8_unmatched': a8d.get('unmatched'),
    'rc_codex3': int(h2), 'codex3_calls': c3d.get('calls'), 'codex3_unmatched_n': len(c3d.get('unmatched') or []),
    'reading': '已知构成的 8 条本侧调用 8/8 归位; 无 tail_messages 的 codex 调用 3/3 记未归因（禁硬凑）'},
  'nc11_contamination_detector': {
    'pass': bool(int(p1) == 2 and len(posd.get('mismatch') or []) == 9 and int(p2) == 0 and int(p3) == 2
                 and len(mutd.get('mismatch') or []) == 1),
    'rc_r504_positive': int(p1), 'r504_mismatch_n': len(posd.get('mismatch') or []),
    'r504_mismatch_files': [m['file'] for m in posd.get('mismatch') or []],
    'rc_clean_copy': int(p2), 'rc_injected_copy': int(p3),
    'injected_mismatch_n': len(mutd.get('mismatch') or []),
    'reading': 'R504 实况被判红且点名 9 文件（=后续作业覆盖数）; 干净副本 rc=0; 注入 1 处污染即点名 1 文件'},
}
json.dump(rec, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
pre = json.load(open(pre_p, encoding='utf-8'))
chk = pre.get('checks_prefirstrun') or {}
chk.update(rec)
pre['checks_prefirstrun'] = chk
json.dump(pre, open(pre_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(rec, ensure_ascii=False, indent=1))
ok = all(v['pass'] for v in rec.values())
print('NC-extra 总判: %s' % ('OK' if ok else 'FAIL'))
sys.exit(0 if ok else 1)
PY
rc=$?
$PY eval/rover/r505/make_prereg_r505.py --check; rc_pre=$?
nc "NC-extra rc=$rc (期望0); prereg --check rc=$rc_pre (期望0)"
[ "$rc" = "0" ] && [ "$rc_pre" = "0" ]
exit $?
