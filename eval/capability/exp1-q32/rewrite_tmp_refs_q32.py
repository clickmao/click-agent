#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · C1 落地: 把 `evidence_cmd` / `negative_control` 里的 /tmp 单副本引用改为仓库内路径。

依据 = 本轮机检 `tmp_path_census_q32.json` / `tmp_path_census3_q32.json` 的逐行裁定:
  · repo_identical 类 (归档副本已存在且逐位相同) ⇒ 直接改指仓库内路径;
  · 单副本脚本/编排器/项目源码类 ⇒ 先逐字归档 (archive_tmp_q32.py, sha256 已记录) 再改指归档路径;
  · 外部资产 (模型权重 / 发布物 / 外部 venv / 测试 scratch 目录) ⇒ **不动** (非「可入库未入库 ⇒ 记入诚实边界)。

三阶段 (幂等, 每阶段都有不变式):
  1. REPAIRS: 已知坏形态的定点修复 (bad→good), 幂等靠 marker 判据 (bad==0 ∧ marker==want);
  2. FIXES  : 字面替换, 幂等靠「未替换的旧出现 == 0」(兼容「新串包含旧串」的替换);
  3. CANON  : 终态不变式 (正确形态出现次数 == 期望, 坏形态 == 0)。

本脚本自身的首跑缺陷 (照原样入档, 不翻案, 同族第 2 次):
  · 缺陷 A (不变式): 首版判据写「旧字面总出现次数 == 0」, 而 `agent.formal.loop_mount` 的新串**包含**旧串
    ⇒ 误判 FAIL, 且第二次运行重复套了一层前缀 (幂等缺陷)。修 = 未替换计数 (count(old) − count(new)×count(old⊂new))。
  · 缺陷 B (重触发): 修 A 后, 该行的「补前缀」条目在 `--only` → `--group` 语义修复之后**再次触发**
    (新串形态变了 ⇒ 判成「未替换」) ⇒ 前缀被套两次。修 = 该行移出 FIXES, 改由 REPAIRS(marker 判据) + CANON 钉住。

