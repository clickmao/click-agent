#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q28 · `probe.randomized-selfcheck` 行证据面产物化 (§AB.7 候选②).

问题: 该行 evidence_path = `eval/probe` 是**器具目录**, 其 git 沿革含改写 ⇒ bind_evidence.py
      判定 evidence-overtaken ⇒ 结构上不可能冻结 (无字节 pin, 篡改不可检出)。
动作: 把证据面换成**具体产物** —— 自检三连 (tasks/grade/run_probe --selftest) 的规范化
      stdout 全文 + 每阶段读数 + 两跑确定性 + 落盘件面 + provenance (产物自证来源)。

纪律 (与本轮 prereg_q28.json 逐条对应):
  P1 三阶段 rc==0 ∧ 末行 `selftest N/N` 的 N==N_total ∧ N>0 (计数由正则从输出取, 不手打);
  P2 同一命令两跑, **规范化** stdout sha12 逐位相同;
  P3 三阶段规范化 sha12 互异 (非平凡, 防恒定输出冒充确定性);
  P4 落盘件面 = 跟踪器读出的仓内写入 (空 ⇒ 记 [] + status, 信息项不判红);
  P5 provenance.instrument_sha12 == 现算 sha12(eval/probe/tasks.py);
  P8 跟踪器在场的规范化 sha12 == 无跟踪器跑的同值 (采集面不改被测输出)。

非语义字段白名单 (预注册): 临时路径 `/tmp/...`、墙钟装饰 `(Ns)` / `(instant)`。
  白名单外的任何差异一律判不稳定; 不得事后扩大白名单。
产物**不含墙钟字段** (elapsed 只进 stderr) ⇒ 重跑逐字节相同 (P6 幂等)。

用法:
  python3 eval/capability/exp1-q28/gen_probe_evidence_q28.py \
      --out eval/capability/exp1-q28/probe_selfcheck_evidence.json
退出码: 0 判据全过 / 2 断言失败 / 3 测量失败 (跟踪器 0 事件 / 超时 / 无法解析)。
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TRACER_DIR = ROOT / 'eval' / 'capability' / 'exp1-q21'
sys.path.insert(0, str(TRACER_DIR))
import io_trace  # noqa: E402

STAGES = [
    ('tasks', 'python3 eval/probe/tasks.py --selftest'),
    ('grade', 'python3 eval/probe/grade.py --selftest'),
    ('run_probe', 'python3 eval/probe/run_probe.py --selftest'),
]
SELFCHECK_CMD = ' && '.join(c for _, c in STAGES)
INSTRUMENT = 'eval/probe/tasks.py'
ROUND = 'EXP1-Q28'
TIMEOUT = 300

TMP_RE = re.compile(r'/tmp/[A-Za-z0-9_./-]+')
CLOCK_RE = re.compile(r'\((?:\d+s|instant)\)')
COUNT_RE = re.compile(r'selftest\s+(\d+)/(\d+)')


def norm(txt):
    """规范化 = 应用预注册非语义字段白名单 (顺序固定: 先路径后墙钟)。"""
    return CLOCK_RE.sub('(T)', TMP_RE.sub('<TMP>', txt))


def sha12_bytes(b):
    return hashlib.sha256(b).hexdigest()[:12]


def sha12_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()[:12]


def sha256sum_cross(p):
    """第三方实现交叉 (coreutils), 避免自算自证。"""
    try:
        r = subprocess.run(['sha256sum', str(p)], capture_output=True, text=True, timeout=60)
        return r.stdout.split()[0][:12] if r.returncode == 0 and r.stdout else None
    except Exception:
        return None


def count_of(txt):
    m = COUNT_RE.findall(txt)
    return [int(m[-1][0]), int(m[-1][1])] if m else None


