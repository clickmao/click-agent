# -*- coding: utf-8 -*-
"""EXP1-Q21 · 子进程跟踪注入点 (经 PYTHONPATH 自动 import).

只用标准库; 父进程未设 Q21_TRACE_FILE 时空转 (对一般 python 进程零副作用)。
有界: 只写过滤后的仓内事件; 超出上限置 capped 并停写; 退出时落 summary (计数 + 样例)。
"""
import json
import os
import sys

_P = os.environ.get('Q21_TRACE_FILE')
if _P and not os.environ.get('Q21_SITE_DONE'):
    os.environ['Q21_SITE_DONE'] = '1'
    os.environ.setdefault('Q21_ROOT', os.getcwd())
    try:
        import q21_filter as _f
    except Exception:
        _f = None
    if _f is not None:
        import atexit
        _EV = ('open', 'os.scandir', 'os.mkdir', 'os.rename', 'os.remove', 'os.rmdir',
               'subprocess.Popen', 'os.system')
        _DUMPS = json.dumps
        _st = {'fd': None, 'writing': False, 'n': 0, 'bytes': 0, 'capped': False,
               'counters': {}, 'examples': {}}

        def _emit(ent):
            if _st['fd'] is None or _st['capped']:
                return
            b = (_DUMPS(ent, ensure_ascii=False) + '\n').encode('utf-8')
            if _st['n'] >= _f.MAX_EVENTS or _st['bytes'] + len(b) > _f.MAX_BYTES:
                _st['capped'] = True
                try:
                    os.write(_st['fd'], _DUMPS({'ev': 'capped', 'events_written': _st['n']}).encode() + b'\n')
                except Exception:
                    pass
                return
            _st['writing'] = True
            try:
                os.write(_st['fd'], b)                 # 单次 append 写: 原子且无缓冲
                _st['n'] += 1
                _st['bytes'] += len(b)
            except Exception:
                pass
            finally:
                _st['writing'] = False

        def _hook(event, args):
            if _st['writing'] or event not in _EV:
                return
            try:
                if event == 'open':
                    p = args[0]
                    if isinstance(p, int):
                        return
                    tgt = os.fspath(p) if not isinstance(p, str) else p
                    mode = str(args[1])
                    tgt, _stt = _f.resolve_path(tgt, None)
                    if _stt != 'ok':
                        _st['counters']['unresolved_relative'] = _st['counters'].get('unresolved_relative', 0) + 1
                        return
                elif event in ('os.scandir', 'os.mkdir', 'os.rmdir', 'os.remove', 'os.rename'):
                    if event == 'os.mkdir':
                        dfd = args[2] if len(args) > 2 else None
                    elif event == 'os.rename':
                        dfd = args[2] if len(args) > 2 else None
                    else:
                        dfd = args[1] if len(args) > 1 else None
                    tgt, _stt = _f.resolve_path(args[0], dfd)
                    if _stt != 'ok':
                        _st['counters']['unresolved_relative'] = _st['counters'].get('unresolved_relative', 0) + 1
                        return
                    mode = ''
                else:
                    _emit({'ev': 'spawn', 'args': [str(a)[:300] for a in args]})
                    return
                cat, label, kind = _f.bucket(tgt)
                if kind == 'event':
                    ent = {'ev': {'os.scandir': 'scandir', 'os.mkdir': 'mkdir', 'os.rmdir': 'rmdir',
                                  'os.remove': 'remove', 'os.rename': 'rename'}.get(event, event),
                           'path': tgt}
                    if event == 'open':
                        ent['mode'] = mode
                    if event == 'os.rename':
                        dst, _dstt = _f.resolve_path(args[1], args[3] if len(args) > 3 else None)
                        ent['dst'] = dst if _dstt == 'ok' else '<unresolved>'
                    _emit(ent)
                else:
                    _st['counters'][cat] = _st['counters'].get(cat, 0) + 1
                    ex = _st['examples'].setdefault(cat, [])
                    if len(ex) < _f.EXAMPLES_PER_CAT and label not in ex:
                        ex.append(label)
            except Exception:
                return

        def _finish():
            try:
                if _st['fd'] is None:
                    return
                _st['writing'] = True
                sumrec = {'ev': 'summary', 'pid': os.getpid(), 'events_written': _st['n'],
                          'capped': _st['capped'], 'excluded_counters': _st['counters'],
                          'excluded_examples': _st['examples'], 'root': _f.ROOT}
                os.write(_st['fd'], _DUMPS(sumrec, ensure_ascii=False).encode() + b'\n')
                os.close(_st['fd'])
                _st['fd'] = None
            except Exception:
                return

        try:
            _st['fd'] = os.open(_P, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        except Exception:
            _st['fd'] = None
        if _st['fd'] is not None:
            atexit.register(_finish)
            sys.addaudithook(_hook)
