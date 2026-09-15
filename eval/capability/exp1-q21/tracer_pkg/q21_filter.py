# -*- coding: utf-8 -*-
"""EXP1-Q21 · 跟踪过滤与上限 (父钩子与子注入共用; 只用标准库).

事故记录 (本轮实测): 无过滤无上限的跟踪器在 5 分钟内对 9 条命令写出 **2.1 GB** 跟踪文件
(每条 ~250 MB) —— 因为解释器启动的每一次 import 都产生 open 事件。物理上限是必需品, 不是优化。

规则: 只写「仓内、非运行时、非台账、非版本库内部」的路径事件; 其余按类**只计数 + 少量样例**;
      超过 MAX_EVENTS / MAX_BYTES 即停写并置 capped (如实可见, 不静默丢弃)。
"""
import os
import sys

ROOT = os.path.abspath(os.environ.get('Q21_ROOT') or os.getcwd())
LEDGER = ('docs/verification-registry.json',
          'eval/capability/instruments.json',
          'eval/capability/kpi.jsonl')
RUNTIME_PREFIXES = tuple(sorted({
    p for p in (sys.prefix, sys.base_prefix, os.path.dirname(os.__file__)) if p
})) + ('/usr/lib/python', '/usr/local/lib/python')
MAX_EVENTS = int(os.environ.get('Q21_TRACE_MAX_EVENTS') or 4000)
MAX_BYTES = int(os.environ.get('Q21_TRACE_MAX_BYTES') or 2 * 1024 * 1024)
EXAMPLES_PER_CAT = 8


def resolve_path(name, dir_fd):
    """把审计事件的 (name, dir_fd) 解成绝对路径。返回 (abs_path|None, 'ok'|'unresolved')。

    实测 (本轮两处缺陷的直接来源): 递归删除类实现会以「相对名 + dir_fd」发起事件, 甚至
    `os.open(name, ..., dir_fd=fd)` 形态 (该事件的审计形参**不含** dir_fd)。
      * dir_fd 为真实 fd ⇒ 经 /proc/self/fd 解析 (不可解析则记 unresolved, 不猜);
      * dir_fd 为 -1 (AT_FDCWD) 或绝对路径 ⇒ 按进程 cwd 解析 (正当);
      * 裸相对名且无 dir_fd ⇒ **不可解析**: 若按 cwd 猜, 会把夹具文件错报成 cwd 下同名文件。
    """
    nm = os.fsdecode(name) if isinstance(name, bytes) else os.fspath(name)
    if not isinstance(nm, str) or not nm:
        return None, 'unresolved'
    if dir_fd is not None and int(dir_fd) >= 0:
        try:
            base = os.readlink('/proc/self/fd/%d' % int(dir_fd))
            return os.path.normpath(os.path.join(base, nm)), 'ok'
        except Exception:
            return None, 'unresolved'
    if os.path.isabs(nm):
        return os.path.normpath(nm), 'ok'
    if os.sep in nm:
        return os.path.abspath(nm), 'ok'
    return None, 'unresolved'


def bucket(path):
    """返回 (类别, 标签, 'event'|'excluded')。类别即报告口径, 不猜测。"""
    ap = os.path.abspath(path)
    try:
        rel = os.path.relpath(ap, ROOT)
    except Exception:
        rel = None
    if rel is None or rel.startswith('..'):
        return 'outside', ap, 'excluded'
    rel = rel.replace(os.sep, '/')
    if rel.startswith('.git/'):
        return 'git', rel, 'excluded'
    if rel in LEDGER:
        return 'ledger', rel, 'excluded'
    if '__pycache__' in rel or rel.endswith('.pyc'):
        return 'pycache', rel, 'excluded'
    if ap.startswith(RUNTIME_PREFIXES):
        return 'runtime', rel, 'excluded'
    if rel.startswith('eval/capability/exp1-q21/'):
        return 'tracer', rel, 'excluded'
    return 'event', rel, 'event'