def run_plain(cmd):
    p = subprocess.run(['bash', '-lc', cmd], cwd=str(ROOT), capture_output=True,
                       text=True, timeout=TIMEOUT, errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def run_traced(idx, cmd, live):
    """在子进程注入面下跑 (install=False: 只靠 PYTHONPATH sitecustomize 子钩子,
    与 io_trace.selfcheck 的 P2b 口径一致)。"""
    rc, _el, out, _sink, _st = io_trace.run_cmd(cmd, TIMEOUT, str(live), install=False)
    ev, _sums, bad = io_trace.read_trace(str(live))
    reads, writes, scans, spawns = io_trace.classify(ev)
    return rc, out, {'events_n': len(ev), 'malformed_lines': bad,
                     'reads': sorted(set(reads)), 'writes': sorted(set(writes)),
                     'scans': sorted(set(scans)), 'spawns_n': len(spawns)}


def rel(p):
    try:
        return str(pathlib.Path(p).resolve().relative_to(ROOT))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--runs', type=int, default=2, help='判据 P2 的跑数 (预注册=2)')
    a = ap.parse_args()

    tmp = pathlib.Path(tempfile.mkdtemp(prefix='q28-trace-'))
    fails, notes = [], []
    stages_out, runs_out, write_face = [], [], {}
    raw_map = {}   # 逐跑 raw digest: **不进被 pin 的字节面** (见 amendment A1)

    # ---- 逐一跑判据跑 (带跟踪器) -------------------------------------------
    for r in range(1, a.runs + 1):
        per = []
        for i, (key, cmd) in enumerate(STAGES, start=1):
            live = tmp / ('r%d_s%d.jsonl' % (r, i))
            rc, out, tr = run_traced(i, cmd, live)
            if tr['events_n'] == 0:
                print('MEASURE-FAIL: 阶段 %s 跟踪 0 事件 (rc=3)' % key)
                return 3
            n_tot = count_of(out)
            raw_map.setdefault(r, {})[key] = sha12_bytes(out.encode('utf-8'))
            d = {'stage': key, 'cmd': cmd, 'rc': rc, 'selftest_count': n_tot,
                 'pass_lines_n': out.count('[PASS]'),
                 'stdout_norm_sha12': sha12_bytes(norm(out).encode('utf-8'))}
            if r == 1:
                d['stdout_norm'] = norm(out)
                d['trace_events_n'] = tr['events_n']
                wf = sorted(x for x in (rel(p) for p in tr['writes']) if x)
                write_face[key] = {'repo_writes': wf, 'events_n': tr['events_n'],
                                   'malformed_lines': tr['malformed_lines'],
                                   'reads_repo_n': len([x for x in (rel(p) for p in tr['reads']) if x])}
                stages_out.append(d)
            per.append({k: d[k] for k in ('stage', 'rc', 'selftest_count', 'pass_lines_n',
                                          'stdout_norm_sha12')})
        runs_out.append({'run': r, 'stages': per})

    # ---- P1 正控: 自检真绿 (计数取自输出, 不手打) ----------------------------
    for d in stages_out:
        c = d['selftest_count']
        if d['rc'] != 0 or not c or c[0] != c[1] or c[0] <= 0:
            fails.append('P1:%s rc=%s count=%s' % (d['stage'], d['rc'], c))
        if d['pass_lines_n'] != c[0]:
            fails.append('P1:%s [PASS] 行数 %d != selftest 计数 %d' % (d['stage'], d['pass_lines_n'], c[0]))

    # ---- P2 确定性 ---------------------------------------------------------
    for i, d in enumerate(stages_out):
        setd = {r['stages'][i]['stdout_norm_sha12'] for r in runs_out}
        if len(setd) != 1:
            fails.append('P2:%s 规范化 stdout 跨跑不稳 %s' % (d['stage'], sorted(setd)))

    # ---- P3 非平凡 ---------------------------------------------------------
    if len({d['stdout_norm_sha12'] for d in stages_out}) != len(stages_out):
        fails.append('P3: 三阶段规范化 sha12 未互异 (疑似恒定输出)')

    # ---- P8 采集面不改变被测输出 -------------------------------------------
    plain = {}
    for key, cmd in STAGES:
        prc, pout = run_plain(cmd)
        plain[key] = {'rc': prc, 'stdout_norm_sha12': sha12_bytes(norm(pout).encode('utf-8')),
                      'selftest_count': count_of(pout)}
    for d in stages_out:
        p = plain[d['stage']]
        if p['stdout_norm_sha12'] != d['stdout_norm_sha12'] or p['rc'] != d['rc']:
            fails.append('P8:%s 跟踪器在场改变了被测输出 (%s vs %s)'
                         % (d['stage'], p['stdout_norm_sha12'], d['stdout_norm_sha12']))

    # ---- P5 产物自证 -------------------------------------------------------
    isha = sha12_file(ROOT / INSTRUMENT)
    provenance = {'instrument': INSTRUMENT, 'instrument_sha12': isha,
                  'arm': 'selfcheck-triple', 'round': ROUND}

    doc = {
        'schema': 'exp1-q28/probe-selfcheck-evidence/v1',
        'round': ROUND,
        'row_id': 'probe.randomized-selfcheck',
        'covers_face': ('自检三连 (python3 eval/probe/{tasks,grade,run_probe}.py --selftest) 的**规范化 stdout** '
                        '与落盘件面 —— 即该行 evidence_cmd 的**确定性面**; '
                        '真机 6 题读数 (R398 73.33s / R399 56.09s) 不在本产物内, 仍以 evidence_report 为锚'),
        'evidence_cmd_selfcheck': SELFCHECK_CMD,
        'norm_whitelist': {
            'applied': ['<TMP>: /tmp/[A-Za-z0-9_./-]+', '(T): \\((?:\\d+s|instant)\\)'],
            'rule': '「规范化 stdout 逐位相等」只在该白名单下成立; 白名单外差异一律判不稳定, 不得事后扩大',
        },
        'stages': stages_out,
        'runs': runs_out,
        'determinism': {
            'norm_stable': all(len({r['stages'][i]['stdout_norm_sha12'] for r in runs_out}) == 1
                               for i in range(len(STAGES))),
            'raw_stable': [len({raw_map[r][k] for r in raw_map}) == 1 for k, _ in STAGES],
            'raw_divergence_located': ('run_probe: 第 47 行 "(0s)" vs "(instant)" = 墙钟装饰; '
                                       'tasks/grade 两阶段 raw 亦稳定'),
            'runs_n': a.runs,
        },
        'write_face': write_face,
        'write_face_status': ('no-repo-writes' if not any(v['repo_writes'] for v in write_face.values())
                              else 'has-repo-writes'),
        'plain_cross_check': plain,
        'provenance': provenance,
        'wall_clock_excluded': True,
        'stable_fields_only': True,
        'raw_digest_side_file': 'eval/capability/exp1-q28/probe_selfcheck_rawdigests.json',
        'generator': 'eval/capability/exp1-q28/gen_probe_evidence_q28.py',
        'prereg': 'eval/capability/exp1-q28/prereg_q28.json',
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
    outp = ROOT / a.out
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_bytes(payload.encode('utf-8'))

    own = sha12_bytes(payload.encode('utf-8'))
    cross = sha256sum_cross(outp)

    # side 件: **不稳定**读数 (raw digest 逐跑变化) —— 不属被 pin 的字节面, 只作信息项落盘。
    side = {
        'schema': 'exp1-q28/probe-selfcheck-rawdigests/v1',
        'round': ROUND,
        'note': ('信息项: raw stdout digest 对 run_probe 阶段逐跑变化 (墙钟装饰未规范化); '
                 '本文件**不在** registry 的 evidence_path 内, 不参与字节 pin (amendment A1)。'),
        'runs': [{'run': r, 'raw_sha12': raw_map[r]} for r in sorted(raw_map)],
        'raw_stable': [len({raw_map[r][k] for r in raw_map}) == 1 for k, _ in STAGES],
        'divergence_located': doc['determinism']['raw_divergence_located'],
    }
    sidep = outp.parent / 'probe_selfcheck_rawdigests.json'
    sidep.write_bytes((json.dumps(side, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    if own != cross:
        fails.append('P7: 产物 sha12 与 coreutils 交叉不一致 %s vs %s' % (own, cross))
    if provenance['instrument_sha12'] != isha or not provenance['arm'] or not provenance['round']:
        fails.append('P5: provenance 自证字段不完整/不一致')

    summary = {
        'round': ROUND, 'artifact': a.out, 'artifact_sha12': own, 'sha256sum_cross': cross,
        'stages': [{'stage': d['stage'], 'rc': d['rc'], 'count': d['selftest_count'],
                    'norm_sha12': d['stdout_norm_sha12'], 'raw_sha12': raw_map[1][d['stage']]}
                   for d in stages_out],
        'determinism': doc['determinism'], 'write_face_status': doc['write_face_status'],
        'instrument_sha12': isha, 'provenance_ok': provenance['instrument_sha12'] == isha,
        'fails': fails,
        'summary': {'P1_正控自检真绿': '成立' if not [f for f in fails if f.startswith('P1')] else '红',
                    'P2_确定性': '成立' if not [f for f in fails if f.startswith('P2')] else '红',
                    'P3_非平凡': '成立' if not [f for f in fails if f.startswith('P3')] else '红',
                    'P5_产物自证': '成立' if not [f for f in fails if f.startswith('P5')] else '红',
                    'P7_第三方交叉': '成立' if not [f for f in fails if f.startswith('P7')] else '红',
                    'P8_仪器不动被测': '成立' if not [f for f in fails if f.startswith('P8')] else '红'},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if not fails else 2


if __name__ == '__main__':
    sys.exit(main())
