#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q42 · M1 负控: 刷新后的 E5 判据不是「被放宽的判据」而是**换掉过期期望**。

判据 (前态/现态成对, 全部机检, 禁自证):
  N1 前态 sha (EXP1-Q41 提交 ecd363d 的该件字节) 是 HEAD 的祖先 ∧ 与现盘不同 (对照物不可变, 非 HEAD 浮动引用)。
  N2 前态字节 **含**旧 check 名 `E5_hook_default_off_passes_bad_list` ∧ **不含**新名 `E5_hook_default_blocks_bad_list`
     ⇒ 归档的 E5 FAIL 可归属到前态字节 (不是别的原因)。
  N3 现盘字节 **含** 新名 (默认档拦下) ∧ 含 `E5b_hook_explicit_off_passes_bad_list` (显式关闸臂) ⇒ 判据未删除, 只是拆成两臂。
  N4 归档首跑 txt 的 mtime **早于** 现盘脚本 mtime ∧ 文本含 `E5_hook_default_off_passes_bad_list` 与 `FAIL`
     ⇒ 「过期」是改前实测, 不是事后追认。
  N5 现盘字节把两臂的期望值写成**相反**的 rc (默认档 ⇒ rc==1 ∧ 显式关 ⇒ rc==0) ⇒ 两臂不可同时空过。
退出码: 0 全绿 / 2 判据红 / 3 环境不可得。
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
REL = 'eval/capability/exp1-q40/selftest_q40_taillf.py'
PRE_SHA = 'ecd363d'                      # EXP1-Q41 提交 (钉死, 禁写 HEAD)
ARCHIVE = 'eval/capability/exp1-q42/taillf_q40_selftest_after_promotion_q42.txt'
OUT = ROOT / 'eval/capability/exp1-q42/nc_prestate_q42.json'


def git(*a):
    return subprocess.run(['git', '-C', str(ROOT)] + list(a), capture_output=True, text=True)


def main():
    checks, detail = {}, {}
    pre = git('show', '%s:%s' % (PRE_SHA, REL))
    if pre.returncode != 0:
        print('ENV: 取前态字节失败 rc=%d (%s) ⇒ 弃权' % (pre.returncode, PRE_SHA))
        return 3
    pre_bytes = pre.stdout
    disk_bytes = (ROOT / REL).read_text(encoding='utf-8')

    anc = git('merge-base', '--is-ancestor', PRE_SHA, 'HEAD')
    checks['N1_pre_sha_is_ancestor_and_differs'] = (anc.returncode == 0 and pre_bytes != disk_bytes)
    detail['N1'] = {'pre_sha': PRE_SHA, 'ancestor_rc': anc.returncode,
                    'pre_len': len(pre_bytes), 'disk_len': len(disk_bytes)}

    checks['N2_prestate_has_only_old_expectation'] = ('E5_hook_default_off_passes_bad_list' in pre_bytes
                                                     and 'E5_hook_default_blocks_bad_list' not in pre_bytes)
    detail['N2'] = {'old_name_in_prestate': 'E5_hook_default_off_passes_bad_list' in pre_bytes,
                    'new_name_in_prestate': 'E5_hook_default_blocks_bad_list' in pre_bytes}

    checks['N3_disk_has_new_default_and_explicit_off_arm'] = ('E5_hook_default_blocks_bad_list' in disk_bytes
                                                             and 'E5b_hook_explicit_off_passes_bad_list' in disk_bytes)
    detail['N3'] = {'new_name_in_disk': 'E5_hook_default_blocks_bad_list' in disk_bytes,
                    'off_arm_in_disk': 'E5b_hook_explicit_off_passes_bad_list' in disk_bytes}

    arch = ROOT / ARCHIVE
    if not arch.exists():
        print('ENV: 归档 %s 不存在 ⇒ 弃权' % ARCHIVE)
        return 3
    a_txt = arch.read_text(encoding='utf-8', errors='replace')
    mtime_ok = arch.stat().st_mtime < (ROOT / REL).stat().st_mtime
    checks['N4_archive_is_before_refresh'] = (mtime_ok and 'E5_hook_default_off_passes_bad_list' in a_txt
                                              and 'FAIL' in a_txt)
    detail['N4'] = {'archive_mtime': arch.stat().st_mtime, 'script_mtime': (ROOT / REL).stat().st_mtime,
                    'archive_says_fail': 'FAIL' in a_txt}

    # N5 两臂期望相反: 从源码取 rc 期望值 (禁手抄)
    i_def = disk_bytes.index('checks[\'E5_hook_default_blocks_bad_list\']')
    i_off = disk_bytes.index('checks[\'E5b_hook_explicit_off_passes_bad_list\']')
    def_expr = disk_bytes[i_def:i_def + 160]
    off_expr = disk_bytes[i_off:i_off + 200]
    checks['N5_arms_expect_opposite_rc'] = ('rc5 == 1' in def_expr and 'rc5b == 0' in off_expr)
    detail['N5'] = {'default_arm_expr': def_expr.split('\n')[0].strip(),
                    'off_arm_expr': off_expr.split('\n')[0].strip()}

    ok = all(checks.values())
    payload = {'round': 'EXP1-Q42', 'schema': 'nc-prestate-q42/1', 'checks': checks,
               'detail': detail, 'verdict': 'PASS' if ok else 'FAIL'}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for k in sorted(checks):
        print('%-46s %s' % (k, 'PASS' if checks[k] else 'FAIL'))
    print('VERDICT=%s out=%s' % (payload['verdict'], OUT))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
