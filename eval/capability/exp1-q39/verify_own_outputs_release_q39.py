#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q39 · 候选②的**白名单成对控制**: 声明式自身产物释放「写事件判定」, 但不得顺手吞掉真红。

背景 (T15 实测): 面 rc=1 的唯一原因 = 新登记的 ③ 每次运行都重写自己的证据 JSON ⇒ 归 self_write。
处置 = 把两件新器具的自身产物加进 `FACE_OUTPUTS` (与 Q25/Q33 同族, 先例明确)。**降级类改动必须成对**:

  W1 声明的自身产物: 命令写它 ⇒ 面判**绿** (写事件被释放)
  W2 **未声明的**既有 tracked 产物: 同一机制下命令写它 ⇒ 面判**红** (释放没有扩大成"什么都放行")
  W3 释放**逐条可见**: 面 stdout 恒打 `FACE_OUTPUTS_DECLARED n=<k> ...`, 且两件新产物在列
  W4 释放只覆盖「写事件」, 不覆盖「内容一致性」: ③ 的证据内容由 instrument_sha12 + 成对判据钉住
     (机检 = 变异 bind_evidence.py 的 sha 后, r476 行判红; 与 Q39 census c8 同源)

全部用上游 gate API 在 /tmp 夹具上跑 (`SideEffectGate`), 不触碰真仓产物。
退出码: 0 全绿 / 2 判据红 / 3 弃权 (gate 模块不可用)。
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GATE_MOD = ROOT / 'eval/capability/exp1-q22/side_effect_gate.py'
CHK = ROOT / 'eval/capability/instruments_check.py'
OUT = HERE / 'verdict_own_outputs_release_q39.json'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def declared_face_outputs():
    src = CHK.read_text(encoding='utf-8')
    ns = {}
    # 只取 FACE_OUTPUTS 的**最终值**: 复跑模块级代码不可行 (会 import 一堆依赖), 故按 AST 求值。
    import ast
    tree = ast.parse(src)
    vals = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'FACE_OUTPUTS'
                                               for t in node.targets):
            vals.append(('assign', node.value))
        elif isinstance(node, ast.AugAssign) and getattr(node.target, 'id', None) == 'FACE_OUTPUTS':
            vals.append(('augassign', node.value))
    acc = set()
    ns = {'FACE_OUTPUTS': set()}      # 逐步喂回: 后续赋值引用了 FACE_OUTPUTS 自身 (|= 与推导式)
    for kind, v in vals:
        ns['FACE_OUTPUTS'] = set(acc)
        try:
            val = eval(compile(ast.Expression(v), '<f>', 'eval'), {}, ns)   # noqa: S307 (本仓内源码)
        except Exception as exc:
            print('AST_EVAL_SKIP %s: %s' % (type(exc).__name__, exc))
            return None, 'ast_eval_failed'
        acc = (acc | set(val)) if kind == 'augassign' else set(val)
    return acc, 'ok'


def fixture(mode, gate_mod):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='q39-whitelist-'))
    (tmp / 'eval/capability').mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', str(tmp)], check=True)
    declared = 'eval/capability/fixture_declared.json'
    undeclared = 'eval/capability/fixture_undeclared.json'
    for rel in (declared, undeclared):
        p = tmp / rel
        p.write_text('{"v": 1}\n', encoding='utf-8')
    subprocess.run(['git', 'add', '-A'], cwd=str(tmp), check=True, capture_output=True)
    target = declared if mode == 'declared' else undeclared
    # 上游 gate 的 run() 接**命令串** (它自己用 strace -f -y 包装)
    cmd = 'bash -c "echo 2 > %s"' % target
    g = gate_mod.SideEffectGate(str(tmp), face_outputs={declared}, scratch=())
    g.begin()
    g.run(cmd)
    rep = g.end()
    return tmp, rep, {'declared': declared, 'undeclared': undeclared}


def main():
    if not GATE_MOD.exists() or not CHK.exists():
        print('GATE_OR_CHECKER_MISSING ⇒ rc=3 弃权')
        return 3
    gate_mod = load(GATE_MOD, 'seg_q39')
    decl, why = declared_face_outputs()
    if decl is None:
        print('FACE_OUTPUTS 求值失败 (%s) ⇒ rc=3 弃权' % why)
        return 3
    checks, detail = {}, {}
    tmp1, rep_decl, paths = fixture('declared', gate_mod)
    try:
        checks['W1_declared_own_output_released'] = (not rep_decl['red']
                                                     and not rep_decl['self_writes'])
        detail['W1'] = {'red': rep_decl['red'], 'verdict': rep_decl['verdict'],
                        'self_writes': [w['path'] for w in rep_decl['self_writes']]}
    finally:
        subprocess.run(['rm', '-rf', str(tmp1)], check=False)
    tmp2, rep_und, _p = fixture('undeclared', gate_mod)
    try:
        checks['W2_undeclared_write_still_red'] = bool(
            rep_und['red'] and any(w['path'] == paths['undeclared'] for w in rep_und['self_writes']))
        detail['W2'] = {'red': rep_und['red'], 'verdict': rep_und['verdict'],
                        'self_writes': [w['path'] for w in rep_und['self_writes']]}
    finally:
        subprocess.run(['rm', '-rf', str(tmp2)], check=False)
    want = {'eval/capability/exp1-q38/archive_dir_nodes_q38.json',
            'eval/capability/exp1-q38/bind_evidence_tail_selftest_q38.json'}
    checks['W3_new_outputs_in_declared_set'] = want.issubset(decl)
    checks['W3b_stdout_marker_present'] = 'FACE_OUTPUTS_DECLARED n=' in CHK.read_text(encoding='utf-8')
    detail['W3'] = {'declared_n': len(decl), 'wanted_subset_ok': want.issubset(decl)}
    # W4: 内容一致性不由白名单负责 (变异 instrument_sha ⇒ 行仍判红), 由 census 件同源机检
    census = HERE / 'census_artifact_class_q39_post.json'
    c8 = False
    if census.exists():
        c8 = bool(json.loads(census.read_text(encoding='utf-8'))['fixture_checks']
                  .get('c8_broken_instrument_sha_is_red'))
    checks['W4_content_pinned_elsewhere'] = bool(c8)
    detail['W4'] = {'census_c8': c8,
                    'note': '写事件释放; 内容闸仍由 instrument_sha12 / 投影 pin 承担'}
    ok = all(checks.values())
    payload = {'round': 'EXP1-Q39', 'schema': 'own-outputs-release/1',
               'checks': checks, 'detail': detail, 'verdict': 'PASS' if ok else 'FAIL'}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    back = json.loads(OUT.read_text(encoding='utf-8'))
    print(json.dumps(checks, ensure_ascii=False))
    for k in detail:
        print('  %-34s %s' % (k, json.dumps(detail[k], ensure_ascii=False)[:180]))
    print('READBACK=%s' % ('OK' if back['verdict'] == payload['verdict'] else 'MISMATCH'))
    print('VERDICT=%s out=%s' % (payload['verdict'], OUT.name))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
