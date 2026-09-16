#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q22 · 归因式副作用闸: 脏路径按「谁写的」归因 (不再是集合差)。

背景 (Q21 实测事故):
  旧闸 = `git status --porcelain -- eval docs` **前后集合差** (instruments_check.py L1 版)。
  * 无法区分「本面命令写的」与「并发写者写的」——对侧 R463 在飞的 4 个 tracked 文件被本闸判成
    「本面弄脏既有产物」⇒ 本侧据此误做 `git checkout` 复原, 抹掉对侧未提交改动 (不可从对象库恢复);
  * 对**已脏路径的重复写入**结构性不可见 (集合差为空 ⇒ 漏检)。

手段 (两条归属通道 + 一条内容通道):
  A 归属通道 (本侧, 完备): 每条本面命令经 `strace -f -y -e trace=<写类系统调用>` 跟踪 ——
    覆盖任意语言、全部后代进程 (不止 python); 本闸进程自身的写入再经 sys.addaudithook 采集。
  B 佐证通道 (对侧): /proc/*/fd 扫描持写句柄的**外部**进程 + 仓内 cwd 进程普查 (普查只作信息项)。
  C 内容通道: 窗内每个脏路径的 sha12 前后快照 —— 闭合「对已脏路径重复写入」盲区。

判据 (四类归属; 守恒: Σ 四类 == 窗末在册脏路径数 + 窗内被我方动过且已不脏的路径数):
  self_write    ∈ A                          ⇒ 判红 (证据: 命令序号/pid/系统调用)
  foreign_write ∉ A ∧ 窗内内容变化/新出现     ⇒ 单列, **不判红** (佐证: live_fd, 可为空=写者已关句柄)
  pre_existing  ∉ A ∧ 窗末仍脏 ∧ 内容未变     ⇒ 单列, 不判红
  unattributed  ∉ A ∧ 内容变化 ∧ 无法归因     ⇒ 判红 (fail-closed: 本闸只作备用通道, 见下)

测量失败 (verdict='measure-failed', 调用方按 rc=3 处置: 弃权, 既不算绿也不算红):
  跟踪通道不可用 / 物理上限截断 / 存在不可解析的相对名事件且仍有未归属脏路径。

口径边界 (诚实): A 通道覆盖**本面命令的进程树**; 若本闸自身 (父进程) 以非 python 方式写文件,
父通道看不到 —— 故父通道只作备用, 且父进程的写入面本身受 white_list 约束。
"""
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

TRACE_SYSCALLS = ('open,openat,openat2,creat,truncate,ftruncate,rename,renameat,renameat2,'
                  'unlink,unlinkat,mkdir,mkdirat,rmdir,symlink,symlinkat,link,linkat')
WRITE_FLAG_MARKERS = ('O_WRONLY', 'O_RDWR', 'O_CREAT', 'O_TRUNC', 'O_APPEND')
TRACE_LINE = re.compile(r'^(\d+)\s+([A-Za-z_][A-Za-z_0-9]*)\((.*)\)\s+=\s+(.*)$')
RET_PATH = re.compile(r'^\d+<(.*)>$')
ARG_FD_PATH = re.compile(r'\d+<(.*)>')
QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"')
LOG_SOFT_CAP = 64 * 1024 * 1024
LOG_HARD_CAP = 256 * 1024 * 1024
# EXP1-Q30 阈值重定 (数据先行; 原值 8MiB / 64MiB 是 **scoped 档**标定的):
#   · scoped 3 器具 / 6 命令实测 log_bytes = 17,943,199 (17.1MiB) ⇒ 旧 8MiB 上限**必然** capped ⇒ 弃权 (rc=3);
#   · 全量面 21 器具 / 47 命令实测 log_bytes = 29,715,862 (28.3MiB), 单条最大 8,476,012 (8.1MiB),
#     其余 44 条合计 <15MiB (体量由少数「多进程 + 大量文件打开」的命令主导)。
#   ⇒ 新阈值 = 全量面实测 × ~2.2 余量 (64MiB), 硬上限 256MiB 保留为**磁盘物理界**
#     (实测 /tmp 余量 14GiB; 越界仍判 `trace-capped` ⇒ 弃权 rc=3, 语义不变)。
# 重入标记: 已在外层闸窗口内的进程树不重复挂 strace —— 实测嵌套 strace 被内核拒绝
# (`PTRACE_TRACEME: Operation not permitted`), 会把内层命令整条判红 (假红)。
GATE_MARKER = 'Q22_SIDE_EFFECT_GATE'
MUTATE_SYSCALLS = ('truncate', 'ftruncate', 'rename', 'renameat', 'renameat2',
                   'unlink', 'unlinkat', 'mkdir', 'mkdirat', 'rmdir',
                   'symlink', 'symlinkat', 'link', 'linkat')
PARENT_WRITE_MODES = ('w', 'a', 'x', '+')
_PARENT_EVENTS = []
_PARENT_HOOK_INSTALLED = False


def _parent_hook(event, args):
    """本闸进程自身的写入 (备用通道; 只采集, 不做归属判定)。"""
    try:
        if event in ('open',):
            tgt = args[0]
            if isinstance(tgt, int):
                return
            mode = str(args[1])
            if not any(c in mode for c in PARENT_WRITE_MODES):
                return
            _PARENT_EVENTS.append({'ev': 'open', 'path': os.path.abspath(os.fspath(tgt)), 'mode': mode})
        elif event in ('os.rename', 'os.replace'):
            _PARENT_EVENTS.append({'ev': 'rename', 'path': os.path.abspath(os.fspath(args[0]))})
        elif event in ('os.remove', 'os.unlink'):
            _PARENT_EVENTS.append({'ev': 'remove', 'path': os.path.abspath(os.fspath(args[0]))})
    except Exception:
        return


def _install_parent_hook():
    global _PARENT_HOOK_INSTALLED
    if not _PARENT_HOOK_INSTALLED:
        sys.addaudithook(_parent_hook)
        _PARENT_HOOK_INSTALLED = True


def sha12_file(abs_path):
    try:
        return hashlib.sha256(pathlib.Path(abs_path).read_bytes()).hexdigest()[:12]
    except Exception:
        return None


def inherited_report(reason='outer-gate-active'):
    """嵌套调用 (外层闸已在跑) 时的占位报告: 归属由**外层**窗口负责 (外层 strace 覆盖整棵进程树),
    本层不重复挂闸、不判红 —— 实测嵌套 strace 被内核拒绝 (PTRACE_TRACEME: Operation not permitted),
    若强行嵌套, 内层命令会被判红 (假红), 破掉被包裹器具的正控。"""
    return {'schema': 'side-effect-attribution/1', 'verdict': 'inherited-outer-gate', 'red': False,
            'measurement_ok': True, 'reasons': [reason],
            'window': {'t0': None, 't1': None, 'trace_dir': None},
            'trace': {'commands': 0, 'events': 0, 'raw_events': 0, 'raw_paths_n': 0,
                      'raw_paths_sample': [], 'log_bytes': 0, 'capped': False,
                      'unresolved_relative': 0, 'channel': 'inherited'},
            'self_writes': [], 'touched_and_gone': [], 'foreign_writes': [], 'pre_existing': [],
            'old_gate_delta': [], 'old_gate_false_reds': [], 'old_gate_missed_self_writes': [],
            'live_fd_scan': {'scanned': 0, 'errors': 0}, 'census_in_repo_cwd': [],
            'conservation': {'classified': 0, 'expected': 0, 'in_scope_after': 0, 'ok': True}}


class SideEffectGate:
    """本面命令窗口内的脏路径归属器 (见模块 docstring)。"""

    def __init__(self, root, face_outputs=(), scratch=(), scope=('eval', 'docs'),
                 trace_dir=None, force_no_trace=False, git_bin='git'):
        self.root = pathlib.Path(root).resolve()
        self.face_outputs = {str(x).strip('/') for x in face_outputs}
        self.scratch = tuple(str(x) for x in scratch)
        self.scope = tuple(scope)
        self.trace_dir = pathlib.Path(trace_dir) if trace_dir else pathlib.Path(tempfile.mkdtemp(prefix='q22gate-'))
        self.force_no_trace = force_no_trace
        self.git_bin = git_bin
        self.cmds = 0
        self.logs = []
        self.parent_events = []
        self.trace_events = []
        self.raw_events = 0
        self.raw_paths = set()
        self.capped = False
        self.unresolved = 0
        self.unavailable = None
        self._before = set()
        self._before_sha = {}
        self._t0 = None

    # ---------- 窗口 ----------
    def begin(self):
        _install_parent_hook()
        _PARENT_EVENTS.clear()
        self._t0 = time.time()
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self._before = self.dirty_in_scope()
        self._before_sha = {p: self.sha(p) for p in self._before}
        if self.force_no_trace or shutil.which('strace') is None:
            self.unavailable = 'no-strace' if not self.force_no_trace else 'forced-no-trace'
        return self

    def wrap(self, cmd):
        """把 shell 命令包成 strace 跟踪形态 (逐条独立日志, 互不覆盖)。"""
        n = self.cmds + 1
        log = self.trace_dir / ('cmd%03d.log' % n)
        self.cmds = n
        self.logs.append((n, log, cmd))
        if self.unavailable:
            return ['bash', '-lc', cmd]
        return ['strace', '-f', '-qq', '-y', '-s', '200', '-o', str(log),
                '-e', 'trace=' + TRACE_SYSCALLS, '--', 'bash', '-lc', cmd]

    def run(self, cmd, timeout=900):
        env = dict(os.environ)
        env[GATE_MARKER] = '1'          # 后代进程据此避免重复挂闸 (嵌套 strace 不被内核允许)
        p = subprocess.run(self.wrap(cmd), cwd=str(self.root), env=env, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, (p.stdout or '') + (p.stderr or '')

    # ---------- 快照 ----------
    def dirty_paths(self):
        """脏路径集合。**逐文件** (-z + --untracked-files=all): 旧闸用默认未跟踪模式时
        git 会把整个未跟踪**目录**折叠成一条目录路径 ⇒ 路径级归属在原理上不可达。"""
        p = subprocess.run([self.git_bin, 'status', '--porcelain', '-z', '--untracked-files=all',
                            '--'] + list(self.scope),
                           cwd=str(self.root), capture_output=True, text=True)
        fields = (p.stdout or '').split('\0')
        out, i = set(), 0
        while i < len(fields):
            f = fields[i]
            if not f:
                i += 1
                continue
            xy, path = f[:2], f[3:]
            out.add(path)
            if 'R' in xy or 'C' in xy:               # 重命名/复制: 下一字段为原路径
                i += 1
                if i < len(fields) and fields[i]:
                    out.add(fields[i])
            i += 1
        return out

    def in_scope(self, rel):
        rel = str(rel).strip('/')
        if rel.startswith('../') or rel in ('..', ''):
            return False
        if not any(rel == s or rel.startswith(s + '/') for s in self.scope):
            return False
        if rel in self.face_outputs or rel.startswith(self.scratch):
            return False
        return True

    def dirty_in_scope(self):
        return {p for p in self.dirty_paths() if self.in_scope(p)}

    def sha(self, rel):
        return sha12_file(self.root / rel)

    # ---------- 归属通道 A: 子进程 (strace) ----------
    def _parse_log(self, idx, log):
        if not log.exists():
            return
        size = log.stat().st_size
        if size > LOG_SOFT_CAP:
            self.capped = True
        if size > LOG_HARD_CAP:
            self.capped = True
        with open(log, 'r', encoding='utf-8', errors='replace') as fh:
            for ln in fh:
                if self.capped:
                    break
                m = TRACE_LINE.match(ln.rstrip('\n'))
                if not m:
                    continue
                pid, sysc, args, ret = m.group(1), m.group(2), m.group(3), m.group(4)
                paths = self._paths_of(sysc, args, ret)
                for p, resolvable in paths:
                    if not resolvable or p is None:
                        self.unresolved += 1
                        continue
                    ap = pathlib.Path(os.path.realpath(p))
                    self.raw_events += 1
                    self.raw_paths.add(str(ap))
                    try:
                        rel = str(ap.relative_to(self.root.resolve()))
                    except ValueError:
                        continue                       # 仓外
                    if not self.in_scope(rel):
                        continue
                    self.trace_events.append({'cmd': idx, 'pid': pid, 'syscall': sysc,
                                              'path': rel, 'failed_ret': False})

    def _paths_of(self, sysc, args, ret):
        """返回 [(abs_path|None, resolvable_bool)]。写意图由 flags / 系统调用语义判定。
        失败的系统调用 (ret=-1) 不产生写入 ⇒ 一律不产生事件。"""
        out = []
        if ret.strip().startswith('-1'):
            return out
        if sysc in ('open', 'openat', 'openat2', 'creat'):
            if 'O_WRONLY' not in args and 'O_RDWR' not in args and 'O_CREAT' not in args \
                    and 'O_TRUNC' not in args and 'O_APPEND' not in args and sysc != 'creat':
                return out
            if ret.startswith('-1'):
                return out
            mret = RET_PATH.match(ret.strip())
            if mret:
                out.append((mret.group(1), True))
                return out
            qs = QUOTED.findall(args)
            if qs:
                cand = qs[-1]
                out.append((os.path.abspath(os.path.join(str(self.root), cand))
                            if not os.path.isabs(cand) else cand, True))
                return out
            fds = ARG_FD_PATH.findall(args)
            if fds:
                out.append((fds[-1], True))
            else:
                out.append((None, False))
            return out
        if sysc in MUTATE_SYSCALLS:
            if 'truncate' in sysc:
                fds = ARG_FD_PATH.findall(args)
                if fds:
                    out.append((fds[0], True))
                else:
                    qs = QUOTED.findall(args)
                    out.append(((qs[0] if qs else None), bool(qs)))
                return out
            qs = QUOTED.findall(args)
            if not qs:
                out.append((None, False))
                return out
            for cand in qs:
                out.append((os.path.abspath(os.path.join(str(self.root), cand))
                            if not os.path.isabs(cand) else cand, True))
            return out
        return out

    def _parse_parent(self):
        for e in _PARENT_EVENTS:
            try:
                ap = pathlib.Path(os.path.realpath(e['path']))
                rel = str(ap.relative_to(self.root.resolve()))
            except Exception:
                continue
            if self.in_scope(rel):
                self.trace_events.append({'cmd': 0, 'pid': str(os.getpid()), 'syscall': 'audit:' + e['ev'],
                                          'path': rel, 'failed_ret': False})

    # ---------- 佐证通道 B ----------
    def tree_pids(self):
        return {str(os.getpid())} | {e['pid'] for e in self.trace_events}

    def live_writers(self, rel_paths):
        target = {os.path.realpath(str(self.root / p)) for p in rel_paths}
        mine = self.tree_pids()
        ev, scanned, errors = [], 0, 0
        try:
            pids = [d for d in os.listdir('/proc') if d.isdigit()]
        except Exception:
            return {'evidence': [], 'scanned': 0, 'errors': 1}
        for d in pids:
            if d in mine:
                continue
            fddir = '/proc/%s/fd' % d
            try:
                fds = os.listdir(fddir)
            except Exception:
                errors += 1
                continue
            for fd in fds:
                scanned += 1
                try:
                    tp = os.readlink(os.path.join(fddir, fd))
                    acc = None
                    with open('/proc/%s/fdinfo/%s' % (d, fd), 'r') as fh:
                        for ln in fh:
                            if ln.startswith('flags:'):
                                acc = int(ln.split()[1], 8) & 3
                                break
                except Exception:
                    continue
                if acc not in (1, 2):
                    continue
                if os.path.realpath(tp) in target:
                    ev.append({'pid': int(d), 'fd': fd, 'accmode': acc,
                               'path': str(tp), 'cmd': self._cmdline(int(d))})
        return {'evidence': ev, 'scanned': scanned, 'errors': errors}

    def _cmdline(self, pid):
        try:
            with open('/proc/%d/cmdline' % pid, 'rb') as fh:
                return fh.read(160).decode('utf-8', 'replace').replace('\x00', ' ').strip()
        except Exception:
            return ''

    def census(self):
        """仓内 cwd 的存活进程 (信息项: 提示并发写者存在, 不作归属判据)。"""
        mine = self.tree_pids()
        out = []
        try:
            pids = [d for d in os.listdir('/proc') if d.isdigit()]
        except Exception:
            return out
        for d in pids:
            if d in mine or d == '1':
                continue
            try:
                cwd = os.readlink('/proc/%s/cwd' % d)
            except Exception:
                continue
            try:
                inside = str(pathlib.Path(os.path.realpath(cwd)).relative_to(self.root.resolve()))
            except Exception:
                continue
            out.append({'pid': int(d), 'cwd': inside, 'cmd': self._cmdline(int(d))})
        return out

    # ---------- 收口 ----------
    def end(self):
        self._parse_parent()
        for idx, log, _cmd in self.logs:
            self._parse_log(idx, log)
        after = self.dirty_in_scope()
        after_sha = {p: self.sha(p) for p in after}
        self_paths = {}
        for e in self.trace_events:
            if not e['failed_ret']:
                self_paths.setdefault(e['path'], e)
        res = {'self_writes': [], 'foreign_writes': [], 'pre_existing': [], 'touched_and_gone': []}
        for p in sorted(after):
            changed = (p not in self._before) or (self._before_sha.get(p) != after_sha.get(p))
            if p in self_paths:
                res['self_writes'].append({'path': p, 'evidence': self_paths[p],
                                           'sha_before': self._before_sha.get(p),
                                           'sha_after': after_sha.get(p)})
            elif changed:
                res['foreign_writes'].append({'path': p, 'sha_before': self._before_sha.get(p),
                                              'sha_after': after_sha.get(p), 'note': 'changed-in-window'})
            else:
                res['pre_existing'].append(p)
        for p in sorted(self._before - after):
            if p in self_paths:
                res['touched_and_gone'].append({'path': p, 'evidence': self_paths[p]})
        live = self.live_writers([w['path'] for w in res['foreign_writes']])
        for w in res['foreign_writes']:
            w['live_fd'] = [e for e in live['evidence'] if os.path.realpath(e['path']) ==
                            os.path.realpath(str(self.root / w['path']))]
        old_delta = sorted(after - self._before)
        self_written_paths = {w['path'] for w in res['self_writes']} | {w['path'] for w in res['touched_and_gone']}
        measurement_ok = True
        reasons = []
        if self.unavailable:
            measurement_ok = False
            reasons.append('trace-channel-unavailable:%s' % self.unavailable)
        if self.capped:
            measurement_ok = False
            reasons.append('trace-capped')
        if self.unresolved and res['foreign_writes']:
            measurement_ok = False
            reasons.append('unresolved-relative-events=%d' % self.unresolved)
        classified = (len(res['self_writes']) + len(res['foreign_writes'])
                      + len(res['pre_existing']) + len(res['touched_and_gone']))
        expected = len(after) + len(res['touched_and_gone'])
        conservation_ok = classified == expected
        if not conservation_ok:
            measurement_ok = False
            reasons.append('conservation-broken:%d!=%d' % (classified, expected))
        red = bool(res['self_writes'] or res['touched_and_gone'])
        verdict = 'measure-failed' if not measurement_ok else ('self-side-effect' if red else 'clean')
        return {
            'schema': 'side-effect-attribution/1',
            'verdict': verdict, 'red': red, 'measurement_ok': measurement_ok, 'reasons': reasons,
            'window': {'t0': self._t0, 't1': time.time(), 'trace_dir': str(self.trace_dir)},
            'trace': {'commands': self.cmds, 'events': len(self.trace_events),
                      'raw_events': self.raw_events, 'raw_paths_n': len(self.raw_paths),
                      'raw_paths_sample': sorted(self.raw_paths)[:200],
                      'log_bytes': sum(l.stat().st_size for _, l, _ in self.logs if l.exists()),
                      'capped': self.capped, 'unresolved_relative': self.unresolved,
                      'channel': 'none' if self.unavailable else 'strace+audithook'},
            'self_writes': res['self_writes'],
            'touched_and_gone': res['touched_and_gone'],
            'foreign_writes': res['foreign_writes'],
            'pre_existing': res['pre_existing'],
            'old_gate_delta': old_delta,
            'old_gate_false_reds': [p for p in old_delta if p not in self_written_paths],
            'old_gate_missed_self_writes': sorted(p for p in self_written_paths if p not in old_delta),
            'live_fd_scan': {'scanned': live['scanned'], 'errors': live['errors']},
            'census_in_repo_cwd': self.census(),
            'conservation': {'classified': classified, 'expected': expected, 'in_scope_after': len(after),
                             'ok': conservation_ok},
        }
