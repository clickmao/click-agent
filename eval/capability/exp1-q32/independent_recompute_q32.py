#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · C5: 本轮器具的**独立视角复算** (第二实现, 与主器具零共享代码) + 一致性对账。

复算三面 (全部取自落盘产物/源码, 不看主器具的中间变量):
  R1 面清单摘要: sha256[:12] of instruments.json 字节 ↔ 面记录 `manifest_sha12`;
  R2 行普查   : registry 行数 / 有 evidence_generated_with 的行数 ↔ 守卫产物 rows_total / n_abstain;
  R3 阈值余量 : 从主器具源码**正则派生** soft_cap/k_min ⇒ 余量 = soft_cap/log_bytes ↔ 台账末行 headroom;
  R4 /tmp 普查: 与 census3 的 n_findings / classes 总数对账 (口径 = 可执行段依赖面)。
判别力负控: 扰动 instruments.json 一个字节 (临时副本) ⇒ R1 必须失配 (证明复算非恒绿)。
退出码: 0 全部一致 / 2 有失配 / 3 环境失败。
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
OUT = 'eval/capability/exp1-q32/independent_recompute_q32.json'


def sha12(p):
    with open(p, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def main():
    checks, bad = [], 0

    def add(name, got, want, note=''):
        nonlocal bad
        ok = got == want
        bad += 0 if ok else 1
        checks.append({'check': name, 'recomputed': got, 'recorded': want, 'ok': ok, 'note': note})
        print('  %-34s 复算=%s 记录=%s %s %s' % (name, got, want, 'OK' if ok else 'MISMATCH', note))

    # R1 面清单摘要
    rec = json.load(open(os.path.join(ROOT, 'eval/capability/instruments-check.json'), encoding='utf-8'))
    add('R1.manifest_sha12', sha12(os.path.join(ROOT, 'eval/capability/instruments.json')),
        rec.get('manifest_sha12'))

    # R2 行普查
    reg = json.load(open(os.path.join(ROOT, 'docs/verification-registry.json'), encoding='utf-8-sig'))
    guard = json.load(open(os.path.join(ROOT, 'eval/capability/exp1-q32/reaudit_guard_q32.json'),
                           encoding='utf-8'))
    pinned = sum(1 for r in reg['rows'] if r.get('evidence_generated_with'))
    add('R2.rows_total', len(reg['rows']), guard.get('rows_total'))
    add('R2.rows_unpinned', len(reg['rows']) - pinned, guard.get('n_abstain'))

    # R3 阈值余量 (soft_cap/k_min 从主器具源码派生, 不读它打印的值)
    src = open(os.path.join(ROOT, 'eval/capability/exp1-q22/side_effect_gate.py'), encoding='utf-8',
               errors='replace').read()
    mcap = re.search(r'LOG_SOFT_CAP\s*=\s*([0-9*\s]+)', src)
    soft = 1
    for part in [p.strip() for p in mcap.group(1).strip().rstrip('*').split('*') if p.strip()]:
        soft *= int(part)
    hsrc = open(os.path.join(ROOT, 'eval/capability/exp1-q31/instruments/face_cap_headroom.py'),
                encoding='utf-8', errors='replace').read()
    kmin = float(re.search(r'K_MIN\s*=\s*([\d.]+)', hsrc).group(1))
    lb = rec['side_effect_attribution']['trace'].get('log_bytes')
    headroom = round(soft / lb, 3)
    ledger = [json.loads(x) for x in open(os.path.join(ROOT, 'eval/capability/face-scale-ledger.jsonl'),
                                          encoding='utf-8').read().strip().split('\n') if x.strip()]
    last = ledger[-1]
    q32 = last.get('round') == 'EXP1-Q32'
    add('R3.log_bytes_matches_ledger', lb, last.get('log_bytes') if q32 else lb,
        note='台账末行 = %s' % last.get('round'))
    add('R3.soft_cap', soft, last.get('soft_cap'))
    add('R3.k_min', kmin, last.get('k_min'))
    add('R3.headroom_vs_ledger', headroom, last.get('headroom') if q32 else headroom)
    if not q32:
        checks[-1]['note'] = '台账末行非本轮 ⇒ 待 C2 落账后再复算 (占位一致, 非真对账)'
        checks[-1]['ok'] = False
        bad += 1
        print('  R3.headroom_vs_ledger   台账末行非本轮 ⇒ 由 C2 先行落账后再复算')

    # R4 /tmp 普查总量
    cen = json.load(open(os.path.join(ROOT, 'eval/capability/exp1-q32/tmp_path_census3_q32.json'),
                         encoding='utf-8'))
    add('R4.census_findings', len(cen['findings']), cen['n_findings'])
    add('R4.census_classes_sum', sum(cen['classes'].values()), len(cen['findings']))

    # 判别力负控: 扰动字节 ⇒ R1 必须失配
    tmp = tempfile.mkdtemp(prefix='q32-recompute-')
    try:
        p = os.path.join(tmp, 'instruments.json')
        shutil.copy2(os.path.join(ROOT, 'eval/capability/instruments.json'), p)
        b = bytearray(open(p, 'rb').read())
        b[-2] = (b[-2] + 1) % 256
        open(p, 'wb').write(bytes(b))
        perturbed = sha12(p)
        nc_ok = perturbed != rec.get('manifest_sha12')
        bad += 0 if nc_ok else 1
        checks.append({'check': 'NC.byte_perturbation_detected', 'recomputed': perturbed,
                       'recorded': rec.get('manifest_sha12'), 'ok': nc_ok,
                       'note': '扰动一个字节 ⇒ 复算摘要必须与记录不同 (证明非恒绿)'})
        print('  %-34s 扰动后=%s 记录=%s %s' % ('NC.byte_perturbation_detected', perturbed,
                                              rec.get('manifest_sha12'), 'OK' if nc_ok else 'FAIL'))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    payload = {'round': 'EXP1-Q32', 'schema': 'independent-recompute/1',
               'checks': checks, 'n_checks': len(checks), 'n_failed': bad,
               'independence_note': '第二实现: 摘要/普查/阈值全部自查盘与源码 (正则派生), 不读主器具中间变量'}
    with open(os.path.join(ROOT, OUT), 'w', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    print('INDEPENDENT_RECOMPUTE=%s (%d/%d) 落盘 %s'
          % ('PASS' if bad == 0 else 'FAIL', len(checks) - bad, len(checks), OUT))
    return 0 if bad == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
