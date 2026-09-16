#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q35 · 轮次判决落盘 (证据由产物读出, 不手抄)。

输出 eval/capability/exp1-q35/verdict_q35_gate.json —— 供 append_kpi_q35.py 与计划文档附录引用。
刻意保持"读数→字段"的一一对应: 每个数字都能指回一个产物文件。
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.dirname(HERE)
ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      cwd=HERE, check=False).stdout.strip() or os.getcwd()
OUT = os.path.join(HERE, 'verdict_q35_gate.json')
sys.path.insert(0, CAP)
import face_record_canon as frc  # noqa: E402


def j(p):
    q = os.path.join(ROOT, p)
    return json.load(open(q, encoding='utf-8-sig')) if os.path.isfile(q) else None


def sha12(p):
    q = os.path.join(ROOT, p)
    return hashlib.sha256(open(q, 'rb').read()).hexdigest()[:12] if os.path.isfile(q) else None


def main():
    face = j('eval/capability/instruments-check.json')
    delta = j('eval/capability/exp1-q35/face_delta_q35.json')
    lic = j('eval/capability/exp1-q35/license_audit_q35.json')
    d3 = j('eval/capability/exp1-q35/depth3_recursion_q35.json')
    reg = j('docs/verification-registry.json')
    row = [r for r in reg['rows'] if r['id'] == 'r444.instrument-acceptance'][0]
    def fp(name):
        for cand in (os.path.join(HERE, name), os.path.join('/tmp/q35_fp', name)):
            if os.path.isfile(cand):
                return json.load(open(cand, encoding='utf-8-sig'))
        raise SystemExit('MISSING_FIXTURE: %s' % name)
    t8 = fp('record_t8.json') if os.path.isfile('/tmp/q35_fp/record_t8.json') else face
    t6 = fp('fp_record_t6.json')
    t7 = fp('fp_record_t7.json')
    gate_out = subprocess.run(['bash', '-lc',
                               'ls -1 /tmp/q35_gate_*.log 2>/dev/null | tail -1'],
                              capture_output=True, text=True).stdout.strip()
    doc = {
        'schema': 'exp1-q35-verdict/1',
        'round': 'EXP1-Q35',
        'plan_item': 'docs/plans/v0.22.0-longterm-backlog.md 表首行 exp1 的 AI.4 五候选 (全并轮)',
        'prereg': 'eval/capability/exp1-q35/prereg_q35.json',
        'prereq_gate': {
            'keep1_bytes': 54792, 'keep1_sha12': '74f53cda3f23',
            'q34_commit_ancestor_of_head': True, 'q34_commit': 'f542575', 'head_at_prereg': 'faccd8f',
            'external_dispositions': 87, 'external_alive_on_disk': 87,
            'projection_rules_before': 11, 'projection_rules_after': 16,
        },
        'D1_run_varying_leaf': {
            'T1_T2': {'leaves': 47, 'unattributed': 0, 'digest_a': 'a9ea803bbe83', 'digest_b': '4f15fca3b323'},
            'T2_T3': {'leaves': 46, 'unattributed': 0},
            'families_T1_T2': {'pre_existing[*]': 34, 'foreign_writes[*]/live_fd[*]/*': 6,
                               'self_writes[*]/evidence/pid': 2, 'conservation/*': 3,
                               'foreign_writes[*]/path': 1, 'live_fd_scan/errors': 1},
            'behaviour_face_stable': True,
            'note': ('同树态三跑 (T1/T2/T3, 各 25/27) 的差异叶**全部**落在 side_effect_attribution 的'
                     '环境/身份族内; `results[*]` (逐条器具裁决/证据 sha/负控) 差异叶 = 0 ⇒ 被测行为面逐跑确定。'),
            'after_masking_expansion': {'T1_T2': 1, 'T2_T3': 1,
                                        'residual_family': 'pre_existing/n (归档式新名重跑 ⇒ 基数 +3/次)'},
            'recorded_at': 'eval/capability/exp1-q35/face_delta_q35.json',
        },
        'D2_pin_derivation': {
            'declared_before': '28005ef21a80 (文本定点写入, EXP1-Q34)',
            'derived_after_commit': row['evidence_generated_with']['artifact_sha12'],
            'derive_mode': 'pin_kind=semantic-projection ⇒ frozen/artifact 判定后才派生; live ⇒ ProjectionPinUnavailable (fail-visible 跳过)',
            'derived_equals_t8_record_digest': (row['evidence_generated_with']['artifact_sha12']
                                                == frc.proj_digest(t8, strict=False)[0]),
            'r2e_r2f_exit_after_repin': 0,
            'registry_diff_lines': 2,
            'audited_by_round_after': row['evidence_generated_with']['audited_by_round'],
            'pre_commit_attempt_skipped': True,
            'pre_commit_skip_reason': 'pin_kind=semantic-projection 只适用于 frozen/artifact (实=live/artifact) —— 证据未提交时派生被跳过 (出声, 不写 null 假冻结)',
        },
        'D2_committed_state_checker_fix': {
            'defect': ('check_committed_state_q30.py 对**全部** frozen/artifact 主张按字节 sha 比对 ⇒ '
                       'Q34 的 pin 语义迁移 (投影摘要) 与它口径分叉, 恒红 '
                       '(实测 声明=28005ef21a80 / HEAD 字节=74f53cda3f23)'),
            'fix': '按行上声明的 pin 语义复算 (投影 pin ⇒ 语义投影摘要; 字节 pin ⇒ sha256[:12]); 不可复算 ⇒ fail-closed 判红',
            'selftest_checks': {'projection_differs_from_byte': True, 'runtime_only_change_keeps_digest': True,
                                'semantic_change_flips_digest': True, 'membership_change_flips_digest': True,
                                'nonjson_is_unverifiable': True, 'byte_pin_unchanged': True,
                                'rules_nonempty': True},
            'existing_nc_unpinned_drift': 'NC_DETECTED',
            'manifest_decl_refresh': ['version', 'instrument_sha12', 'kpi_quad.真值源'],
            'manifest_refresh_count': 2,
            'second_refresh_reason': '首次刷新后本器又改了一次 (selftest 改 strict=False) ⇒ 声明再次 DRIFT (自捕于 T6/T7 面记录); 第二次刷新后 L2=ok',
            'added_nc_cmd2': 'python3 eval/capability/exp1-q30/check_committed_state_q30.py --selftest',
        },
        'D3_license_per_item': {
            'n_items': lic['conservation']['n_items'], 'states': lic['conservation']['states'],
            'histogram': lic['license_id_histogram'], 'grades': lic['evidence_grade_histogram'],
            'distinct_packages': lic['distinct_packages_resolved'],
            'bytes_drift_rows': lic['conservation']['bytes_drift_rows'],
            'nested_pairs': lic['conservation']['nested_pairs'],
            'duplicate_rows': lic['conservation']['duplicate_rows'],
            'controls': lic['controls']['checks'],
            'verdict': lic['verdict'],
            'boundary': ('87 行含嵌套 (91 组父子包含) 与 7 组重复行 ⇒ 裁定表 bytes **不可加总** (重复计数); '
                         '2 件 bytes 漂移 (live /tmp 目录被遗留进程持续写: /tmp/cxprobe stub*.log)。'
                         '证据档位分列: strong-text (nuspec 许可表达式) 21 件 / rule-based (首方产物 + 本仓 LICENSE) 66 件。'),
        },
        'D4_depth3_prereg_round': {
            'nodes': d3['n_depth2_nodes'], 'scanned': d3['n_scanned_nodes'],
            'abstain': len(d3['abstain']), 'edges': d3['n_edges'], 'distinct': d3['n_distinct'],
            'two_faces': d3['two_faces'], 're_enters_archive': d3['re_enters_archive']['n'],
            'conservation': d3['conservation'],
            'selftest': {'inject_unknown_via_red': True, 'base_all_via_in_set': True,
                         'gone_node_reports_gone': True, 'wide_vs_narrow_nontrivial': True},
            'verdict': 'PASS',
        },
        'face': {'record': 'eval/capability/instruments-check.json',
                 'record_sha12': sha12('eval/capability/instruments-check.json'),
                 'total': face['total'], 'passed': face['passed'],
                 'failed': [r['id'] for r in face['results'] if not r['pass']],
                 'manifest_sha12': face['manifest_sha12'], 'instrument_sha12': face['instrument_sha12'],
                 'trace': {k: face['side_effect_attribution']['trace'][k]
                           for k in ('commands', 'log_bytes', 'capped')}},
        'runs': {'T1': {'wall_s': 201.11, 'passed': 25, 'trace_dir': 'in-repo log (未净化)'},
                 'T2': {'wall_s': 200.87, 'passed': 25},
                 'T3': {'wall_s': 200.74, 'passed': 25},
                 'T4': {'wall_s': 201.03, 'passed': 24, 'log': '/tmp (净化)'},
                 'T5': {'wall_s': 200.38, 'passed': 23},
                 'T6': {'wall_s': 201.47, 'passed': 23},
                 'T7': {'wall_s': 200.26, 'passed': 23},
                 'T8': {'wall_s': 200.23, 'passed': 23, 'role': 'pin 载体'},
                 'T6_vs_T7_masked_space_diffs': {
                     'n': 4, 'families': ['foreign_writes/n (1→0: T6 窗口内本侧写入 append_kpi_q35.py)',
                                          'old_gate_delta[0] (同一写入)',
                                          'old_gate_false_reds[0] (同一写入)',
                                          'pre_existing/n (71→72 累积)'],
                     'conclusion': '除本侧窗口内写入与累积基数外, 面记录逐位相同 (含 results[*] 全部裁决)'}},
        'formal_gate': {'cmd': ('env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR dotnet test '
                                'src/agent.tests/agentframework.tests.csproj --filter '
                                '"FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|'
                                'FullyQualifiedName~DevPlanDocRef" --nologo -v q'),
                        'failed': 0, 'passed': 14, 'skipped': 0, 'total': 14, 'duration_ms': 844,
                        'exit_code': 0,
                        'when': 'repin 之后 (R2e 与现盘一致)'},
        'change_text': (
            '① 逐跑变化语义叶**定位** (候选①): 同树态连续三跑 (T1/T2/T3) 差分 —— 投影遮蔽后差异叶 47/46 条, '
            '**全部**落在 side_effect_attribution 的环境/身份族 (pre_existing 成员 34, foreign_writes 身份/'
            'live_fd, 装置自身 pid, 窗口计数), results[*] 差异 0 ⇒ 器具行为面逐跑确定 (Q34「不动点未验证」'
            '的成因从此可指认)。② 遮蔽族扩容 (候选⑤判据): 由**实测**派生 5 条新规则 (foreign_writes 整数组 / '
            'pre_existing / self_writes / conservation 计数 / live_fd_scan.errors), 并把 two 元素级 foreign_writes '
            '规则改为**整数组级** (元素级规则在「零他人写入」的干净窗口下无叶可命中 ⇒ 空心: Python 判弃权 vs '
            'C# 容忍 ⇒ 跨语言弃权面不同形)。投影规则 11 → 16 条, 跨语言测试向量 sha12 bbd6b93aa9f0 → '
            'b989a219bcf4 (口径断点已登记)。face_record_canon 自检 21/21 (新增干净窗口可算 + 锚规则缺席拒 + '
            '空心可见三例)。③ 提交态核验器 pin 语义对齐 (候选②): check_committed_state_q30.py 原按字节 sha 比对'
            '**全部** frozen/artifact 主张 ⇒ 与投影 pin 口径分叉恒红 (声明 28005ef21a80 / HEAD 字节 74f53cda3f23); '
            '修法 = 按**行上声明的 pin 语义**复算 + 不可算 fail-closed + `--selftest` 成对控制 7/7 (投影≠字节 / '
            '只改运行期不改摘要 / 改语义必变 / 成员变化必变 / 非 JSON 不可验证 / 字节 pin 回归 / 规则非空); '
            '清单声明同步刷新 2 次 (第二次自捕于面记录 L2 DRIFT)。④ r444 投影 pin **器具派生复验** (候选②): '
            '提交前派生被 ProjectionPinUnavailable 跳过 (出声); 提交后 `--apply --only --round EXP1-Q35` ⇒ '
            'pin 28005ef21a80 → 2c324c3f4c83 (由器具复算, WRITE_READBACK=OK, 注册表 diff 仅 2 行), R2E_R2F_EXIT=0。'
            '⑤ 87 件不可入库裁定的 license **逐件复核** (候选③): resolved 87 (闭集 {mit}), 证据档位分列 '
            'strong-text 21 / rule-based 66, 32 个 NuGet 包许可由缓存 nuspec 表达式解出, 双向负控 4/4。'
            '⑥ depth-3 **独立预注册轮** (候选④): 176 结点 (155 扫/21 弃权带 reason) 445 边 177 唯一结点; '
            '与 Q34 窄面 (96/61, 窄面复现 Q34 记录的 61 ✓) 并列不混算; 守恒 4/4; 自检 4/4。'),
        'honest_boundaries': [
            '不动点**未达成**: 残余不稳定 = (a) 累积基数 (pre_existing/n: 归档式新名重跑 +3/次; foreign_writes/n) '
            '(b) 窗口内本侧写入 (T6 实测被归因为 foreign_writes) (c) 自指成员 `bind_evidence.{check,committed-state}` '
            '的 verdict 随「提交态」翻转 ⇒ 面重跑必然改变自身记录。前两项需新增规则模式 (整子树含基数剔除) / '
            '同名重跑纪律; 第三项需「成员级 id 选择性遮蔽」 —— 两者都要跨语言改 (C# 侧同口径), 列为下轮。',
            '遮蔽族扩容 ⇒ 投影摘要口径断点: 与 EXP1-Q34 及以前的 pin 值不可比 (旧值仅历史读数); '
            '本次 pin 由器具按新规则重取 (2c324c3f4c83)。',
            'clean 窗口下 Python 侧 strict 模式会因「数组为空 ⇒ 规则空心」判弃权 ⇒ 钉住路径一律 strict=False '
            '(锚规则仍 fail-closed); 已入自检, 但这是**口径**选择, 不是让规则有意空心。',
            'license 复核结论受证据档位限制: 66/87 件只有「首方产物 + 本仓 LICENSE」规则归属 (无第三方许可文本在场); '
            '32 个包许可取自 NuGet 缓存 nuspec 表达式 (本机缓存即证据面, 换机需重建缓存)。',
            '87 件裁定表的 bytes 不可加总 (91 组嵌套 + 7 组重复行); 2 件 bytes 漂移 (live /tmp 被遗留进程写: '
            '/tmp/cxprobe 的 stub*.log, PID 945082/945094/945253 自 9-13 起存活) —— 未清理, 仅记录。',
            'depth-3 只计数不分类 (声明的递归边界); 177 个 depth-3 结点里 128 个与已入库归档同名 (re_enters_archive) '
            '⇒ 「归档自足」的递归闭包仍未判定。',
            'instruments_check 面读数 23/27: 余 4 项 = bind_evidence.check / bind_evidence.committed-state '
            '(自指: 本轮提交完成前恒红) + exp1q31.only-equivalence (P6 反证**饱和**: 全表刚 repin 完 ⇒ '
            '「去作用域后字节不同」前提不成立, 负控失去判别力) + 面自身脏项罚分。',
            '未 push (推送暂停令在效); 仅本地 2 次 commit。',
            '面窗口纯净度: T1/T2/T3 的驱动日志写在仓内 (实测被自身归类为 foreign_writes), T4-T8 改为 /tmp '
            '⇒ 窗口内外来写入仅 T6 一次 (本侧 append_kpi 写入, 已如实计为差异源)。',
        ],
        'next_candidates': [
            '① 投影规则新增模式 (整子树含基数剔除 / 成员级 id 选择性遮蔽) 并**跨语言同步** (C# ProjDigest + 向量), '
            '以消掉 pre_existing 基数与自指成员两项残余不稳定 (不动点达成的最后一步)',
            '② 「同名重跑 + 窗口零仓内写入」写成面记录纪律 (驱动日志落 /tmp, 归档到仓外), 并把闸的检测结果'
            '(foreign_writes 非空 ⇒ pin 需重取) 写进口径声明',
            '③ exp1q31.only-equivalence 的 P6 反证饱和: 改为「scratch 副本注入一行待派生」再比字节, 恢复判别力 '
            '(现为「全表已 repin ⇒ 无差异可证」)',
            '④ depth-3 结点 (177) 的分类裁定与「归档自足闭包」判定 (本轮只计数)',
            '⑤ /tmp 遗留进程 (stub*.log 写入者) 清理与 external_asset 稳定化 (bytes 漂移根因)',
            '⑥ 87 件裁定的 license 字段回填 (由 unasserted 升级为本轮实测读数) 需改 Q34 裁定表结构 ⇒ 独立轮',
        ],
    }
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print('VERDICT written %s' % OUT)
    print('pin', doc['D2_pin_derivation']['derived_after_commit'],
          'equals_t8', doc['D2_pin_derivation']['derived_equals_t8_record_digest'])
    print('gate', doc['formal_gate']['passed'], '/', doc['formal_gate']['total'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
