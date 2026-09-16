#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q40 · 候选⑤ 成对控制: 「归档面分母参数化」——分母一变不再整体弃权。

判据 (预注册见 eval/capability/exp1-q40/prereg_q40.json H7)：
  D1 零回归 (真 Q37 记录, 29 结点): 固有读数**逐字段不变** (per_node + 摘要在册键),
     新增键 = 且仅 = 元数据键集 (denominator_* / new_nodes / missing_nodes / source_record)。
  D2 判别力自证 (前态器具, HEAD 版本): 注入 1 个 directory_node ⇒ **rc=3 整体弃权** (缺陷态:
     「分母一变面就瞎了」)。
  D3 修复生效 (现盘器具): 同一注入记录 ⇒ rc=0 ∧ denominator_actual=30 ∧ new_nodes 恰为该结点
     ∧ 在**实分母**上守恒 (rows == dispositions_sum == 30) ∧ 29 个固有结点读数不变。
  D4 负控 (仍须弃权的情形): 记录里零个 directory_node ⇒ rc=3 (无可判对象; 不伪造 PASS)。

夹具纪律: 真 Q37 记录只读; 一切落盘走 /tmp (--out / --archive-root) ⇒ 真仓零写入。
退出码: 0 全绿 / 2 判据红 / 3 弃权。
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True,
                                   text=True, check=True).stdout.strip())
ARCHIVER = 'eval/capability/exp1-q38/archive_dir_nodes_q38.py'
Q37_REC = ROOT / 'eval/capability/exp1-q37/archive_selfsufficiency_q37.json'
REG_OUT = ROOT / 'eval/capability/exp1-q38/archive_dir_nodes_q38.json'
HERE = pathlib.Path(__file__).resolve().parent
SCRATCH = pathlib.Path('/tmp/q40_denom')
# 前态器具的**提交 sha** (修复前最后一次提交)。禁写 HEAD: 修复一旦提交, HEAD 即是修复态,
# 该锚会让「缺陷复现」臂静默失效 (EXP1-Q40 实测: 提交后成对控制 rc=2)。
PRE_STATE = '2718f9fc85a38b509feb781185fc494e14f586c8'
META_KEYS = {'denominator_expected_registered', 'denominator_actual', 'denominator_registry_source',
             'denominator_registered_keys_n', 'new_nodes', 'missing_nodes', 'source_record'}


DRIVER = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""夹具驱动器: 以**未改动的**归档器字节为被测件, 只注入路径常量 (ROOT/Q37_REC/OUT/ARCH)。

