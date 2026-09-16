#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C3: 提交前钩子的「跨写者提交闸」机检 (stage_guard 接入 tools/hooks/pre-commit)。

背景: 同 gateway 下的兄弟作业/前台循环与本作业**共享同一工作树**。整树 `git add` 会把对侧在飞文件
      一起提交, 而提交不报错 ⇒ 归属混乱事后才发现 (R481 曾为此回退 96 行)。
本步把 stage_guard 接进钩子, 并在此用**一次性 git 夹具仓**机检其能力 (与真索引零接触):
  P1 默认关: 无 AGENTFRAMEWORK_STAGE_MANIFEST ⇒ 钩子行为与旧版逐位相同 (零回归);
  P2 清单 == staged ⇒ 放行 (rc=0);
  P3 staged 多出对侧在飞文件 ⇒ 拒绝 (rc!=0 + BLOCKED 文案);
  P4 清单文件声明了却不存在 ⇒ fail-closed 拒绝;
  P5 真仓 (本仓库) 无 env 时钩子仍 rc=0 (真机零回归)。
控制:
  N1 `same_count_wrong_content` (条数相同、内容不同) ⇒ 必须被拒 (条数口径漏检被证明);
  N2 反证: 去掉钩子里的 stage-guard 段 (内存里构造旧版) ⇒ P3 夹具变绿 ⇒ 证明该段是唯一护栏。
退出码: 0 全过 / 2 有红 / 3 环境失败。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
HOOK = 'tools/hooks/pre-commit'
GUARD = 'eval/capability/exp1-q30/stage_guard_q30.py'


def sha12(p):
    return __import__('hashlib').sha256(open(p, 'rb').read()).hexdigest()[:12]


def run_hook(cwd, env_extra, manifest=None, claim='/nonexistent/ROUND_CLAIM'):
    env = dict(os.environ)
    env['AGENTFRAMEWORK_ROUND_CLAIM'] = claim
    env.pop('AGENTFRAMEWORK_STAGE_MANIFEST', None)
    if manifest is not None:
        env['AGENTFRAMEWORK_STAGE_MANIFEST'] = manifest
    env.update(env_extra)
    p = subprocess.run(['bash', HOOK], cwd=cwd, capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def make_repo(guard_sha_expect):
    tmp = tempfile.mkdtemp(prefix='q31-hook-')
    subprocess.run(['git', 'init', '-q'], cwd=tmp, check=True)
    subprocess.run(['git', 'config', 'user.email', 'q31@local'], cwd=tmp, check=True)
    subprocess.run(['git', 'config', 'user.name', 'q31'], cwd=tmp, check=True)
    os.makedirs(os.path.join(tmp, 'tools/hooks'), exist_ok=True)
    shutil.copy(os.path.join(ROOT, HOOK), os.path.join(tmp, HOOK))
    # 夹具里的器具副本必须与真仓逐字节相同 (provenance by sha, 不测「另一个版本」)
    dst = os.path.join(tmp, GUARD)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(os.path.join(ROOT, GUARD), dst)
    got = sha12(dst)
    for rel, body in [('a/b.py', 'x=1\n'), ('sibling/half-done.py', 'y=2\n'), ('sibling/x.py', 'z=3\n')]:
        p = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'w', encoding='utf-8').write(body)
    return tmp, got


def stage(tmp, paths):
    subprocess.run(['git', 'add', '--'] + paths, cwd=tmp, check=True)


def reset_index(tmp):
    subprocess.run(['git', 'rm', '-r', '--cached', '-q', '.'], cwd=tmp, check=False)


