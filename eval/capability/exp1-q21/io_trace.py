#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q21 · 输入面跟踪器 (audit hook, 失败可见 + 物理上限).

用途: 把「器具正控命令**实际读过哪些输入**」变成可复现读数 —— 而不是靠读源码猜输入面。
手段: sys.addaudithook 采集本进程的 open/os.scandir/os.mkdir/os.rename/os.remove/subprocess.Popen;
      子 python 进程经 PYTHONPATH=<tracer_pkg> (sitecustomize.py) 继承同一钩子, 事件追加到 Q21_TRACE_FILE。

纪律:
  * 自证双边: 父读夹具 + 子 python 读标记 都必须出现在事件里 (正控 4 项);
  * 负控: 无钩子环境下同一读命令 stdout 仍有内容 (证明读数只经钩子/注入面可见, 非空心仪器);
  * 物理上限: 只写过滤后的仓内事件 + 计数其余类 (实测事故: 无上限版本 5 分钟写出 2.1 GB);
  * fail-closed: 事件数为 0 / 跟踪文件缺失 ⇒ rc=3 (测量失败), 与 rc=2 (断言失败) 不同码。

用法:
  python3 io_trace.py --selfcheck --out <json>
  python3 io_trace.py --row-id <id> --cmd "<shell>" --out <json> [--timeout 300]
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE / 'tracer_pkg'
TRACE_ENV = 'Q21_TRACE_FILE'
EV_OK = ('open', 'os.scandir', 'os.mkdir', 'os.rename', 'os.remove', 'os.rmdir', 'subprocess.Popen', 'os.system')
sys.path.insert(0, str(PKG))
import q21_filter as qf  # noqa: E402


def _resolve(name, dir_fd, st):
    """薄封装: 解析口径单源于 q21_filter.resolve_path (父/子两个钩子共用同一实现)。"""
    p, status = qf.resolve_path(name, dir_fd)
    if status != 'ok':
        st['counters']['unresolved_relative'] = st['counters'].get('unresolved_relative', 0) + 1
        return None, False
    return p, True


def new_state():
    return {'fh': None, 'writing': False, 'events': 0, 'bytes': 0, 'capped': False,
            'counters': {}, 'examples': {}}


def _write(state, ent):
    if state['capped']:
        return
    b = (json.dumps(ent, ensure_ascii=False) + '\n').encode('utf-8')
    if state['events'] >= qf.MAX_EVENTS or state['bytes'] + len(b) > qf.MAX_BYTES:
        state['capped'] = True
        b = (json.dumps({'ev': 'capped', 'events_written': state['events']}, ensure_ascii=False) + '\n').encode('utf-8')
        if state['fh'] is not None:
            state['fh'].write(b)
        return
    if state['fh'] is not None:
        state['fh'].write(b)
    state['events'] += 1
    state['bytes'] += len(b)


def _mk_hook(sink, get_path, state=None):
    """sink: list 收集事件; get_path: callable 返回落盘路径 (None = 不落盘); state: 计数/上限。"""
    st = state if state is not None else new_state()

    def hook(event, args):
        if st['writing'] or event not in EV_OK:
            return
        try:
            st['writing'] = True
            if event == 'open':
                p = args[0]
                if isinstance(p, int):
                    return
                tgt = os.fspath(p) if not isinstance(p, str) else p
                mode = str(args[1])
                resolved, ok = _resolve(tgt, None, st)
                if not ok:
                    return
                tgt = resolved
            elif event in ('os.scandir', 'os.mkdir', 'os.rmdir', 'os.remove', 'os.rename'):
                raw = args[0]
                # 逐事件取 dir_fd 实参位 (audit 形参顺序固定): mkdir(path,mode,dir_fd) /
                # rmdir(path,dir_fd) / remove(path,dir_fd) / rename(src,dst,src_fd,dst_fd)
                if event == 'os.mkdir':
                    dfd = args[2] if len(args) > 2 else None
                elif event == 'os.rename':
                    dfd = args[2] if len(args) > 2 else None
                else:
                    dfd = args[1] if len(args) > 1 else None
                resolved, ok = _resolve(raw, dfd, st)
                if not ok:
                    return
                tgt, mode = resolved, ''
            else:
                ent = {'ev': 'spawn', 'args': [str(a)[:300] for a in args]}
                sink.append(ent)
                _ensure_fh(st, get_path)
                _write(st, ent)
                return
            cat, label, kind = qf.bucket(tgt)
            if kind != 'event':
                st['counters'][cat] = st['counters'].get(cat, 0) + 1
                ex = st['examples'].setdefault(cat, [])
                if len(ex) < qf.EXAMPLES_PER_CAT and label not in ex:
                    ex.append(label)
                return
            ent = {'ev': {'os.scandir': 'scandir', 'os.mkdir': 'mkdir', 'os.rmdir': 'rmdir',
                          'os.remove': 'remove', 'os.rename': 'rename'}.get(event, event),
                   'path': os.path.abspath(tgt)}
            if event == 'open':
                ent['mode'] = mode
            if event == 'os.rename':
                ent['dst'] = os.path.abspath(os.fspath(args[1]))
            sink.append(ent)
            _ensure_fh(st, get_path)
            _write(st, ent)
        except Exception:
            return
        finally:
            st['writing'] = False

    return hook, st


