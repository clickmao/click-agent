#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 候选⑥: 提交态内部一致性核验 (登记行 `-c Release` 变体的口径落地 = 冻结/提交档)。

与 worktree 档的分工:
  * worktree 档 (`bind_evidence.py --check`)  —— 查**现盘**: 声明 pin vs 工作区字节;
  * 提交态档 (本器具)                         —— 查**HEAD**: HEAD 版登记表的每条 frozen/artifact 主张
    vs HEAD blob 重算 sha256[:12]。
提交期缺口 (worktree 档结构性查不出): 「器具/证据已改但登记表未重审」——改动一旦 `git add` 后提交,
工作区与声明**都**变成新的 (工作区档自然绿), 而**HEAD 里那一步是否自洽**无人核验。
取字节用一次 `git cat-file --batch` (不逐文件起进程)。

用法:
  python3 eval/capability/exp1-q30/check_committed_state_q30.py
  python3 eval/capability/exp1-q30/check_committed_state_q30.py --inject-defect unpinned-drift   # 负控
"""
import hashlib
import json
import subprocess
import sys

REG = 'docs/verification-registry.json'


def git(*args, data=None):
    return subprocess.run(['git'] + list(args), capture_output=True, input=data, check=True).stdout


def main():
    inject = '--inject-defect' in sys.argv
    mode = sys.argv[sys.argv.index('--inject-defect') + 1] if inject else None
    raw = git('show', 'HEAD:%s' % REG)
    doc = json.loads(raw.decode('utf-8'))
    rows = doc['rows']

    # 收集需要冻结字节的行: frozen + artifact
    want, claims = [], []
    for r in rows:
        f = r.get('evidence_generated_with')
        if not isinstance(f, dict):
            continue
        if f.get('pin_status') != 'frozen':
            continue
        if f.get('evidence_kind') == 'directory':
            continue        # 目录聚合行的清单式 pin 另有器具 (本器只核 artifact 字节)
        ep, pin = r.get('evidence_path'), f.get('artifact_sha12')
        inst, ipin = f.get('instrument'), f.get('instrument_sha12')
        if inject and mode == 'unpinned-drift' and not claims:
            pin = 'deadbeef0000'          # 只在内存里改一条主张 ⇒ 模拟「改了没重审就提交」
        claims.append((r.get('id'), 'artifact', ep, pin))
        want.append(ep)
        if inst:
            claims.append((r.get('id'), 'instrument', inst, ipin))
            want.append(inst)

    paths = sorted({p for p in want if p})
    sha = {}
    req = '\n'.join('HEAD:%s' % p for p in paths) + '\n'
    out = git('cat-file', '--batch', data=req.encode())
    i = 0
    for p in paths:
        j = out.index(b'\n', i)
        header = out[i:j].decode('utf-8', 'replace').split()
        i = j + 1
        if len(header) == 2 and header[1] == 'missing':
            sha[p] = None
            continue
        size = int(header[2])
        body = out[i:i + size]
        i += size + 1
        sha[p] = hashlib.sha256(body).hexdigest()[:12]

    viol = [(rid, kind, p, pin, sha.get(p)) for rid, kind, p, pin in claims
            if p is None or sha.get(p) != pin]
    if inject:
        if viol:
            print('NC_DETECTED (注入 %s ⇒ %d 条违反: %s)' % (mode, len(viol), viol[0]))
            return 0
        print('NC_NOT_DETECTED (注入未被检出 ⇒ 器具空心)')
        return 1
    n_claims = len(claims)
    print('COMMITTED_STATE rows=%d claims=%d blobs=%d' % (len(rows), n_claims, len(paths)))
    for v in viol[:10]:
        print('  VIOLATION %s/%s %s 声明=%s HEAD=%s' % v)
    if viol:
        print('COMMITTED_STATE_CHECK=FAIL (%d 条)' % len(viol))
        return 2
    print('COMMITTED_STATE_CHECK=OK (HEAD 登记表主张与 HEAD blob 逐条一致)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