def write_manifest(tmp, lines, name='manifest.txt'):
    p = os.path.join(tmp, name)
    open(p, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    return p


def main():
    rep = {'round': 'EXP1-Q31', 'checks': {}, 'readings': {}}
    tmp, guard_sha = make_repo(None)
    try:
        rep['readings']['guard_sha12_in_fixture'] = guard_sha
        rep['readings']['guard_sha12_in_repo'] = sha12(os.path.join(ROOT, GUARD))
        rep['checks']['P0_夹具器具逐字节同日'] = (guard_sha == rep['readings']['guard_sha12_in_repo'])
        os.remove(os.path.join(tmp, GUARD))       # 先验默认关: 连器具都不在也能 NO-OP
        # P1 默认关 (对侧文件也在 staged, 无 env ⇒ 不拦)
        stage(tmp, ['a/b.py', 'sibling/half-done.py'])
        rc, out = run_hook(tmp, {}, manifest=None)
        rep['checks']['P1_默认关零回归'] = (rc == 0 and 'STAGE_GUARD' not in out)
        rep['readings']['P1'] = {'rc': rc, 'out_tail': out.strip().splitlines()[-1:]}
        # 装回器具副本 (后续用例)
        os.makedirs(os.path.dirname(os.path.join(tmp, GUARD)), exist_ok=True)
        shutil.copy(os.path.join(ROOT, GUARD), os.path.join(tmp, GUARD))
        m_ok = write_manifest(tmp, ['a/b.py'])
        # P2 清单 == staged ⇒ 放行
        reset_index(tmp)
        stage(tmp, ['a/b.py'])
        rc, out = run_hook(tmp, {}, manifest=m_ok)
        rep['checks']['P2_清单等于staged放行'] = (rc == 0 and 'STAGE_GUARD=OK' in out)
        rep['readings']['P2'] = {'rc': rc, 'out_tail': out.strip().splitlines()[-1:]}
        # P3 对侧在飞文件多出 ⇒ 拒绝
        stage(tmp, ['sibling/half-done.py'])
        rc, out = run_hook(tmp, {}, manifest=m_ok)
        rep['checks']['P3_拒绝对侧在飞'] = (rc != 0 and 'BLOCKED' in out and 'sibling/half-done.py' in out)
        rep['readings']['P3'] = {'rc': rc, 'out': out.strip().splitlines()[-4:]}
        # N1 条数相同内容不同
        reset_index(tmp)
        stage(tmp, ['a/b.py'])
        m_wrong = write_manifest(tmp, ['sibling/x.py'], 'manifest_wrong.txt')
        rc, out = run_hook(tmp, {}, manifest=m_wrong)
        rep['checks']['N1_条数相同内容不同被拒'] = (rc != 0 and 'BLOCKED' in out)
        rep['readings']['N1'] = {'rc': rc, 'out': out.strip().splitlines()[-3:]}
        # P4 清单文件缺失 ⇒ fail-closed
        rc, out = run_hook(tmp, {}, manifest=os.path.join(tmp, 'no_such_manifest.txt'))
        rep['checks']['P4_清单缺失fail_closed'] = (rc != 0 and 'BLOCKED' in out)
        rep['readings']['P4'] = {'rc': rc, 'out': out.strip().splitlines()[-2:]}
        # N2 反证: 内存里构造「无 stage-guard 段」的旧钩子 ⇒ P3 形态必须变绿
        hook_txt = open(os.path.join(tmp, HOOK), encoding='utf-8').read()
        if '# EXP1-Q31:' not in hook_txt:
            # 钩子本身不含该段 ⇒ 反证构造不可能 ⇒ 直接判红 (这正是「空心钩子」场景, 不抛异常)
            rep['checks']['N2_反证_旧钩子漏检'] = False
            rep['readings']['N2_old_hook'] = {'error': 'hook_lacks_stage_guard_block'}
        else:
            i = hook_txt.index('# EXP1-Q31:')
            j = hook_txt.rindex('exit 0')
            old_txt = hook_txt[:i] + hook_txt[j:]
            assert 'AGENTFRAMEWORK_STAGE_MANIFEST' not in old_txt
            open(os.path.join(tmp, HOOK), 'w', encoding='utf-8').write(old_txt)
            reset_index(tmp)
            stage(tmp, ['a/b.py', 'sibling/half-done.py'])
            rc_old, out_old = run_hook(tmp, {}, manifest=m_ok)
            rep['readings']['N2_old_hook'] = {'rc': rc_old, 'has_blocked': 'BLOCKED' in out_old}
            rep['checks']['N2_反证_旧钩子漏检'] = (rc_old == 0 and 'BLOCKED' not in out_old)
            shutil.copy(os.path.join(ROOT, HOOK), os.path.join(tmp, HOOK))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # P5 真仓零回归 (默认关)
    rc_real, out_real = run_hook(ROOT, {}, manifest=None, claim='/tmp/q31_no_claim')
    rep['checks']['P5_真仓默认关放行'] = (rc_real == 0)
    rep['readings']['P5'] = {'rc': rc_real, 'out_tail': out_real.strip().splitlines()[-2:]}
    rep['n_checks'] = '%d/%d' % (sum(1 for v in rep['checks'].values() if v), len(rep['checks']))
    rep['verdict'] = 'PASS' if all(rep['checks'].values()) else 'FAIL'
    out_rel = (sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv
               else 'eval/capability/exp1-q31/scratch/verdict_q31_hook_gate.json')
    out = os.path.join(ROOT, out_rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(json.dumps(rep, ensure_ascii=False, indent=1) + '\n')
    for k, v in rep['checks'].items():
        print('%-34s %s' % (k, 'OK' if v else 'FAIL'))
    print('verdict=%s (%s)' % (rep['verdict'], rep['n_checks']))
    print('落盘 %s' % os.path.relpath(out, ROOT))
    return 0 if rep['verdict'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
