#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 候选⑥+⑦: 器具面扩容 (3 条新器具进 L2) + 自引用器具行版本刷新。

新增/变更:
  1. `l2.instruments-check` 行的 instrument_sha12/version 刷新 (器具本体被本轮修改 ⇒ 必须重审);
  2. `bind_evidence.check`            —— 现盘档: 登记表声明 pin vs 工作区字节 (负控注入 pin 破坏);
  3. `bind_evidence.committed-state`  —— 冻结/提交档 (`-c Release` 变体的口径落地): HEAD 登记表主张 vs HEAD blob;
  4. `exp1q28.whitelist-coverage`     —— Q28 白名单覆盖面核验器进器具面 (负控 = 恒等归一必报残留)。
纪律 (承 R409): 序列化器逐字节复现断言 → 只做定点插入/替换 → 幂等 → 写后读回。
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
MAN = 'eval/capability/instruments.json'
MAN_ABS = os.path.join(ROOT, MAN)


def sha12(rel):
    return hashlib.sha256(open(os.path.join(ROOT, rel), 'rb').read()).hexdigest()[:12]


def entry(id_, kind, cmd, expect_substr, nc_cmd, nc_expect, ev_path, unit, denom, truth, caliber,
          surface, count, reason, owner='EXP1-Q30'):
    s = sha12(ev_path)
    e = {'id': id_, 'kind': kind, 'cmd': cmd, 'expect_rc': 0, 'expect_substr': expect_substr,
         'nc_cmd': nc_cmd, 'nc_expect': nc_expect,
         'version': 'content-sha12:' + s, 'version_source': 'content-sha12', 'instrument_sha12': s,
         'input_fingerprint': [],
         'kpi_quad': {'单位': unit, '分母': denom, '真值源': truth, '口径档': caliber},
         'owner_round': owner, 'evidence_path': ev_path,
         'input_surface': surface, 'input_surface_source': 'audit_hook',
         'input_surface_reason': reason}
    if surface == 'dynamic_corpus':
        e['corpus_dynamic_count'] = count
    return e


def main():
    raw = open(MAN_ABS, encoding='utf-8', newline='').read()
    doc = json.loads(raw)
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    tail = '\n' if raw.endswith('\n') else ''
    if ser + tail != raw:
        print('SER_ASSERT=FAIL 序列化器未能逐字节复现原文件 (禁改写)')
        return 3
    print('SER_ASSERT=OK (indent=1, ensure_ascii=False, tail=%s)' % ('LF' if tail else 'NONE'))
    rows = doc['instruments']
    ids = [e['id'] for e in rows]
    if 'bind_evidence.check' in ids:
        print('IDEMPOTENT=OK (已应用)')
        return 0

    # --- 1) 自引用行版本刷新 ---
    upd = [e for e in rows if e['id'] == 'l2.instruments-check']
    assert len(upd) == 1
    new_sha = sha12('eval/capability/instruments_check.py')
    old = upd[0]['instrument_sha12']
    upd[0]['instrument_sha12'] = new_sha
    upd[0]['version'] = 'content-sha12:' + new_sha
    print('REFRESH l2.instruments-check instrument_sha12 %s -> %s' % (old, new_sha))

    # --- 2) 3 条新器具 ---
    n_rows = len(json.load(open(os.path.join(ROOT, 'docs/verification-registry.json'),
                                encoding='utf-8'))['rows'])
    new = [
        entry('bind_evidence.check', 'registry-checker',
              'python3 eval/capability/bind_evidence.py --check', 'R2E_R2F_EXIT=0',
              'bash eval/capability/exp1-q30/_nc_bind_evidence_pin.sh', 'detect:NC_DETECTED',
              'eval/capability/bind_evidence.py',
              '登记行', '产品面证据行 (level∈L1..L4 ∧ evidence_path∈eval/|docs/reports/)',
              '磁盘文件重算 sha256[:12] + 工作区 git 状态', '现盘档 (声明 pin vs 工作区字节)',
              'dynamic_corpus', n_rows,
              '登记表为追加式动态语料 (行数随轮增长, 其 pin 目标也在轮内变化) ⇒ 不做字节指纹, 记行数'),
        entry('bind_evidence.committed-state', 'registry-checker',
              'python3 eval/capability/exp1-q30/check_committed_state_q30.py', 'COMMITTED_STATE_CHECK=OK',
              'python3 eval/capability/exp1-q30/check_committed_state_q30.py --inject-defect unpinned-drift',
              'detect:NC_DETECTED',
              'eval/capability/exp1-q30/check_committed_state_q30.py',
              '主张(frozen×artifact)', 'HEAD 登记表 frozen/artifact 主张数',
              'git cat-file --batch 取 HEAD blob 字节重算 sha256[:12]', '冻结/提交档 (HEAD 内部自洽)',
              'dynamic_corpus', n_rows,
              '核验对象 = HEAD 版登记表 (随轮增长); 主张集由 HEAD 内容派生 ⇒ 不做字节指纹'),
        entry('exp1q28.whitelist-coverage', 'analyzer',
              'python3 eval/capability/exp1-q28/verify_whitelist_q28.py', '"ok": true',
              'python3 eval/capability/exp1-q30/_nc_wl_identity_q30.py', 'detect:NC_DETECTED',
              'eval/capability/exp1-q28/verify_whitelist_q28.py',
              '归一后残留处数', '三阶段原始 stdout 全文',
              '真实原始文本 (非已归一文本) 重算', '白名单覆盖面 + 恒等归一反空心对照',
              'dynamic_corpus', 3,
              '输入 = 三阶段命令的实时 stdout (每次运行重放, 非仓库内固定语料)'),
    ]
    rows.extend(new)
    out = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    open(MAN_ABS, 'w', encoding='utf-8', newline='').write(out)
    back = open(MAN_ABS, encoding='utf-8', newline='').read()
    print('WRITE_READBACK=%s' % ('OK' if back == out else 'MISMATCH'))
    d2 = json.loads(back)
    print('INSTRUMENTS %d -> %d' % (len(doc['instruments']) - len(new), len(d2['instruments'])))
    print(subprocess.run(['git', 'diff', '--numstat', '--', MAN], cwd=ROOT, capture_output=True,
                         text=True).stdout.strip())
    return 0 if back == out else 2


if __name__ == '__main__':
    sys.exit(main())