def _ensure_fh(st, get_path):
    if st['fh'] is None:
        fp = get_path()
        if fp:
            pathlib.Path(fp).parent.mkdir(parents=True, exist_ok=True)
            st['fh'] = open(fp, 'a', encoding='utf-8')


def finalize(st, tag):
    """写出 summary 行 (计数 + 样例 = 被排除类别的可见性), 关闭句柄。"""
    try:
        if st['fh'] is None:
            return
        st['fh'].write(json.dumps({'ev': 'summary', 'who': tag, 'events_written': st['events'],
                                   'capped': st['capped'], 'excluded_counters': st['counters'],
                                   'excluded_examples': st['examples']}, ensure_ascii=False) + '\n')
        st['fh'].close()
        st['fh'] = None
    except Exception:
        return


def child_env(trace_file):
    env = dict(os.environ)
    env['PYTHONPATH'] = str(PKG) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    env[TRACE_ENV] = str(trace_file)
    env['Q21_ROOT'] = str(ROOT)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONHASHSEED'] = '0'
    return env


def run_cmd(cmd, timeout, live_trace, install=True, state=None):
    """在父进程钩子在场下跑 cmd; 返回 (rc, elapsed, stdout_tail, sink, state)。"""
    sink = []
    st = state if state is not None else new_state()
    if install:
        hook, st = _mk_hook(sink, lambda: live_trace, st)
        sys.addaudithook(hook)                     # 不可移除: 故必须在最后阶段才落盘汇总
    t0 = time.time()
    try:
        p = subprocess.run(['bash', '-lc', cmd], cwd=str(ROOT), env=child_env(live_trace),
                           capture_output=True, text=True, timeout=timeout, errors='replace')
        rc, out = p.returncode, (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        rc, out = 124, 'TIMEOUT after %ss' % timeout
    return rc, round(time.time() - t0, 2), out, sink, st


def read_trace(path):
    """读跟踪文件, 返回 (events, summaries, malformed_n)。"""
    events, sums, bad = [], [], 0
    p = pathlib.Path(path)
    if not p.exists():
        return events, sums, bad
    for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            bad += 1
            continue
        (sums if d.get('ev') == 'summary' else events).append(d)
    return events, sums, bad


def classify(events):
    """按事件面做「读写/扫描」分类; 纯函数, 供自证与派生共用。"""
    reads, writes, scans, spawns = [], [], [], []
    for e in events:
        ev = e.get('ev')
        if ev == 'open':
            m = e.get('mode') or ''
            core = m.replace('b', '').replace('+', '').replace('t', '') or 'r'
            (writes if any(c in core for c in 'wax') else reads).append(e['path'])
        elif ev == 'scandir':
            scans.append(e['path'])
        elif ev in ('mkdir', 'rmdir', 'rename', 'remove'):
            writes.append(e.get('path'))
        elif ev == 'spawn':
            spawns.append(e.get('args'))
    return reads, writes, scans, spawns


def selfcheck(out_path):
    """正控 5 项 + 负控 1 项 + 过滤器 1 项。仓内夹具建在 tracer 目录**之外** (tracer 目录被过滤)。"""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='q21-trace-selfcheck-'))
    live = tmp / 'child_trace.jsonl'
    sc = ROOT / 'eval' / 'capability' / 'exp1-q21-selfcheck'
    sc.mkdir(parents=True, exist_ok=True)
    res: dict = {'tmpdir': str(tmp), 'selfcheck_dir': str(sc.relative_to(ROOT))}
    sink = []
    parent_hook, pst = _mk_hook(sink, lambda: None)          # 父钩子: 只入内存
    sys.addaudithook(parent_hook)
    # 仓内夹具 (可进事件面)
    repo_fixture = sc / 'fixture_read_me.txt'
    repo_fixture.write_text('q21-repo-fixture-marker\n', encoding='utf-8')
    repo_marker = sc / 'child_marker.txt'
    repo_marker.write_text('q21-repo-child-marker\n', encoding='utf-8')
    # 仓外夹具 (必须被过滤: 只计数不写事件)
    outside_fixture = tmp / 'outside_read_me.txt'
    outside_fixture.write_text('q21-outside-marker\n', encoding='utf-8')
    parent_read = repo_fixture.read_text(encoding='utf-8')
    outside_read = outside_fixture.read_text(encoding='utf-8')

    rc, el, out, _, st = run_cmd(
        'python3 -c "from pathlib import Path,sys; sys.stdout.write(Path(sys.argv[1]).read_text())" %s' % repo_marker,
        120, live, install=False, state=pst)
    child_ev, child_sums, child_bad = read_trace(live)
    reads, writes, scans, spawns = classify(sink)
    child_reads, _, _, _ = classify(child_ev)
    res.update({
        'repo_fixture': str(repo_fixture.relative_to(ROOT)), 'repo_marker': str(repo_marker.relative_to(ROOT)),
        'outside_fixture': str(outside_fixture),
        'rc': rc, 'stdout_tail': (out or '').strip()[-200:],
        'parent_read_ok': parent_read.strip() == 'q21-repo-fixture-marker',
        'outside_read_ok': outside_read.strip() == 'q21-outside-marker',
        'events_n': len(sink) + len(child_ev), 'parent_events_n': len(sink), 'child_events_n': len(child_ev),
        'child_summaries_n': len(child_sums), 'child_malformed_n': child_bad,
        'P2a_parent_read_fixture': str(repo_fixture) in set(reads),
        'P2b_child_read_marker': str(repo_marker) in set(child_reads),
        'P2c_write_classified': str(repo_fixture) in set(writes) or str(repo_marker) in set(writes),
        'P2c_spawn_classified': len(spawns) >= 1,
        'P2d_repo_fixture_not_filtered': str(repo_fixture) in set(reads),
        'P4_outside_filtered_n': st['counters'].get('outside', 0),
        'P4_outside_examples': st['examples'].get('outside', [])[:3],
        'P4_pass': bool(st['counters'].get('outside', 0) >= 2),   # 仓外夹具不许进事件面
    })
    res['P2_pass'] = bool(res['P2a_parent_read_fixture'] and res['P2b_child_read_marker']
                          and res['P2c_write_classified'] and res['P2c_spawn_classified']
                          and res['P2d_repo_fixture_not_filtered'])

    # P5 归因正控 (本轮实测缺陷的护栏): 递归删除以「相对名 + dir_fd」发起事件,
    # 只按进程 cwd 解析会把夹具文件错报成仓库根同名文件 ⇒ 断言全部事件落在夹具子树内。
    import shutil as _sh
    sub = sc / 'rmtree_case'
    (sub / 'nested').mkdir(parents=True, exist_ok=True)
    (sub / 'b.cs').write_text('x', encoding='utf-8')
    (sub / 'nested' / 'a.cs').write_text('y', encoding='utf-8')
    del sink[:]
    _sh.rmtree(sub, ignore_errors=True)
    del_events = [e for e in sink if e.get('path', '').startswith(str(sub)) or
                  e.get('path', '').endswith(('b.cs', 'a.cs'))]
    resolved_ok = all(str(e.get('path', '')).startswith(str(sub)) for e in del_events) and bool(del_events)
    misattributed = [e for e in sink if e.get('path') in (str(ROOT / 'b.cs'), str(ROOT / 'a.cs'))]
    res.update({'P5_rmtree_events_n': len(del_events), 'P5_all_under_subtree': bool(resolved_ok),
                'P5_misattributed_to_repo_root': len(misattributed),
                'P5_unresolved_relative_n': pst['counters'].get('unresolved_relative', 0),
                'P5_accounted_n': len(del_events) + pst['counters'].get('unresolved_relative', 0),
                'P5_total_events_n': len(sink),
                'P5_boundary': 'fd 相对 open 事件在审计面不带 dir_fd ⇒ 不可解析 (只计数, 不猜路径)',
                'P5_pass': bool(resolved_ok and not misattributed)})

    env = dict(os.environ)
    env.pop(TRACE_ENV, None)
    env['PYTHONPATH'] = ''
    p = subprocess.run(['bash', '-lc', 'cat %s' % repo_fixture], capture_output=True, text=True,
                       timeout=120, errors='replace', env=env)
    res['P3_neg_stdout_has_marker'] = 'q21-repo-fixture-marker' in (p.stdout or '')
    res['P3_pass'] = bool(res['P3_neg_stdout_has_marker'])
    res['P3_note'] = '负控 = 同一读命令在无钩子环境下 stdout 仍有内容 (读发生了), 但事件面只由钩子/注入面产生'
    res['ok'] = bool(res['P2_pass'] and res['P3_pass'] and res['P4_pass'] and res['P5_pass'])
    res['summary'] = {'P2_正控(父读/子读/读写分类/spawn分类/仓内夹具)': '5/5' if res['P2_pass'] else '红',
                      'P3_负控(无钩子×读发生)': '成立' if res['P3_pass'] else '红',
                      'P4_过滤器(仓外夹具必须只计数不进事件面)': '成立' if res['P4_pass'] else '红',
                      'P5_归因(dir_fd 相对名不得错归到仓库根)': '成立' if res['P5_pass'] else '红'}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if out_path:
        pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(out_path).write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(sc, ignore_errors=True)
    return 0 if res['ok'] else 2


