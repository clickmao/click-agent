#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 候选①-b 核验: `--only` 定向重审 vs 块级文本插入 (两条独立写路径) 逐字节等价。

判据 (预注册见 prereg_q30.json): P1/P1b/P2/P3/P4/P5/P6/P7/P8/P8b + N1..N3。
纪律: 一切实验落在 eval/capability/exp1-q30/scratch/; 真登记表只被 --check 读 (读前后 sha 断言相同)。
块级插入 (路径 B) 自带独立定位/替换实现 (不用序列化器) —— 与器具的序列化器路径互为独立证据。
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
Q30 = os.path.join(ROOT, 'eval/capability/exp1-q30')
S = os.path.join(Q30, 'scratch')
TOOL = 'eval/capability/bind_evidence.py'
PRE = os.path.join(S, 'bind_evidence_pre.py')
REG = 'docs/verification-registry.json'
ROUND = 'EXP1-Q30'
TARGET = 'r479.responses-io-wire'      # 冻结行 (tracked ∧ clean) —— 打坏其 pin 制造「陈旧声明」夹具
OTHER = 'r468.gate-rules-port-diff'    # worktree-only 行 (作行级不变式的对照样本)


def sha12(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]


def rd(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def wr(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def run(args, cwd=ROOT):
    p = subprocess.run(['python3'] + args, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def block_insert(raw, row_id, new_field):
    """路径 B: 纯文本块级替换 (不用 json 序列化整份文件)。返回 (新文本, 变更键集)."""
    i = raw.index('"id": "%s"' % row_id)
    j = raw.index('\n  },', i) + len('\n  },')
    block = raw[i:j]
    k = block.index('"evidence_generated_with": ')
    ls = block.rindex('\n', 0, k) + 1
    W = block[ls:k]                                   # 该字段行前导空白
    ob = block.index('{', k)
    depth, p, in_str, esc = 0, ob, False, False
    while True:
        ch = block[p]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                break
        p += 1
    end = block.index('\n', p + 1)                    # 到该行行尾 (含可能的逗号)
    trailing = block[p + 1:end]                       # ',' 或 ''
    old = json.loads(block[ob:p + 1])
    inner = json.dumps(new_field, indent=1, ensure_ascii=False).split('\n')
    lines = [W + '"evidence_generated_with": {'] + [W + l for l in inner[1:]]
    new_block = block[:ls] + '\n'.join(lines) + trailing + block[end:]
    keys = sorted(set(old) | set(new_field))
    changed_keys = sorted(kk for kk in keys if old.get(kk) != new_field.get(kk))
    return raw[:i] + new_block + raw[j:], changed_keys, old, new_field


def rows_of(path):
    return {r.get('id'): r for r in json.load(open(path, encoding='utf-8'))['rows']}


def main():
    rep = {'round': ROUND, 'readings': {}, 'checks': {}, 'verdict': None}
    os.makedirs(S, exist_ok=True)
    reg_real = os.path.join(ROOT, REG)
    reg_sha_before = sha12(reg_real)

    # ---- 夹具: HEAD 副本 + 打坏目标行 pin (人为「陈旧声明」) ----
    fixture = os.path.join(S, 'fixture_only.json')
    raw = rd(reg_real)
    broken = raw.replace('"artifact_sha12": "3bf281ff7d7b"', '"artifact_sha12": "deadbeef0001"', 1)
    assert broken != raw, '夹具构造失败: 目标 pin 未找到'
    wr(fixture, broken)
    rep['readings']['fixture_sha12'] = sha12(fixture)

    # 派生内容 (两条路径共用同一真理源 derive(); 差异只在"怎么写盘")
    sys.path.insert(0, os.path.join(ROOT, 'eval/capability'))
    import bind_evidence as be
    # 两条路径必须用**同一轮号参数**派生 (器具侧由 --round 设置该全局; 路径 B 在此对齐 —— 否则
    #   等价判定测的是"参数不同"而不是"写路径不同", 属判据缺陷, 首跑即被自身踩到)。
    be.AUDITED_BY_ROUND = ROUND
    tracked, dirty = be.git_state(ROOT)
    row = rows_of(fixture)[TARGET]
    field = be.derive(ROOT, row, tracked, dirty)
    rep['readings']['derived_field'] = field
    rep['readings']['declared_before_fixture'] = row['evidence_generated_with']

    # ---- 路径 A: --only ----
    a = os.path.join(S, 'out_only.json')
    wr(a, broken)
    rcA, outA = run([TOOL, '--apply', '--only', TARGET, '--round', ROUND, '--registry', a])
    rep['checks']['A_rc'] = (rcA == 0)
    rep['readings']['A_stdout_head'] = outA.strip().splitlines()[:6]
    # ---- 路径 B: 块级插入 ----
    b = os.path.join(S, 'out_block.json')
    txtB, ck, old, new = block_insert(broken, TARGET, field)
    wr(b, txtB)
    rep['readings']['block_changed_keys'] = ck

    rep['checks']['P1_逐字节等价'] = (sha12(a) == sha12(b))
    rep['readings']['A_sha12'] = sha12(a)
    rep['readings']['B_sha12'] = sha12(b)
    rep['checks']['P1b_非空转'] = (sha12(a) != sha12(fixture))
    rep['checks']['N3_夹具有效'] = (field['artifact_sha12'] != 'deadbeef0001')

    # ---- P2 作用域 (行级逐字段) ----
    ra, rf = rows_of(a), rows_of(fixture)
    changed_rows = sorted(i for i in ra if ra[i] != rf[i])
    rep['readings']['changed_rows'] = changed_rows
    rep['checks']['P2_作用域'] = (changed_rows == [TARGET]
                                  and len(ra) == len(rf)
                                  and OTHER in ra and ra[OTHER] == rf[OTHER])

    # ---- P3 幂等 ----
    rcA2, outA2 = run([TOOL, '--apply', '--only', TARGET, '--round', ROUND, '--registry', a])
    rep['checks']['P3_幂等'] = (rcA2 == 0 and 'IDEMPOTENT=OK' in outA2 and sha12(a) == rep['readings']['A_sha12'])
    rep['readings']['A2_idempotent_line'] = [l for l in outA2.splitlines() if 'IDEMPOTENT' in l][:1]

    # ---- P4 未知 id / P5 缺轮号 (rc=3 + 零写入) ----
    d = os.path.join(S, 'out_unknown.json'); wr(d, broken); sd = sha12(d)
    rcD, outD = run([TOOL, '--apply', '--only', 'bogus.id.does-not-exist', '--round', ROUND, '--registry', d])
    rep['checks']['P4_未知id'] = (rcD == 3 and sha12(d) == sd)
    rep['readings']['P4_line'] = outD.strip().splitlines()[:2]
    e = os.path.join(S, 'out_noround.json'); wr(e, broken); se = sha12(e)
    rcE, outE = run([TOOL, '--apply', '--only', TARGET, '--registry', e])
    rep['checks']['P5_缺轮号'] = (rcE == 3 and sha12(e) == se)
    rep['readings']['P5_line'] = outE.strip().splitlines()[:2]
    rep['checks']['N1_零写入'] = rep['checks']['P4_未知id'] and rep['checks']['P5_缺轮号']

    # ---- P6 负控: 旧器具 (无 --only) 全表同轮号 ⇒ 触达行数 >> 1 且字节 !=  ---- (monkeypatch REG)
    pre_apply = ('import importlib.util,sys;spec=importlib.util.spec_from_file_location("p",%r);'
                 'm=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.REG=%r;'
                 'sys.argv=["x","--apply","--round",%r];sys.exit(m.main())')
    c = os.path.join(S, 'out_full_old.json'); wr(c, broken)
    rcC, outC = run(['-c', pre_apply % (PRE, os.path.relpath(c, ROOT), ROUND)])
    touched = [l for l in outC.splitlines() if 'UNCHANGED=' in l]
    rep['readings']['C_stdout_touched'] = touched
    n_touched = int(touched[0].split('/ TOUCHED=')[1].split()[0]) if touched else -1
    rep['checks']['P6_负控_去作用域'] = (rcC == 0 and n_touched > 1 and sha12(c) != rep['readings']['A_sha12'])

    # ---- P7 真登记表零副作用 ----
    rep['checks']['P7_真登记表零副作用'] = (sha12(reg_real) == reg_sha_before)
    rep['readings']['reg_real_sha12'] = sha12(reg_real)

    # ---- P8 无参 --check 零回归 (新旧 stdout 逐字节) ----
    rc_new, out_new = run([TOOL, '--check'])
    rc_old, out_old = run([PRE, '--check'])
    rep['checks']['P8_无参零回归_check'] = (out_new == out_old and rc_new == rc_old)
    rep['readings']['check_exit'] = {'new': rc_new, 'old': rc_old}
    rep['readings']['check_tail'] = out_new.strip().splitlines()[-2:]

    # ---- P8b 全表 --apply 零回归 (同 scratch → 逐字节相同) ----
    f1 = os.path.join(S, 'zr_old.json'); f2 = os.path.join(S, 'zr_new.json')
    wr(f1, rd(reg_real)); wr(f2, rd(reg_real))
    rcO, outO = run(['-c', pre_apply % (PRE, os.path.relpath(f1, ROOT), ROUND)])
    rcN, outN = run([TOOL, '--apply', '--round', ROUND, '--registry', f2])
    rep['readings']['zeroregress_apply'] = {'old_rc': rcO, 'new_rc': rcN,
                                            'old_sha12': sha12(f1), 'new_sha12': sha12(f2),
                                            'old_touched': [l for l in outO.splitlines() if 'UNCHANGED=' in l][:1],
                                            'new_touched': [l for l in outN.splitlines() if 'UNCHANGED=' in l][:1]}
    rep['checks']['P8b_无参零回归_apply'] = (rcO == rcN == 0 and sha12(f1) == sha12(f2))

    # ---- P9 候选② 前提 (重算口径: 声明 worktree-only 而重算 frozen) ----
    stale = []
    for r in json.load(open(reg_real, encoding='utf-8'))['rows']:
        if 'evidence_generated_with' not in r or not be.needs_field(r):
            continue
        f = r['evidence_generated_with']
        if f.get('pin_status') == 'live' and f.get('pin_reason') == 'worktree-only':
            dd = be.derive(ROOT, r, tracked, dirty)
            if dd['pin_status'] == 'frozen':
                stale.append(r['id'])
    rep['readings']['stale_worktree_only_ids'] = stale
    rep['checks']['P9_候选②前提为假(已闭合)'] = (len(stale) == 0)

    keys = [k for k in rep['checks'] if not k.startswith('N')]
    rep['verdict'] = 'PASS' if all(rep['checks'].values()) else 'FAIL'
    rep['failed'] = [k for k, v in rep['checks'].items() if not v]
    rep['n_checks'] = '%d/%d' % (sum(1 for v in rep['checks'].values() if v), len(rep['checks']))
    out = os.path.join(Q30, 'verdict_q30_only.json')
    wr(out, json.dumps(rep, ensure_ascii=False, indent=1) + '\n')
    for k, v in rep['checks'].items():
        print('%-28s %s' % (k, 'OK' if v else 'FAIL'))
    print('verdict=%s (%s)' % (rep['verdict'], rep['n_checks']))
    print('落盘', os.path.relpath(out, ROOT))
    return 0 if rep['verdict'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
