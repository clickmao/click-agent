#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q39 · 候选③ 的**钩子面机检**: 声明一致性闸 + 证据绑定闸的判别力自证 (成对)。

判据 (缺一不可; 全部在**临时树**上跑, 真仓索引/心跳不被触碰):
  G1 默认开: 夹具树里制造**声明漂移** ⇒ 钩子 rc=1 且文案含 `声明一致性闸` + 处置命令
  G2 默认开: 夹具树里制造**证据绑定违规** ⇒ 钩子 rc=1 且文案含 `证据绑定闸`
  G3 探针越权: 两闸关掉 (`=0`) ⇒ 同一漂移态下钩子 rc=0 (负控: 证明 G1 的红确实来自新闸)
  G4 空心钩子反证: 把新闸两段从钩子正文里删掉 ⇒ 验证器必须判红 (自己抓自己)
  G5 只读: 两闸全开跑完后, 夹具树里**除钩子自己**没有文件被改 (闸不写仓内字节)
  G6 真仓默认态: 真仓跑钩子 rc=0 (新闸不误伤当前树态) —— 无网络/无构建依赖
  G7 真仓关闸态: AGENTFRAMEWORK_DECL_SWEEP=0 / EVIDENCE_CHECK=0 时真仓 rc=0 (逃生通道可用)

