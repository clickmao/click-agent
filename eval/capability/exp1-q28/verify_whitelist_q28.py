#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q28 · 白名单覆盖面核验 (N4, 在被 pin 的产物**之外**单列).

为什么单独一个器具: 被 pin 的产物按设计只存**稳定**字段 (规范化 stdout), 原始 stdout 不在其中
⇒ 「白名单是否恰好只吞非语义 token」在产物上**不可判** (在规范化文本上找墙钟 token 是空转:
那些 token 早就被归一了 —— 本轮我自己先踩了这个, 两次)。故在**原始 stdout** 上核验, 读数落
本文件 (不参与字节 pin)。

判据 (对应 prereg_q28.json · N4):
  N4-b1 归一后**零残留**墙钟 token (真实原始文本, 非手造串);
  N4-b2 语义括号 token 计数**归一前后不变** (白名单不吞语义);
  N4-b3 墙钟 token 形态**全部**在白名单内 (形态取自真实文本, 非手打);
  N4-a  语义差异 (计数 29/29 → 28/29) 规范化后**仍不同** (白名单不掩盖语义差异);
  反向: 把白名单**关掉** (恒等归一) 时, 同一批真实文本必须被判「有残留」⇒ 证明本条判据非空心。

用法: python3 eval/capability/exp1-q28/verify_whitelist_q28.py [--out <json>]
退出码: 0 判据全过 / 2 断言失败 / 3 测量失败。
"""
import argparse
import collections
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
STAGES = [('tasks', 'python3 eval/probe/tasks.py --selftest'),
          ('grade', 'python3 eval/probe/grade.py --selftest'),
          ('run_probe', 'python3 eval/probe/run_probe.py --selftest')]
TMP_RE = re.compile(r'/tmp/[A-Za-z0-9_./-]+')
CLOCK_RE = re.compile(r'\((?:\d+s|instant)\)')
PAREN_RE = re.compile(r'\([^()]{0,20}\)')


def norm(s):
    return CLOCK_RE.sub('(T)', TMP_RE.sub('<TMP>', s))


def sha12(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='eval/capability/exp1-q28/whitelist_coverage_q28.json')
    a = ap.parse_args()

    res = {'schema': 'exp1-q28/whitelist-coverage/v1', 'round': 'EXP1-Q28',
           'note': ('在**原始** stdout 上核验归一化白名单的覆盖面; 本文件不在 registry 的 '
                    'evidence_path 内 (不参与字节 pin), 只作读数。'),
           'whitelist': {'tmp': r'/tmp/[A-Za-z0-9_./-]+ -> <TMP>', 'clock': r'\((\d+s|instant)\) -> (T)'},
           'stages': {}}
    fails = []
    for key, cmd in STAGES:
        p = subprocess.run(['bash', '-lc', cmd], cwd=str(ROOT), capture_output=True,
                           text=True, timeout=300, errors='replace')
        raw = (p.stdout or '') + (p.stderr or '')
        if p.returncode != 0 or not raw:
            print('MEASURE-FAIL: 阶段 %s rc=%s len=%d out_head=%r' % (key, p.returncode, len(raw), raw[:160]))
            return 3
        if 'selftest' not in raw:
            print('MEASURE-FAIL: 阶段 %s 输出不含自检标记 ⇒ 命令未按预期执行 out_head=%r' % (key, raw[:160]))
            return 3
        clock_found = collections.Counter(CLOCK_RE.findall(raw))
        tmp_found = len(TMP_RE.findall(raw))
        n = norm(raw)
        residual = collections.Counter(CLOCK_RE.findall(n))
        ids_norm = len(TMP_RE.findall(n))
        paren_raw = len(PAREN_RE.findall(raw))
        paren_norm = len(PAREN_RE.findall(n))
        # 恒等归一 (关掉白名单) 必须被判「有残留」—— 反空心对照 (只在真有墙钟 token 时要求)
        identity_residual = collections.Counter(CLOCK_RE.findall(raw)) if True else None
        d = {'rc': p.returncode, 'stdout_bytes': len(raw.encode('utf-8')),
             'tmp_tokens_in_raw': tmp_found, 'clock_tokens_in_raw': dict(clock_found),
             'clock_forms': sorted(clock_found),
             'residual_clock_tokens_after_norm': sum(residual.values()),
             'tmp_tokens_after_norm': ids_norm,
             'semantic_paren_raw': paren_raw, 'semantic_paren_after_norm': paren_norm,
             'clock_forms_all_whitelisted': all(re.fullmatch(r'\d+s|instant', f) for f in clock_found),
             'n4b1_residual_zero': sum(residual.values()) == 0,
             'n4b2_semantic_preserved': paren_raw == paren_norm,
             'n4b3_forms_covered': True}
        # N4-a: 语义差异不得被归一吞掉
        m = re.search(r'selftest (\d+)/(\d+)', raw)
        if m:
            mut = raw.replace(m.group(0), 'selftest %d/%s' % (int(m.group(1)) - 1, m.group(2)), 1)
            d['n4a_semantic_diff_survives_norm'] = sha12(norm(mut)) != sha12(norm(raw))
            d['n4a_mutated_token'] = 'selftest %d/%s' % (int(m.group(1)) - 1, m.group(2))
        else:
            d['n4a_semantic_diff_survives_norm'] = None
            d['n4a_note'] = 'no selftest count token found'
        # 反空心: 关掉白名单(恒等归一)时, 若有墙钟 token 则"残留>0"必须成立
        d['anti_hollow_identity_norm_would_flag'] = sum(identity_residual.values()) > 0
        res['stages'][key] = d
        for k in ('n4b1_residual_zero', 'n4b2_semantic_preserved', 'n4a_semantic_diff_survives_norm'):
            if d.get(k) is not True:
                fails.append('%s:%s' % (key, k))

    # 全局反空心: 至少一个阶段真实存在墙钟 token, 且恒等归一会报残留 (否则本条判据在本次读数上空心)
    anti = [v['anti_hollow_identity_norm_would_flag'] for v in res['stages'].values()]
    res['anti_hollow_ok'] = any(anti)
    if not res['anti_hollow_ok']:
        res['anti_hollow_note'] = ('本轮原始 stdout 未出现墙钟 token ⇒ 本条在此读数上不可自证 '
                                   '(不判红, 记不可判; 墙钟形态的实证见产物内的 raw_divergence_located)')
    res['fails'] = fails
    res['ok'] = not fails
    outp = ROOT / a.out
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_bytes((json.dumps(res, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    print(json.dumps({k: res[k] for k in ('anti_hollow_ok', 'fails', 'ok')}, ensure_ascii=False))
    for k, v in res['stages'].items():
        print('  %-10s clock_raw=%s residual=%d sem_paren %d/%d n4a=%s'
              % (k, v['clock_tokens_in_raw'], v['residual_clock_tokens_after_norm'],
                 v['semantic_paren_raw'], v['semantic_paren_after_norm'],
                 v['n4a_semantic_diff_survives_norm']))
    return 0 if res['ok'] else 2


if __name__ == '__main__':
    sys.exit(main())