退出码: 0 通过 (含幂等) / 2 断言失败 / 3 环境失败 (字段/字面不匹配 ⇒ 拒改)。
"""
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
REG = 'docs/verification-registry.json'
ARD = 'eval/capability/exp1-q32/archived_tmp'
RESTORE = 'eval/capability/exp1-q32/instruments/tmp_archive_restore.py'

PREFIX_ONLY = ('python3 %s --restore --only r391probe (归档件逐位还原到该路径; 冲突 fail-closed) && ' % RESTORE)
PREFIX_GROUP = ('python3 %s --restore --group r391probe (归档件逐位还原到该路径; 冲突 fail-closed) && ' % RESTORE)
PROBE_CMD = 'dotnet run -c Release --project /tmp/r391probe'

# 1) 定点修复: (row_id, field, bad, good, marker, want_marker)
REPAIRS = []

PROBE_MARKER = 'tmp_archive_restore.py'


def normalize_probe(cur):
    """把 `agent.formal.loop_mount` 的 evidence_cmd 规范化为「**单个**还原前缀 + 原命令」。

    缺陷 C (自捕, 同族第 3 次): 前缀补全 + 语义修复 (--only→--group) 相互作用 ⇒ 前缀被套两层
    (marker×2)。处置 = 以 PROBE_CMD 为锚做**确定性规范化** (前缀取单个 + 锚后原文全保留), 并断言
    终态 marker==1 ∧ PROBE_CMD==1 ∧ 无 --only 形态。幂等: 已规范 ⇒ noop。
    返回 (new_text, verdict)。
    """
    if cur.count(PROBE_MARKER) == 1 and cur.count(PROBE_CMD) == 1 and cur.startswith(PREFIX_GROUP):
        return cur, 'canonical_noop'
    pos = cur.find(PROBE_CMD)
    if pos < 0:
        return cur, 'fail_no_probe_cmd'
    new = PREFIX_GROUP + cur[pos:]
    if new.count(PROBE_MARKER) != 1 or new.count(PROBE_CMD) != 1 or '--only r391probe' in new:
        return cur, 'fail_normalize'
    return new, 'normalized'

# 2) 字面替换: (row_id, field, old, new, expected_count)
FIXES = [
    ('r462.language-agnostic-recall', 'evidence_cmd',
     'bash /tmp/r462_e2e.sh', 'bash %s/r462/r462_e2e.sh' % ARD, 1),
    ('r462.recall-reality-gate', 'evidence_cmd',
     '(原声明 bash /tmp/r462_e2e.sh 已不存在)',
     '(原声明 bash /tmp/r462_e2e.sh: EXP1-Q32 现盘实测该文件**仍存在**且为单副本 ⇒ 以现盘为准, '
     '已逐字归档 sha256=dff0133d89f8… ⇒ 入口自足化)', 1),
    ('r462.recall-reality-gate', 'negative_control',
     '见 /tmp/r462_negctl.json',
     '见 %s/r462/r462_negctl.json (原 /tmp 单副本已逐字归档, EXP1-Q32)' % ARD, 1),
    ('r457.effect-closure', 'evidence_cmd',
     'bash /tmp/r457_run_agent_tools.sh', 'bash %s/r457/r457_run_agent_tools.sh' % ARD, 1),
    ('r457.effect-closure', 'evidence_cmd',
     'bash /tmp/r457_nokey.sh', 'bash %s/r457/r457_nokey.sh' % ARD, 1),
    ('artifact.failure.feedback', 'evidence_cmd',
     'bash /tmp/gameprobe/run_r374.sh', 'bash %s/gameprobe/run_r374.sh' % ARD, 1),
    ('ask.frontend.channel', 'evidence_cmd',
     'python3 /tmp/fp375/probe.py', 'python3 %s/fp375/probe.py' % ARD, 1),
    ('ask.menu.loop', 'evidence_cmd',
     'python3 /tmp/fp376/probe2.py', 'python3 %s/fp376/probe2.py' % ARD, 1),
    ('plan.route.local_first_frontend_kpi', 'evidence_cmd',
     '/tmp/r382/plan_frontend_probe.py', '%s/r382/plan_frontend_probe.py' % ARD, 1),
    ('kpi.prompt_cache_hit', 'evidence_cmd',
     '/tmp/gameprobe/r377_kpi.telemetry', '%s/gameprobe/r377_kpi.telemetry' % ARD, 1),
    ('r458.humanized-continuation', 'evidence_cmd',
     'bash /tmp/r458_setup.sh && bash /tmp/r458_run.sh',
     'bash eval/rover/r458/r458_setup.sh && bash eval/rover/r458/r458_run.sh', 1),
    ('r460.brevity-menu-cache', 'evidence_cmd',
     'bash /tmp/r460_setup.sh && bash /tmp/r460_run.sh',
     'bash eval/rover/r460/r460_setup.sh && bash eval/rover/r460/r460_run.sh', 1),
    ('r461.contract-not-front-and-hit-budget', 'evidence_cmd',
     'bash /tmp/r461_setup.sh && bash /tmp/r461_run.sh',
     'bash eval/rover/r461/r461_setup.sh && bash eval/rover/r461/r461_run.sh', 1),
    ('llamacpp.process.boundary', 'evidence_cmd',
     '--prompt-file /tmp/probe-r408/prompt.txt',
     '--prompt-file eval/rover/r409/prompt.txt (逐位相同副本; 原 /tmp 为易失路径)', 1),
]

# 3) 终态不变式: (row_id, field, substring, expected_count)
CANON = [
    ('agent.formal.loop_mount', 'evidence_cmd', 'tmp_archive_restore.py --restore --group r391probe', 1),
    ('agent.formal.loop_mount', 'evidence_cmd', '--only r391probe', 0),
    ('agent.formal.loop_mount', 'evidence_cmd', PROBE_CMD, 1),
    ('r462.language-agnostic-recall', 'evidence_cmd', '/tmp/', 0),
    ('r457.effect-closure', 'evidence_cmd', '/tmp/', 0),
    ('kpi.prompt_cache_hit', 'evidence_cmd', '/tmp/', 0),
]


def unreplaced(cur, old, new):
    """字段里**尚未被替换**的旧出现次数 (兼容新串包含旧串)。"""
    return cur.count(old) - cur.count(new) * new.count(old)


def main():
    dry = '--dry-run' in sys.argv
    raw = open(os.path.join(ROOT, REG), encoding='utf-8', newline='').read()
    doc = json.loads(raw)
    tail = '\n' if raw.endswith('\n') else ''
    if json.dumps(doc, indent=1, ensure_ascii=False) + tail != raw:
        print('SER_ASSERT=FAIL (序列化器不能逐字节复现原文件 ⇒ 拒写)')
        return 3
    print('SER_ASSERT=OK (indent=1, ensure_ascii=False, tail=%s)' % ('LF' if tail else 'NONE'))

    by_id = {r.get('id'): r for r in doc['rows']}
    need = sorted({f[0] for f in list(FIXES) + list(REPAIRS) + list(CANON) if f[0] not in by_id})
    if need:
        print('ENV_FAIL: 登记表无这些行 %s' % need)
        return 3

    todo, marks = [], []
    for rid, field, bad, good, marker, want_marker in REPAIRS:
        cur = by_id[rid].get(field) or ''
        if cur.count(bad) == 0 and cur.count(marker) == want_marker:
            marks.append((rid, field, 'noop', cur.count(bad), cur.count(marker), 'ok'))
            continue
        if cur.count(bad) != 1:
            print('REPAIR_ASSERT=FAIL %s.%s bad×%d (期望 1) ⇒ 拒改' % (rid, field, cur.count(bad)))
            return 3
        by_id[rid][field] = cur.replace(bad, good)
        marks.append((rid, field, 'applied', bad.count(marker), want_marker, 'ok'))
        print('REPAIR %s.%s 删除重复前缀形态 (marker 保持 ×%d)' % (rid, field, want_marker))

    cur = by_id['agent.formal.loop_mount'].get('evidence_cmd') or ''
    new, v = normalize_probe(cur)
    print('NORMALIZE agent.formal.loop_mount.evidence_cmd = %s (marker×%d → ×%d)'
          % (v, cur.count(PROBE_MARKER), new.count(PROBE_MARKER)))
    if v.startswith('fail'):
        return 3
    if v == 'normalized':
        by_id['agent.formal.loop_mount']['evidence_cmd'] = new
        marks.append(('agent.formal.loop_mount', 'evidence_cmd', 'normalized', 1, 1, 'ok'))

    for rid, field, old, new, want in FIXES:
        cur = by_id[rid].get(field) or ''
        un = unreplaced(cur, old, new)
        if un == 0 and (new in cur):
            continue
        if cur.count(old) != want:
            print('LITERAL_ASSERT=FAIL %s.%s old×%d 期望 %d ⇒ 拒改 (不猜)' % (rid, field, cur.count(old), want))
            return 3
        todo.append((rid, field, old, new, want))

    print('LITERAL_ASSERT=OK (FIXES %d 条, 待改 %d 条)' % (len(FIXES), len(todo)))
    if not todo and all(m[2] == 'noop' for m in marks):
        print('IDEMPOTENT=OK (无变化)')
        return idempotent_check(by_id, CANON)

    if dry:
        for rid, field, old, new, want in todo:
            print('  DRY %-42s %-16s %s → %s' % (rid, field, old[:38], new[:52]))
        print('DRY_RUN=OK (未写盘)')
        return 0

    for rid, field, old, new, want in todo:
        by_id[rid][field] = (by_id[rid].get(field) or '').replace(old, new)

    out = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    open(os.path.join(ROOT, REG), 'w', encoding='utf-8', newline='').write(out)
    back = open(os.path.join(ROOT, REG), encoding='utf-8', newline='').read()
    print('WRITE_READBACK=%s' % ('OK' if back == out else 'MISMATCH'))
    if back != out:
        return 2
    d2 = json.loads(back)
    b2 = {r.get('id'): r for r in d2['rows']}
    ok_rows = len(d2['rows']) == len(doc['rows'])
    print('ROW_CONSERVATION=%s (%d 行)' % ('OK' if ok_rows else 'FAIL', len(d2['rows'])))
    bad = [(rid, field, unreplaced(b2[rid].get(field) or '', old, new), (b2[rid].get(field) or '').count(new))
           for rid, field, old, new, want in todo
           if unreplaced(b2[rid].get(field) or '', old, new) != 0
           or (b2[rid].get(field) or '').count(new) != want]
    print('POST_LITERAL=%s %s' % ('OK' if not bad else 'FAIL', bad if bad else '未替换旧出现×0 ∧ new×1'))
    print('CHANGED_ROWS=%d %s' % (len(todo), sorted({c[0] for c in todo})))
    print(subprocess.run(['git', 'diff', '--numstat', '--', REG], cwd=ROOT, capture_output=True,
                         text=True).stdout.strip())
    rc = 0 if (ok_rows and not bad) else 2
    return max(rc, idempotent_check(b2, CANON))


def idempotent_check(by_id, canon):
    bad = []
    for rid, field, sub, want in canon:
        cur = by_id[rid].get(field) or ''
        if cur.count(sub) != want:
            bad.append((rid, field, sub[:44], cur.count(sub), want))
    print('CANON=%s %s' % ('OK' if not bad else 'FAIL', bad if bad else '%d 条终态不变式全过' % len(canon)))
    return 0 if not bad else 2


if __name__ == '__main__':
    sys.exit(main())