退出码: 0 全绿 / 2 判据红 / 3 弃权 (夹具树/真仓不可用)。
"""
import contextlib
import hashlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HOOK = 'tools/hooks/pre-commit'
OUT = HERE / 'verdict_decl_hook_gate_q39.json'


def hook_text():
    return (ROOT / HOOK).read_text(encoding='utf-8')


def run_hook(cwd, env_extra=None, path=HOOK):
    env = dict(os.environ)
    env.pop('AGENTFRAMEWORK_ROUND_CLAIM', None)
    env.pop('AGENTFRAMEWORK_STAGE_MANIFEST', None)
    env.pop('AGENTFRAMEWORK_REAUDIT_GUARD', None)
    env['GIT_DIR'] = os.path.join(cwd, '.git')          # 夹具树自带 git-dir (无心跳 ⇒ 仲裁段跳过)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(['bash', path], cwd=cwd, capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def tree_digest(root):
    h = {}
    for dirpath, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d not in ('.git', '__pycache__')]
        for fn in fns:
            p = os.path.join(dirpath, fn)
            h[os.path.relpath(p, root)] = hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]
    return h


def make_fixture(mode):
    """临时树: 真钩子 + 最小 eval 面 (**自带 git 仓**, 无 status_gen ⇒ L3 段自然跳过)。

    夹具的 manifest 与登记表都是**自足最小集** (只引用夹具内确实存在的文件) —— 否则夹具会因
    「引用仓外路径」而自带违规, 闸的红就不可归因 (空心夹具)。
    """
    tmp = tempfile.mkdtemp(prefix='q39-hook-%s-' % mode)
    root = pathlib.Path(tmp)
    for rel in (HOOK, 'eval/capability/decl_sweep.py', 'eval/capability/bind_evidence.py',
                'eval/capability/face_record_canon.py'):
        src = ROOT / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
    subprocess.run(['git', 'init', '-q', str(tmp)], check=True)
    ep_a, ep_b = 'eval/capability/decl_sweep.py', 'eval/capability/bind_evidence.py'
    sha = lambda rel: hashlib.sha256((root / rel).read_bytes()).hexdigest()[:12]

    def inst_row(rid, ep, ver_bad=False):
        ver = 'content-sha12:' + ('000000000000' if ver_bad else sha(ep))
        isha = '000000000000' if ver_bad else sha(ep)
        return {'id': rid, 'kind': 'checker', 'cmd': 'true', 'expect_rc': 0, 'expect_substr': '',
                'kpi_quad': {'单位': '行', '分母': '夹具', '真值源': '夹具', '口径档': 'n/a'},
                'owner_round': 'EXP1-Q39', 'evidence_path': ep, 'version': ver,
                'version_source': 'content-sha12', 'instrument_sha12': isha,
                'input_fingerprint': [], 'input_surface': 'dynamic_corpus',
                'input_surface_source': 'audit_hook', 'input_surface_reason': '夹具最小输入面',
                'corpus_dynamic_count': 1}

    man = {'schema': 'instruments/v1', 'spec': '夹具', 'note': 'Q39 钩子闸夹具', 'round': 'EXP1-Q39',
           'owner_round': 'EXP1-Q39',
           'instruments': [inst_row('fx.decl-a', ep_a, ver_bad=(mode == 'decl_drift')),
                           inst_row('fx.decl-b', ep_b)]}
    mp = root / 'eval/capability/instruments.json'
    mp.write_text(json.dumps(man, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')

    pin = '000000000000' if mode == 'evidence_drift' else sha(ep_a)
    reg = {'schema': 'verification-registry/v1', 'updated_round': 'EXP1-Q39', 'spec': '夹具',
           'levels': {}, 'rows': [{
               'id': 'fx.reg-1', 'level': 'L2', 'capability': '夹具行', 'evidence_cmd': 'python3 ' + ep_a,
               'evidence_path': ep_a,
               'evidence_generated_with': {'evidence_kind': 'artifact', 'pin_status': 'frozen',
                                           'pin_reason': 'archived-per-round', 'artifact_sha12': pin,
                                           'instrument': ep_a, 'instrument_sha12': sha(ep_a),
                                           'binding': 'audit-pin', 'audited_by_round': 'EXP1-Q39'}}],
           'aot_check_policy': 'n/a', 'aot_check_policy_note': '夹具'}
    rp = root / 'docs/verification-registry.json'
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    subprocess.run(['git', 'add', '-A'], cwd=tmp, check=True, capture_output=True)
    return tmp


def main():
    checks, detail = {}, {}
    if not (ROOT / HOOK).exists():
        print('NO_HOOK ⇒ rc=3 弃权')
        return 3
    # G6/G7 真仓 (只读; 用 GIT_DIR 指向真仓)
    rc_real, out_real = run_hook(str(ROOT))
    checks['G6_real_repo_default_off_rc0'] = (rc_real == 0)
    detail['G6'] = {'rc': rc_real, 'tail': out_real.strip().splitlines()[-3:]}
    rc_esc, _o = run_hook(str(ROOT), {'AGENTFRAMEWORK_DECL_SWEEP': '0',
                                      'AGENTFRAMEWORK_EVIDENCE_CHECK': '0'})
    checks['G7_real_repo_escape_hatch_rc0'] = (rc_esc == 0)
    detail['G7'] = {'rc': rc_esc}

    # G1/G2/G3/G5 夹具树
    for mode, key, needle in (('decl_drift', 'G1_fixture_decl_drift_rc1', '声明一致性闸'),
                              ('evidence_drift', 'G2_fixture_evidence_violation_rc1', '证据绑定闸')):
        tmp = make_fixture(mode)
        try:
            before = tree_digest(tmp)
            rc, out = run_hook(tmp)
            after = tree_digest(tmp)
            checks[key] = (rc == 1 and needle in out)
            detail[key] = {'rc': rc, 'needle_found': needle in out,
                           'tail': out.strip().splitlines()[-4:]}
            if mode == 'decl_drift':
                rc_off, out_off = run_hook(tmp, {'AGENTFRAMEWORK_DECL_SWEEP': '0'})
                checks['G3_escape_hatch_rc0_on_same_state'] = (rc_off == 0)
                detail['G3'] = {'rc': rc_off, 'tail': out_off.strip().splitlines()[-2:]}
                changed = sorted(k for k in set(list(before) + list(after))
                                 if before.get(k) != after.get(k))
                checks['G5_gates_write_nothing_in_repo'] = (changed == [])
                detail['G5'] = {'changed_paths': changed}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # G4 空心钩子反证: 删掉两段新闸 ⇒ 本验证器必须在**同一夹具**上判红 (自己抓自己)
    tmp = make_fixture('decl_drift')
    try:
        txt = hook_text()
        i = txt.index('# EXP1-Q39:')
        j = txt.rindex('exit 0')
        hollow = txt[:i] + txt[j:]
        assert 'decl_sweep' not in hollow, '空心化失败: 新闸仍在'
        (pathlib.Path(tmp) / HOOK).write_text(hollow, encoding='utf-8')
        rc, out = run_hook(tmp)
        checks['G4_hollow_hook_detected'] = (rc == 0 and '声明一致性闸' not in out)
        detail['G4'] = {'rc': rc, 'note': '空心钩子在漂移夹具上 rc=0 ⇒ 本闸的判别力来自新段本身'}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    ok = all(checks.values())
    payload = {'round': 'EXP1-Q39', 'schema': 'decl-hook-gate/1', 'hook_sha12':
               hashlib.sha256(hook_text().encode()).hexdigest()[:12],
               'checks': checks, 'detail': detail, 'verdict': 'PASS' if ok else 'FAIL'}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    back = json.loads(OUT.read_text(encoding='utf-8'))
    print(json.dumps(checks, ensure_ascii=False))
    for k in detail:
        print('  %-34s %s' % (k, json.dumps(detail[k], ensure_ascii=False)[:200]))
    print('READBACK=%s' % ('OK' if back['verdict'] == payload['verdict'] else 'MISMATCH'))
    print('VERDICT=%s out=%s' % (payload['verdict'], OUT.name))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
