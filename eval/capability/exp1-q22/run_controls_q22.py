#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q22 · 归因式副作用闸控制矩阵 (预注册先于运行: eval/capability/exp1-q22/prereg_q22.json)。

控制面 (每个控制 = 一次独立窗口; 白名单只含探针文件, 以证明跟踪通道非空心):
  C0  基线                       : 只有白名单探针写入          ⇒ 不判红, trace 事件 >=1
  C1  自写(已脏路径)             : 本面命令写 c1.txt            ⇒ self_write 判红; 旧闸集合差为空(漏检)
  C2  外国写者(持写句柄)         : 外部进程写 c2.txt 后**保持句柄** ⇒ foreign_write 不判红 + live_fd 带 pid
  C2b 同一路径由本面命令写       : 上面两行的成对控制            ⇒ self_write 判红 (判别器非恒绿)
  C3  窗内无人动                : c3.txt 脏但内容未变          ⇒ pre_existing 不判红
  C3b 自写(对已脏路径重复写)     : 本面命令改写 c3b.txt          ⇒ self_write 判红 + 旧闸盲区记为证据
  C4  外国写者(写后关句柄)       : 外部进程写 c4.txt 后退出      ⇒ foreign_write 不判红 (Q21 事故类: 旧闸判红)
  C6  干净→脏(tracked 夹具)      : 本面命令写已提交且干净的夹具  ⇒ self_write 判红 ∧ 旧闸亦判红 (不回归)
  C7  跟踪通道不可用             : 强制无 strace                ⇒ measure-failed (弃权: 不判绿不判红)