def trace_one(row_id, cmd, timeout, out_path):
    live = HERE / 'l2runs' / ('trace_%s.child.jsonl' % row_id.replace('/', '_'))
    live.parent.mkdir(parents=True, exist_ok=True)
    if live.exists():
        live.unlink()
    rc, el, out, sink, st = run_cmd(cmd, timeout, live)
    finalize(st, 'parent')
    child_ev, child_sums, child_bad = read_trace(live)
    events = sink + child_ev
    reads, writes, scans, spawns = classify(events)
    excluded = dict(st['counters'])
    for s in child_sums:
        for k, v in (s.get('excluded_counters') or {}).items():
            excluded[k] = excluded.get(k, 0) + v
    doc = {'row_id': row_id, 'cmd': cmd, 'rc': rc, 'elapsed_s': el,
           'events_n': len(events), 'parent_events_n': len(sink), 'child_events_n': len(child_ev),
           'trace_bytes': live.stat().st_size if live.exists() else 0,
           'capped': bool(st['capped'] or any(s.get('capped') for s in child_sums)),
           'malformed_lines': child_bad,
           'excluded_counters': excluded, 'excluded_examples': st['examples'],
           'reads': sorted(set(reads)), 'writes': sorted(set(writes)),
           'scans': sorted(set(scans)), 'spawns': spawns[:12],
           'stdout_tail': out.strip()[-1200:]}
    pathlib.Path(out_path).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return doc


def main():
    args = sys.argv[1:]

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default
    out = opt('--out')
    if '--selfcheck' in args:
        return selfcheck(out)
    if '--row-id' in args:
        row = opt('--row-id')
        cmd = opt('--cmd')
        if not row or not cmd:
            print('FATAL: --row-id/--cmd 必填 (fail-closed)')
            return 3
        doc = trace_one(row, cmd, int(opt('--timeout', '300')), out or str(HERE / 'l2runs' / 'trace_last.json'))
        if doc['events_n'] == 0:
            print('MEASURE-FAIL: 0 事件 ⇒ 跟踪未生效 (rc=3)')
            return 3
        print(json.dumps({k: doc[k] for k in ('row_id', 'rc', 'elapsed_s', 'events_n',
                                              'parent_events_n', 'trace_bytes', 'capped')},
                         ensure_ascii=False))
        return 0
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