为什么不用 CLI: 前态器具 (HEAD 版本) 无 argv 解析 ⇒ 若把它复制到 /tmp 运行, 它由自身位置推出的
ROOT/Q37_REC 会指向 /tmp/eval/... (FileNotFoundError, rc=1) —— 那是夹具缺陷, 不是被测行为。
路径注入只改「被测件读哪个文件」, 不改分母逻辑本身 (D2 判的是分母不符时的分支)。
"""
import importlib.util, json, pathlib, sys

arch, rec, out, archroot, root = sys.argv[1:6]
spec = importlib.util.spec_from_file_location('under_test', arch)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.ROOT = pathlib.Path(root)
m.Q37_REC = pathlib.Path(rec)
m.OUT = pathlib.Path(out)
m.ARCH = pathlib.Path(archroot)
m.LISTONLY = pathlib.Path('/tmp/q40_denom_listonly')
print('PLUMBING root=%s rec=%s out=%s arch=%s' % (root, rec, out, archroot))
try:
    sys.exit(m.main())
except SystemExit:
    raise
'''


def run(archiver, rec, out, archroot, env=None):
    drv = SCRATCH / 'runner.py'
    drv.write_text(DRIVER, encoding='utf-8')
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run(['python3', str(drv), str(archiver), str(rec), str(out), str(archroot),
                        str(ROOT)], cwd=str(ROOT), capture_output=True, text=True, env=e)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def main():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    reg = json.loads(REG_OUT.read_text(encoding='utf-8'))
    reg_nodes = sorted(reg['per_node'].keys())
    print('FIXTURE registered_nodes=%d arvn=%s' % (len(reg_nodes), reg.get('equivalence_face_n')))

    pre = SCRATCH / 'tree/eval/capability/exp1-q38/archiver_prefix.py'
    pre.parent.mkdir(parents=True, exist_ok=True)
    blob = subprocess.run(['git', 'show', '%s:%s' % (PRE_STATE, ARCHIVER)], cwd=str(ROOT),
                          capture_output=True)
    assert blob.returncode == 0, '前态器具取不到'
    assert subprocess.run(['git', 'merge-base', '--is-ancestor', PRE_STATE, 'HEAD'],
                          cwd=str(ROOT)).returncode == 0, '前态 sha 不是 HEAD 祖先'
    assert hashlib.sha256(blob.stdout).hexdigest() != \
        hashlib.sha256((ROOT / ARCHIVER).read_bytes()).hexdigest(), '前态与现盘同字节 ⇒ 复现臂失效'
    pre.write_bytes(blob.stdout)
    # 前态件必须放在**同构深度**的目录里: 它在 import 期就执行 `ROOT = HERE.parents[2]`
    #   (无 argv 解析) ⇒ 直接放 /tmp 根会 IndexError ⇒ 那是夹具缺陷, 不是被测行为。
    assert 'IndexError' not in run(pre, Q37_REC, SCRATCH / 'smoke.json', SCRATCH / 'arch_smoke')[1][-200:]
    print('TOOL_PRE_SHA12=%s TOOL_NOW_SHA12=%s (must differ)'
          % (hashlib.sha256(blob.stdout).hexdigest()[:12],
             hashlib.sha256((ROOT / ARCHIVER).read_bytes()).hexdigest()[:12]))

    checks, detail = {}, {}

    # ---- D1 真记录: 零回归 ----------------------------------------------------------
    out_real = SCRATCH / 'real.json'
    arch_real = SCRATCH / 'arch_real'
    rc, o = run(ROOT / ARCHIVER, Q37_REC, out_real, arch_real)
    real = json.loads(out_real.read_text(encoding='utf-8')) if out_real.is_file() else {}
    # 非语义字段白名单 (被夹具主动重定向的字段): 值必须**等于注入值**, 只作信息项, 不参与逐字段相等。
    NONSEM = {'archive_root': os.path.relpath(str(arch_real), str(ROOT))}
    shared = [k for k in reg if k not in META_KEYS and k not in NONSEM and k != 'source']
    diffs = {k: {'reg': reg.get(k), 'now': real.get(k)} for k in shared if reg.get(k) != real.get(k)}
    nonsem_ok = all(real.get(k) == v for k, v in NONSEM.items())
    extra_keys = sorted(set(real) - set(reg))
    detail['D1'] = {'rc': rc, 'registered_keys': len(reg), 'now_keys': len(real),
                    'shared_key_diffs': {k: v for k, v in list(diffs.items())[:4]},
                    'diff_n': len(diffs), 'extra_keys': extra_keys,
                    'nonsem_whitelist': NONSEM, 'nonsem_ok': nonsem_ok}
    checks['D1_real_record_zero_regression'] = (rc == 0 and not diffs and nonsem_ok
                                                and set(extra_keys) <= META_KEYS
                                                and real.get('denominator_actual') == 29
                                                and real.get('new_nodes') == [])

    # ---- 注入 1 个 directory_node 的 scratch 记录 ------------------------------------
    src = json.loads(Q37_REC.read_text(encoding='utf-8'))
    dir_nodes = [r['node'] for r in src['disposition'] if r.get('reason') == 'directory_node']
    cand = next((r['node'] for r in src['disposition']
                 if r.get('reason') != 'directory_node' and r['node'] in src['per_node']
                 and (src['per_node'][r['node']].get('n_refs') or 0) > 0), None)
    if cand is None:
        print('INJECTION_TARGET=NONE ⇒ rc=3 弃权 (无法构造分母位移)')
        return 3
    inj = json.loads(Q37_REC.read_text(encoding='utf-8'))
    for r in inj['disposition']:
        if r['node'] == cand:
            r['reason'] = 'directory_node'
    inj_path = SCRATCH / 'q37_injected.json'
    inj_path.write_text(json.dumps(inj, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
    inj_nodes = [r['node'] for r in inj['disposition'] if r.get('reason') == 'directory_node']
    print('INJECTED node=%s (原因 %s→directory_node) denom %d→%d'
          % (cand, '非 directory_node', len(dir_nodes), len(inj_nodes)))

    # D2 前态: 整体弃权
    rc_pre, o_pre = run(pre, inj_path, SCRATCH / 'pre.json', SCRATCH / 'arch_pre')
    detail['D2'] = {'rc': rc_pre, 'mismatch_line': 'DENOMINATOR_MISMATCH' in o_pre,
                    'tail': o_pre.strip().splitlines()[-2:]}
    checks['D2_pre_abstains_on_denominator_shift(缺陷复现)'] = (rc_pre == 3
                                                                and 'DENOMINATOR_MISMATCH' in o_pre)

    # D3 现盘: 在实分母上判
    out_inj = SCRATCH / 'inj.json'
    rc_post, o_post = run(ROOT / ARCHIVER, inj_path, out_inj, SCRATCH / 'arch_inj')
    cur = json.loads(out_inj.read_text(encoding='utf-8')) if out_inj.is_file() else {}
    node_diffs = [n for n in reg_nodes
                  if reg['per_node'].get(n) != cur.get('per_node', {}).get(n)
                  and reg['per_node'].get(n) is not None]
    detail['D3'] = {'rc': rc_post, 'denominator_actual': cur.get('denominator_actual'),
                    'new_nodes': cur.get('new_nodes'), 'conservation': cur.get('conservation'),
                    'node_diffs': node_diffs[:5], 'node_diff_n': len(node_diffs),
                    'extern_holdout': cur.get('equivalence_face_n'),
                    'denominator_line': [l for l in o_post.splitlines() if l.startswith('DENOMINATOR')]}
    checks['D3_post_judges_on_actual_denominator'] = (
        rc_post == 0 and cur.get('denominator_actual') == len(inj_nodes)
        and cur.get('new_nodes') == [cand]
        and cur.get('conservation', {}).get('c0_rows_eq_denominator') is True
        and cur.get('conservation', {}).get('c1_dispositions_sum') is True)
    checks['D3_registered_nodes_readings_unchanged'] = (not node_diffs)

    # ---- D4 负控: 零 directory_node ⇒ 仍弃权 ----------------------------------------
    empty = json.loads(Q37_REC.read_text(encoding='utf-8'))
    empty['disposition'] = [r for r in empty['disposition'] if r.get('reason') != 'directory_node']
    empty_path = SCRATCH / 'q37_empty.json'
    empty_path.write_text(json.dumps(empty, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
    rc_e, o_e = run(ROOT / ARCHIVER, empty_path, SCRATCH / 'e.json', SCRATCH / 'arch_e')
    detail['D4'] = {'rc': rc_e, 'empty_line': 'DENOMINATOR_EMPTY=0' in o_e}
    checks['D4_empty_denominator_still_abstains'] = (rc_e == 3 and 'DENOMINATOR_EMPTY=0' in o_e)

    ok = all(checks.values())
    payload = {'round': 'EXP1-Q40', 'schema': 'selftest-q40-denom/1',
               'prereg': 'eval/capability/exp1-q40/prereg_q40.json',
               'fixture': {'registered_nodes_n': len(reg_nodes), 'injected_node': cand,
                           'tool_pre_sha12': hashlib.sha256(blob.stdout).hexdigest()[:12],
                           'tool_now_sha12': hashlib.sha256((ROOT / ARCHIVER).read_bytes()).hexdigest()[:12]},
               'checks': checks, 'detail': detail, 'verdict': 'PASS' if ok else 'FAIL'}
    outp = HERE / 'selftest_q40_denom.json'
    outp.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for k in sorted(checks):
        print('%-52s %s' % (k, 'PASS' if checks[k] else 'FAIL'))
    print('VERDICT=%s out=%s' % (payload['verdict'], outp))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