"""
import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import side_effect_gate as seg  # noqa: E402

CTRL = ROOT / 'eval/capability/exp1-q22-controls'
FIX = CTRL / 'fixtures'
PROBE = CTRL / 'probe.txt'
TRACKED = CTRL / 'tracked_fixture.txt'
SIG = pathlib.Path('/tmp/q22sig')
WRITER = (
    "import os, sys, time\n"
    "sig, target, mode = sys.argv[1], sys.argv[2], sys.argv[3]\n"
    "for _ in range(600):\n"
    "    if os.path.exists(sig):\n"
    "        break\n"
    "    time.sleep(0.05)\n"
    "fh = open(target, 'a', encoding='utf-8')\n"
    "fh.write('foreign-write\\n')\n"
    "fh.flush()\n"
    "if mode == 'hold':\n"
    "    time.sleep(900)\n"
    "else:\n"
    "    fh.close()\n"
)


def rel(p):
    return str(pathlib.Path(p).resolve().relative_to(ROOT.resolve()))


def probe_cmd():
    return "printf 'probe\\n' >> %s" % PROBE


def write_cmd(target, text='x\\n'):
    return "printf '%s' >> %s" % (text, target)


def start_foreign(target, mode):
    if SIG.exists():
        SIG.unlink()
    return subprocess.Popen([sys.executable, '-c', WRITER, str(SIG), str(target), mode],
                            start_new_session=True)


def fire():
    SIG.write_text('go\n', encoding='utf-8')


def wait_until(pred, timeout=8.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return True
        time.sleep(0.05)
    return False


def new_gate(extra_white=(), force_no_trace=False):
    return seg.SideEffectGate(ROOT, face_outputs=[rel(PROBE)] + [rel(x) for x in extra_white],
                              scratch=(), force_no_trace=force_no_trace)


def summarize(rep):
    return {
        'verdict': rep['verdict'], 'red': rep['red'], 'measurement_ok': rep['measurement_ok'],
        'reasons': rep['reasons'],
        'self_writes': [w['path'] for w in rep['self_writes']],
        'touched_and_gone': [w['path'] for w in rep['touched_and_gone']],
        'foreign_writes': [w['path'] for w in rep['foreign_writes']],
        'pre_existing': rep['pre_existing'],
        'old_gate_delta': rep['old_gate_delta'],
        'old_gate_false_reds': rep['old_gate_false_reds'],
        'old_gate_missed_self_writes': rep['old_gate_missed_self_writes'],
        'live_fd_pids': sorted({e['pid'] for w in rep['foreign_writes'] for e in w.get('live_fd', [])}),
        'trace': rep['trace'], 'conservation': rep['conservation'],
        'census_n': len(rep['census_in_repo_cwd']),
        'census_cmds': [c['cmd'][:60] for c in rep['census_in_repo_cwd']][:6],
        'log_bytes': rep['trace']['log_bytes'],
    }


def evaluate(expect, rep):
    s = summarize(rep)
    res = {}
    for k, v in expect.items():
        if k == 'red':
            res[k] = (s['red'] is v)
        elif k == 'verdict':
            res[k] = (s['verdict'] == v)
        elif k == 'measurement_ok':
            res[k] = (s['measurement_ok'] is v)
        elif k == 'self_has':
            res[k] = (rel(v) in s['self_writes'])
        elif k == 'self_empty':
            res[k] = (s['self_writes'] == [] and s['touched_and_gone'] == [])
        elif k == 'foreign_has':
            res[k] = (rel(v) in s['foreign_writes'])
        elif k == 'foreign_empty':
            res[k] = (s['foreign_writes'] == [])
        elif k == 'pre_has':
            res[k] = (rel(v) in s['pre_existing'])
        elif k == 'old_delta_empty':
            res[k] = (s['old_gate_delta'] == [])
        elif k == 'old_delta_has':
            res[k] = (rel(v) in s['old_gate_delta'])
        elif k == 'old_missed_has':
            res[k] = (rel(v) in s['old_gate_missed_self_writes'])
        elif k == 'live_fd_nonempty':
            res[k] = (len(s['live_fd_pids']) >= 1)
        elif k == 'live_fd_empty':
            res[k] = (s['live_fd_pids'] == [])
        elif k == 'trace_events_min':
            res[k] = (s['trace']['events'] >= v)
        elif k == 'raw_events_min':
            res[k] = (s['trace'].get('raw_events', 0) >= v)
        elif k == 'probe_in_raw':
            res[k] = (str(pathlib.Path(PROBE).resolve()) in set(s['trace'].get('raw_paths_sample') or []))
        elif k == 'conservation_ok':
            res[k] = (s['conservation']['ok'] is True)
        elif k == 'probe_not_flagged':
            res[k] = (rel(PROBE) not in s['self_writes'] and rel(PROBE) not in s['foreign_writes']
                      and rel(PROBE) not in s['pre_existing'])
        else:
            res[k] = None
    return res


def run_control(tag, cmds, expect, extra_white=(), force_no_trace=False, pre=None, mid=None):
    g = new_gate(extra_white, force_no_trace=force_no_trace)
    g.begin()
    ctx = {}
    if pre:
        pre(ctx)
    outs = []
    for c in cmds:
        rc, out = g.run(c)
        outs.append({'cmd': c, 'rc': rc,
                     'out_tail': (out.strip().splitlines()[-1][:120] if out.strip() else '')})
    if mid:
        mid(ctx, g)
    rep = g.end()
    checks = evaluate(expect, rep)
    return {'tag': tag, 'expect': expect, 'observed': summarize(rep), 'checks': checks,
            'pass': all(checks.values()), 'cmds': outs, 'report': rep}


def c2_like(tag, mode, expect, target_name):
    tgt = FIX / target_name
    if tgt.exists():
        tgt.unlink()
    g = new_gate()
    g.begin()
    proc = start_foreign(tgt, mode)
    g.run(probe_cmd())
    fire()
    ok_write = wait_until(lambda: tgt.exists() and tgt.read_text(encoding='utf-8').strip() != '')
    if mode == 'hold':
        rep = g.end()
        proc.kill()
        proc.wait(timeout=10)
    else:
        proc.wait(timeout=10)
        rep = g.end()
    checks = evaluate(expect, rep)
    checks['foreign_write_landed'] = bool(ok_write)
    return {'tag': tag, 'expect': expect, 'observed': summarize(rep), 'checks': checks,
            'pass': all(checks.values()), 'cmds': [{'cmd': probe_cmd(), 'rc': 0, 'out_tail': ''}],
            'report': rep}


def c8_nested_gate():
    """外层窗内跑「自身也带闸」的被包裹器具 (L2 面的真实嵌套形态: l2.instruments-check 行)。
    实测缺陷: 嵌套 strace 被内核拒绝 (PTRACE_TRACEME: Operation not permitted) ⇒ 内层命令整条判红 (假红)。
    修法 = 重入标记: 后代进程见 Q22_SIDE_EFFECT_GATE 即不重复挂闸 (外层覆盖整棵进程树)。
    设计边界 (本控制当场暴露): 外层窗口的白名单必须与被包裹器具自身的写面**一致**
    —— 否则被包裹器具的合法写点会落进外层的 self_write (本轮用「镜像白名单」构造真实集成形态)。"""
    face_out = {'eval/capability/instruments-check.json', 'eval/capability/instruments-check-drift.json',
                'eval/capability/instruments-check-surface-claim.json',
                'eval/capability/instruments-check-surface-unknown.json',
                'eval/capability/instruments-check-nc-notapplied.json'}
    scratch = ('eval/capability/exp1-q19/l2runs/', 'eval/capability/exp1-q20/l2runs/',
               'eval/capability/exp1-q21/', 'eval/capability/exp1-q21-selfcheck/')
    cmd = 'python3 eval/capability/instruments_check.py --only exp1q1.scope-selftest'
    g = seg.SideEffectGate(ROOT, face_outputs=face_out, scratch=scratch)
    g.begin()
    rc, out = g.run(cmd)
    rep = g.end()
    checks = {
        'nested_rc0': (rc == 0),
        'no_ptrace_reject': ('PTRACE_TRACEME' not in out),
        'nested_marks_inherit': ('外层闸标记在场' in out),
        'outer_gate_clean': (rep['red'] is False and rep['measurement_ok'] is True
                             and rep['self_writes'] == []),
        'conservation_ok': (rep['conservation']['ok'] is True),
    }
    return {'tag': 'C8_nested_gate_reentrancy', 'expect': {'nested_rc0': True, 'no_ptrace_reject': True,
                                                           'nested_marks_inherit': True,
                                                           'outer_gate_clean': True, 'conservation_ok': True},
            'observed': summarize(rep), 'checks': checks, 'pass': all(checks.values()),
            'cmds': [{'cmd': cmd, 'rc': rc,
                      'out_tail': out.strip().splitlines()[0][:120] if out.strip() else ''}],
            'report': rep}


def main():
    CTRL.mkdir(parents=True, exist_ok=True)
    FIX.mkdir(parents=True, exist_ok=True)
    PROBE.write_text('probe-seed\n', encoding='utf-8')

    results = []

    # C0 基线: 只有白名单探针写入
    results.append(run_control(
        'C0_baseline', [probe_cmd() + '; true'],
        {'red': False, 'measurement_ok': True, 'self_empty': True, 'foreign_empty': True,
         'raw_events_min': 1, 'probe_in_raw': True, 'conservation_ok': True, 'probe_not_flagged': True}))

    # C1 自写 (已脏路径) —— 旧闸集合差为空 = 旧闸漏检
    c1 = FIX / 'c1.txt'
    c1.write_text('seed\n', encoding='utf-8')
    results.append(run_control(
        'C1_self_on_dirty_before', [probe_cmd(), write_cmd(c1)],
        {'red': True, 'self_has': c1, 'old_delta_empty': True, 'old_missed_has': c1,
         'probe_not_flagged': True, 'conservation_ok': True}))

    # C2 外国写者持句柄
    results.append(c2_like(
        'C2_foreign_live_fd', 'hold',
        {'red': False, 'measurement_ok': True, 'foreign_has': FIX / 'c2.txt',
         'live_fd_nonempty': True, 'probe_not_flagged': True, 'conservation_ok': True},
        'c2.txt'))

    # C2b 同一路径由本面命令写 (成对控制)
    c2b = FIX / 'c2b.txt'
    if c2b.exists():
        c2b.unlink()
    results.append(run_control(
        'C2b_self_same_shape', [probe_cmd(), write_cmd(c2b)],
        {'red': True, 'self_has': c2b, 'old_delta_has': c2b, 'probe_not_flagged': True,
         'conservation_ok': True}))

    # C3 窗内无人动
    c3 = FIX / 'c3.txt'
    c3.write_text('seed\n', encoding='utf-8')
    results.append(run_control(
        'C3_pre_existing', [probe_cmd() + '; true'],
        {'red': False, 'self_empty': True, 'pre_has': c3, 'foreign_empty': True,
         'probe_not_flagged': True, 'conservation_ok': True}))

    # C3b 对已脏路径重复写 —— Q21 盲区
    c3b = FIX / 'c3b.txt'
    c3b.write_text('seed\n', encoding='utf-8')
    results.append(run_control(
        'C3b_self_repeat_on_dirty', [probe_cmd(), write_cmd(c3b)],
        {'red': True, 'self_has': c3b, 'old_delta_empty': True, 'old_missed_has': c3b,
         'probe_not_flagged': True, 'conservation_ok': True}))

    # C4 外国写者写后关句柄 (Q21 事故类)
    results.append(c2_like(
        'C4_foreign_closed_fd', 'close',
        {'red': False, 'measurement_ok': True, 'foreign_has': FIX / 'c4.txt',
         'live_fd_empty': True, 'old_delta_has': FIX / 'c4.txt', 'probe_not_flagged': True,
         'conservation_ok': True},
        'c4.txt'))

    # C6 干净→脏 (tracked 夹具; 需先提交)
    blob_before = subprocess.run(['git', 'rev-parse', 'HEAD:%s' % rel(TRACKED)], cwd=str(ROOT),
                                 capture_output=True, text=True).stdout.strip()
    dirty_before = rel(TRACKED) in seg.SideEffectGate(ROOT, face_outputs=[rel(PROBE)]).dirty_paths()
    if not blob_before or dirty_before:
        results.append({'tag': 'C6_clean_to_dirty_tracked', 'expect': {}, 'observed': {},
                        'checks': {'fixture_committed_and_clean': False}, 'pass': False,
                        'cmds': [{'cmd': 'git rev-parse HEAD:<tracked>', 'rc': 1, 'out_tail': blob_before}]})
    else:
        rec = run_control(
            'C6_clean_to_dirty_tracked', [probe_cmd(), write_cmd(TRACKED)],
            {'red': True, 'self_has': TRACKED, 'old_delta_has': TRACKED, 'probe_not_flagged': True,
             'conservation_ok': True})
        subprocess.run(['git', 'checkout', '--', rel(TRACKED)], cwd=str(ROOT), check=False)
        blob_after = subprocess.run(['git', 'hash-object', rel(TRACKED)], cwd=str(ROOT),
                                    capture_output=True, text=True).stdout.strip()
        rec['checks']['restored_byte_identical'] = (blob_after == blob_before)
        rec['pass'] = all(rec['checks'].values())
        results.append(rec)

    # C7 跟踪通道不可用 ⇒ 弃权
    c7 = FIX / 'c7.txt'
    c7.write_text('seed\n', encoding='utf-8')
    results.append(run_control(
        'C7_trace_unavailable', [probe_cmd(), write_cmd(c7)],
        {'verdict': 'measure-failed', 'measurement_ok': False, 'red': False,
         'self_empty': True, 'conservation_ok': True}, force_no_trace=True))

    # C8 嵌套闸重入 (外层窗内跑自身带闸的器具)
    results.append(c8_nested_gate())

    # ---- 判据汇总 ----
    by_tag = {r['tag']: r for r in results}
    def ok(tag, key):
        return bool(by_tag.get(tag, {}).get('checks', {}).get(key))
    criteria = {
        'P1_conservation': all(r['observed'].get('conservation', {}).get('ok') for r in results
                               if r['observed']),
        'P2_self_channel': (ok('C1_self_on_dirty_before', 'self_has') and ok('C0_baseline', 'raw_events_min')
                            and ok('C0_baseline', 'probe_in_raw')),
        'P3_foreign_channel': (ok('C4_foreign_closed_fd', 'foreign_has') and ok('C2_foreign_live_fd', 'live_fd_nonempty')
                               and ok('C2b_self_same_shape', 'self_has')),
        'P4_q21_blind_spot_closed': (ok('C3b_self_repeat_on_dirty', 'self_has')
                                     and ok('C3b_self_repeat_on_dirty', 'old_missed_has')),
        'P5_no_detection_regression': (ok('C6_clean_to_dirty_tracked', 'self_has')
                                       and ok('C6_clean_to_dirty_tracked', 'old_delta_has')
                                       and ok('C6_clean_to_dirty_tracked', 'restored_byte_identical')),
        'P6_whitelist_semantics': all(ok(r['tag'], 'probe_not_flagged') for r in results
                                      if 'probe_not_flagged' in r['checks']),
        'P7_measure_failure_visible': (ok('C7_trace_unavailable', 'verdict')
                                       and ok('C7_trace_unavailable', 'measurement_ok')),
        'P8_integration_zero_regress': None,      # 由 run_integration_q22.py 单独判定
        'P9_registry_refresh': None,              # 由 refresh_changed_q22.py 单独判定
    }
    # 事后判据单列 (预注册之后才暴露的缺陷类): 本轮集成跑当场抓到「嵌套 strace 不被内核允许」
    # ⇒ 内层器具被判假红; 修法=重入标记。此判据不得回写成预注册命中。
    posthoc = {
        'P10_nested_gate_reentrancy': (ok('C8_nested_gate_reentrancy', 'nested_rc0')
                                       and ok('C8_nested_gate_reentrancy', 'no_ptrace_reject')
                                       and ok('C8_nested_gate_reentrancy', 'nested_marks_inherit')),
    }
    verdict = {
        'round': 'EXP1-Q22', 'schema': 'q22-controls/1',
        'controls_pass': sum(1 for r in results if r['pass']), 'controls_total': len(results),
        'criteria': criteria,
        'checks_posthoc': posthoc,
        'all_pass_except_deferred': all(v for k, v in criteria.items() if v is not None) and
                                    all(r['pass'] for r in results),
        'results': results,
    }
    (HERE / 'controls_q22.json').write_text(json.dumps(verdict, ensure_ascii=False, indent=1, default=str) + '\n',
                                            encoding='utf-8')
    lines = []
    for r in results:
        lines.append('%-28s %s %s' % (r['tag'], 'PASS' if r['pass'] else 'FAIL', json.dumps(r['observed'], ensure_ascii=False)))
        for k, v in r['checks'].items():
            if not v:
                lines.append('    check FAIL: %s' % k)
    lines.append('')
    for k, v in list(criteria.items()) + list(posthoc.items()):
        lines.append('%-36s %s' % (k, v))
    lines.append('controls: %d/%d pass' % (verdict['controls_pass'], verdict['controls_total']))
    (HERE / 'evidence_q22.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))
    return 0 if verdict['all_pass_except_deferred'] else 1


if __name__ == '__main__':
    sys.exit(main())
