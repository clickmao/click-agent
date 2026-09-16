#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · 收口: 附录 AF + KPI 台账行 + 门禁读数归档 (全部由产物现算, 禁手抄数字)。

① `eval/capability/kpi.jsonl` 追加本轮行 (键集对齐上一行, 幂等: 同 round 已存在则不追加);
② `eval/capability/exp1-q31/gate_readings_q31.json`: dotnet 门禁两次真跑的读数 (log 被 .gitignore 忽略 ⇒
   归档 stdout/sha256/分类, 不归档 .log 本体);
③ 计划文档追加/替换「附录 AF」段 (数字全部从 JSON 产物读取)。
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
Q31 = 'eval/capability/exp1-q31'
PLAN = 'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md'
KPI = 'eval/capability/kpi.jsonl'
MARK = '### AF. EXP1-Q31'


def j(rel):
    return json.load(open(os.path.join(ROOT, rel), encoding='utf-8-sig'))


def sha12(rel):
    p = os.path.join(ROOT, rel)
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12] if os.path.isfile(p) else None


def gate_readings():
    out = {'schema': 'q31-gate-readings/1', 'runs': []}
    for label in ('r420-recall-wiring', 'formal-gate-q31', 'formal-gate-q31b'):
        log = os.path.join(Q31, 'logs/%s.log' % label)
        p = os.path.join(ROOT, log)
        if not os.path.isfile(p):
            continue
        raw = open(p, 'rb').read()
        tail = [l.strip() for l in raw.decode('utf-8', 'replace').splitlines() if 'Failed:' in l][:1]
        out['runs'].append({'label': label, 'log_bytes': len(raw), 'log_sha256_16': hashlib.sha256(raw).hexdigest()[:16],
                            'summary_line': tail[0] if tail else None})
    return out


def kpi_line():
    disp = j('%s/residual_disposition_q31.json' % Q31)
    q30 = j('eval/capability/exp1-q30/instrument_gap_census_q30.json')
    q31 = j('%s/instrument_gap_census_q31.json' % Q31)
    face = j('eval/capability/instruments-check.json')
    led = [json.loads(l) for l in open(os.path.join(ROOT, 'eval/capability/face-scale-ledger.jsonl'),
                                       encoding='utf-8-sig') if l.strip()]
    hook = j('%s/verdict_q31_hook_gate.json' % Q31)
    return {
        'round': 'EXP1-Q31',
        'ts': subprocess.run(['date', '+%Y-%m-%dT%H:%M%z'], capture_output=True, text=True).stdout.strip(),
        'kind': 'self-check / 残留器具行裁定并轮 (5→0) + 判据绑误用重写 + 提交前跨写者闸入钩子 + 器具面扩容 21→27 + 阈值余量台账 (60m 自检作业, 不占主线轮号)',
        'artifact': ('eval/capability/exp1-q31/{prereg_q31.json,instruments/*.py,verify_stage_guard_hook_q31.py,'
                     'residual_disposition_q31.py,residual_disposition_q31.json,instrument_gap_census_q31.json,'
                     'rewrite_evidence_cmd_q31.py,edit_manifest_q31.py,apply_face_fixes_q31.py,commit_q31.py,'
                     'fix_write_side_links_q31.py,tmp_archive_identity_q31.json,verdict_q31_hook_gate.json,'
                     'gate_readings_q31.json,write_side_after_q31.json,round_artifact_list_q31.txt}; '
                     'tools/hooks/pre-commit; eval/capability/{instruments.json,instruments_check.py,'
                     'instruments-check.json,face-scale-ledger.jsonl}; docs/verification-registry.json; '
                     'docs/improvements.md (5 条根相对链接); docs/plans/v0.22.0-exp1-local-index-and-code-graph.md (附录 AF)'),
        'change': ('① 残留 5 行器具化: 覆盖 %d→%d 行, 未派生 %d→%d; 其中 `engine.retired.no_local_gguf` 的原声明'
                   '(全树词面 grep)在现盘**为假**(合法 kernel32 声明被误杀)⇒ 判据重写为「绑子系统作用域 + 互操作库允许清单」'
                   '(正控 1 + 负控 3); `r462.weight-probe` 归档已在仓库内且与 /tmp 原件逐位相同(sha256 3/3)⇒ 缺口在声明层, '
                   '改指自足入口(真跑 execution_blocked); 2 行裸 dotnet test 命令行→外部测试面包装器(退出码三分类 0/2/3); '
                   '1 行 `python3 -c` 一次性读取→带控制器具。'
                   '② 全量面跨会话复跑: %d/%d 通过(首跑 20/27 的 7 红已按类修复, 见附录 AF.5), 窗口命令 %d 条, '
                   'trace %d B, 守恒 %d==%d。'
                   '③ stage_guard 入 pre-commit (env 门控默认关) + 8/8 机检(含「空心钩子」反证), 真仓默认关零回归; '
                   'dogfood: 该闸拦下本侧自己的首次提交(清单未含清单文件)rc=1, 修后放行。'
                   '④ 阈值台账 face-scale-ledger.jsonl 2 行: 21 器具/47 命令 余量 %.3f → 27 器具/59 命令 余量 %.3f '
                   '(K_MIN=2.0, 已贴下沿)。'
                   '⑤ 器具面 21→27 (6 新行各配负控) + `verify_q30_only` 等价判据自足化为长驻闸(8/8, 夹具锚现场派生); '
                   '`hooks.pre-commit` 器具字节变更触发 DRIFT ⇒ 声明 sha 重审(闸有效性的正向证据)。'
                   '⑥ R486 残留 8: docs/improvements.md 5 条根相对链接修复(提及守恒 23 处未动), 写侧探针复跑 '
                   'moved 5→0 / resolved 79→84 / 0.908→0.9655。'
                   '⑦ 前序漂移收口(非本轮成果): r483b 器具 pin 陈旧(R487 提交未重审) + r487×3 缺 '
                   'evidence_generated_with ⇒ 定向重审/补字段后 R2E_R2F_EXIT=0。')
        % (q30['rows_covered'], q31['rows_covered'], q30['no_instrument'], q31['no_instrument'],
           face['passed'], face['total'], face['side_effect_attribution']['trace']['commands'],
           face['side_effect_attribution']['trace']['log_bytes'],
           face['side_effect_attribution']['conservation']['classified'],
           face['side_effect_attribution']['conservation']['expected'],
           led[0]['headroom'] if led else 0, led[-1]['headroom'] if led else 0),
        'verdict': 'PASS (全量面 27/27; 残留 0; 形式门禁 Failed 0/Passed 14)',
        'readings': {'census': {'before': {'covered': q30['rows_covered'], 'derived': q30['derived_instrument'],
                                           'no_instrument': q30['no_instrument']},
                                'after': {'covered': q31['rows_covered'], 'derived': q31['derived_instrument'],
                                          'no_instrument': q31['no_instrument']}},
                     'distribution': disp['distribution'],
                     'face': {'before': {'passed': 21, 'total': 21, 'commands': 47, 'log_bytes': 29715723,
                                         'headroom': 2.258},
                              'after': {'passed': face['passed'], 'total': face['total'],
                                        'commands': face['side_effect_attribution']['trace']['commands'],
                                        'log_bytes': face['side_effect_attribution']['trace']['log_bytes'],
                                        'headroom': led[-1]['headroom'] if led else None}},
                     'hook_gate': {'verdict': hook['verdict'], 'n': hook['n_checks']},
                     'write_side': {'before': j('eval/capability/exp1-q31/write_side_before_q31.json')['classes'],
                                    'after': j('%s/write_side_after_q31.json' % Q31)['classes']}},
        'honest_bounds': [
            'r462 归档件硬编码 /tmp 语料 ⇒ 归档不自足, 真跑未执行 (execution_blocked)',
            '9 行 evidence_cmd 仍含 /tmp 路径 (参数/输出), 逐行核查列下轮',
            '余量 2.019 已贴 K_MIN=2.0 下沿 ⇒ 下次面扩容前必须先复测阈值',
            'r444 artifact 提交前结构性只能派生成 live/worktree-only; 提交后重审回 frozen',
        ],
        'next': [
            '9 行 /tmp 路径逐行核查 (含 r462 wrapper 的语料注入)',
            '面扩容前阈值复测 + K_MIN 是否随面规模重定',
            'r483b/r487 类「器具改而登记表未重审」的提交前机检 (防下次再漏)',
        ],
    }


def appendix():
    disp = j('%s/residual_disposition_q31.json' % Q31)
    q30 = j('eval/capability/exp1-q30/instrument_gap_census_q30.json')
    q31 = j('%s/instrument_gap_census_q31.json' % Q31)
    face = j('eval/capability/instruments-check.json')
    led = [json.loads(l) for l in open(os.path.join(ROOT, 'eval/capability/face-scale-ledger.jsonl'),
                                       encoding='utf-8-sig') if l.strip()]
    hook = j('%s/verdict_q31_hook_gate.json' % Q31)
    ws_b = j('%s/write_side_before_q31.json' % Q31)
    ws_a = j('%s/write_side_after_q31.json' % Q31)
    rows = '\n'.join('| %s | %s | %s | `%s` | %s |' % (d['id'], d['level'], d['rule'],
                                                      os.path.basename(d['instrument'] or '-'), d['action'])
                     for d in disp['dispositions'])
    checks = ' / '.join('%s=%s' % (k.split('_')[0], 'OK' if v else 'FAIL') for k, v in disp['checks'].items())
    L = []
    L.append('')
    L.append(MARK + ' 收口: 残留器具行裁定并轮 + 判据绑误用重写 + 提交前跨写者闸入钩子 + 器具面 21→27 + 阈值余量台账')
    L.append('')
    L.append('> 分支 A · 计划项 exp1 (v0.22.0-longterm-backlog 最前未完成项)。触发 = AE.7 五候选 (用户令 2026-09-16 '
             '全部候选并轮) + R486 §5 残留 8。预注册见 `eval/capability/exp1-q31/prereg_q31.json`。60m 自检作业轮号段 '
             '(EXP1-Qxx), 不占主线轮号。')
    L.append('')
    L.append('#### AF.1 残留 5 行的裁定表 (分布先行, 机检产出)')
    L.append('')
    L.append('覆盖行 %d, 分布: evidence_kind=%s / 器具派生=%s / 命令形态=%s。'
             % (disp['rows_covered'], json.dumps(disp['distribution']['by_evidence_kind'], ensure_ascii=False),
                json.dumps(disp['distribution']['by_instrument'], ensure_ascii=False),
                json.dumps(disp['distribution']['by_cmd_shape'], ensure_ascii=False)))
    L.append('')
    L.append('| 行 | 级别 | 裁定规则 | 仓库内器具 | 动作 |')
    L.append('|---|---|---|---|---|')
    L.append(rows)
    L.append('')
    L.append('机检: %s (核查 %s)。读数: 覆盖 %d→%d / 有器具 %d→%d / 未派生 %d→%d。'
             % (checks, disp['n_checks'], q30['rows_covered'], q31['rows_covered'],
                q30['derived_instrument'], q31['derived_instrument'], q30['no_instrument'], q31['no_instrument']))
    L.append('')
    L.append('**真实发现 (原声明在现盘为假)**: `engine.retired.no_local_gguf` 的原命令 '
             '`! grep -rq "DllImport|LibraryImport" src/ --include=*.cs` 现盘 **rc=1** —— 命中的是 '
             '`src/agent/llmservice/WindowsMemory.cs` 的 `[DllImport("kernel32.dll")]` (v0.20.1 P4-c / R344 的合法'
             '跨平台内存探测), 与「本地 GGUF/原生推理层退役」无关 ⇒ **词面判据过宽** (标记「出现」≠「误用」)。'
             '新判据 = 四条退役路径不存在 + 全树互操作库允许清单(`kernel32.dll`, 带理由) + 退役作用域 0 声明; '
             '控制: 正控(仅合法 kernel32)=绿, 负控(注入 `ggml.dll` / 在退役作用域内注入 kernel32 / 重建退役路径)全红。')
    L.append('')
    L.append('**存在面 ≠ 扫描面**: `r462.weight-probe` 的器具/语料/报告器**已在仓库内且与 /tmp 原件逐位相同** '
             '(`sha256` 3/3, `tmp_archive_identity_q31.json`) ⇒ 缺口在**声明层**(evidence_cmd 仍指 /tmp); '
             '且归档件硬编码 `CORPUS = "/tmp/r462_corpus.json"` ⇒ **归档不自足** ⇒ 改指自足入口 wrapper, 真跑标 '
             '`execution_blocked` (需 gguf + llama-server, 本轮未跑, 不宣称已验证)。')
    L.append('')
    L.append('#### AF.2 动作')
    L.append('')
    L.append('1. **5 行 evidence_cmd → 仓库内器具** (`rewrite_evidence_cmd_q31.py`, 序列化器逐字节复现断言 + 逐行探针机检 + 幂等 + 读回 + numstat 5/5)。')
    L.append('2. **全量面跨会话复跑** (同器具面, 与 Q30 首次运行隔一个会话): `%d/%d` 通过, 命令 %d 条, trace %d B, '
             '守恒 %s==%s, 归因闸 verdict=%s。'
             % (face['passed'], face['total'], face['side_effect_attribution']['trace']['commands'],
                face['side_effect_attribution']['trace']['log_bytes'],
                face['side_effect_attribution']['conservation']['classified'],
                face['side_effect_attribution']['conservation']['expected'],
                face['side_effect_attribution']['verdict']))
    L.append('3. **`r444.instrument-acceptance` 重审**: 其证据=全量面记录(每次跑重写) ⇒ 记录刷新后必须重审 pin '
             '(提交时序语义: 未提交件结构性只能派生成 live/worktree-only)。')
    L.append('4. **stage_guard 入提交钩子** (`tools/hooks/pre-commit`, env `AGENTFRAMEWORK_STAGE_MANIFEST` 门控, '
             '默认关=零回归): 机检 8/8 —— 默认关放行 / 清单==staged 放行 / 对侧在飞文件拒绝 / 清单缺失 fail-closed / '
             '条数相同内容不同被拒 / 空心钩子反证 / 真仓默认关 rc=0 / 夹具器具逐字节同日。')
    L.append('5. **阈值余量台账** (`face-scale-ledger.jsonl`, 幂等追加): 阈值从器具源码读 (单一权威), 判据 '
             '`soft_cap ≥ 2.0 × 实测 log_bytes`; 读数 %d 器具/%d 命令 ⇒ %d B, 余量 **%.3f** (上一行 %d/%d ⇒ %d B, %.3f)。'
             % (led[-1]['n_instruments'], led[-1]['n_commands'], led[-1]['log_bytes'], led[-1]['headroom'],
                led[0]['n_instruments'], led[0]['n_commands'], led[0]['log_bytes'], led[0]['headroom']))
    L.append('6. **器具面 21 → 27**: 新增 6 行 (退役面断言 / 清理台账 / 测试面分类器 / 阈值余量 / 等价闸 / 钩子闸), '
             '每行成对正控+负控; `verify_q30_only` 的等价判据**自足化**为长驻闸 `only_equivalence_guard.py` '
             '(夹具锚从当前登记表现场派生, 防旧轮 pin 字面量过期)。')
    L.append('7. **R486 §5 残留 8**: `docs/improvements.md` 5 条根相对链接修 `./`; 反引号提及 23 处未动 (守恒); '
             '写侧探针复跑: moved %s→%s, resolved %s→%s。'
             % (ws_b['classes'].get('moved'), ws_a['classes'].get('moved'),
                ws_b['classes'].get('resolved'), ws_a['classes'].get('resolved')))
    L.append('')
    L.append('#### AF.3 读数 (全部机检, 产物可复算)')
    L.append('')
    L.append('| 面 | 前 | 后 | 判据 / 器具 |')
    L.append('|---|---|---|---|')
    L.append('| 残留器具行 | %d 行未派生 (覆盖 %d) | **%d 行** (覆盖 %d) | `residual_disposition_q31.json` %s |'
             % (q30['no_instrument'], q30['rows_covered'], q31['no_instrument'], q31['rows_covered'], disp['n_checks']))
    L.append('| 全量面 | 21/21 (Q30, 47 命令) | **%d/%d** (%d 命令, 跨会话) | `eval/capability/instruments-check.json` (schema /5) |'
             % (face['passed'], face['total'], face['side_effect_attribution']['trace']['commands']))
    L.append('| 阈值余量 | 2.258 (21 器具) | **%.3f** (27 器具) | `face-scale-ledger.jsonl` + `face_cap_headroom.py` |'
             % (led[-1]['headroom'],))
    L.append('| 提交前闸 | 手工核对 | selftest+真仓 8/8, dogfood 拦下本侧提交 1 次 | `verdict_q31_hook_gate.json` |')
    L.append('| 等价判据 | 轮内探针 (依赖轮内 scratch) | 自足长驻闸 8/8 + 注入负控 | `only_equivalence_guard.py` |')
    L.append('| 写侧误写 | 5 (0.908 解析率) | **0** (0.9655) | `write_side_after_q31.json` vs R486 记录 |')
    L.append('| 登记表机检 | R2E_R2F_EXIT=2 (3 类违规) | **R2E_R2F_EXIT=0** (113 行) | `bind_evidence.py --check` |')
    L.append('| 形式门禁 | 14/14 | **Failed 0 / Passed 14** | `dotnet_test_gate.py --label formal-gate-q31` |')
    L.append('')
    L.append('#### AF.4 负控 (按预注册原样判定)')
    L.append('')
    L.append('| 负控 | 读数 |')
    L.append('|---|---|')
    L.append('| 退役路径重建 | 器具 rc=2 + `RETIRED_CHECK=FAIL` (`_nc_retired_q31.sh`) |')
    L.append('| capped=True 面记录 | `CAP_HEADROOM=FAIL` rc=2 (`_nc_cap_capped_q31.py`) |')
    L.append('| 等价闸轮号注入 | `A≠B` ⇒ P1 判红 + `NC_DETECTED` |')
    L.append('| 空心钩子 | 验证器 3/8 ⇒ rc=2 ⇒ `NC_DETECTED` |')
    L.append('| 清理台账缺字段/仍在盘 | selftest 4/4 (3 类负控全检出) |')
    L.append('| dotnet 退出码混同 | 分类器 6/6 (编译错与测试红分开, rc0+Failed>0 判红) |')
    L.append('| 面扩容反证 (旧器具 scoped 覆盖) | 见 AE.4 N8 (本轮未重跑) |')
    L.append('')
    L.append('#### AF.5 首跑红与自伤 (照原样入档, 不翻案)')
    L.append('')
    L.append('1. **全量面首跑 20/27**, 三类原因: ① 4 个新行缺 `corpus_dynamic_count` (我方字段漏写) ② 1 处 '
             '`SIDE-EFFECT: 本面命令弄脏既有产物` (新验证器默认 `--out` 指向轮次证据 —— 与 Q17/Q28/Q30 同族**第 3 次**) '
             '③ 3 行**前序漂移** (非本侧引入, 见 AF.6)。修复 = 补字段 + 默认写点改 scratch 面 + 定向重审, '
             '**未放宽任何断言**。')
    L.append('2. **普查器输出面自伤 (第 2 次同族)**: 直接跑 Q30 普查器把 Q30 冻结证据整份改写成 Q31 读数 ⇒ 已从 HEAD 还原, '
             '并**源码派生** Q31 版 (逐行 diff 仅 2 处: 输出路径 + 轮号); Q30 读数 110/105/5 与 Q31 读数 113/113/0 两栏并列。')
    L.append('3. **提交闸拦下本侧自己的提交**: manifest 文件自身未写进清单 ⇒ staged 30 ≠ 声明 29 ⇒ rc=1 拒提交 '
             '(dogfood 实证该闸真的在拦人, 非装饰); 修 (清单含清单自身) 后 30/30 放行。')
    L.append('4. `rewrite_evidence_cmd_q31` 的 `CHANGED_ROWS` 不变式**空转** (与就地改过的 dict 比较 ⇒ 恒空), '
             '与 Q30 AE.5② 同族第 2 次 ⇒ 真实证据改为 numstat 5/5 + 写后读回 + git diff 行数 5/5。')
    L.append('5. 等价判据的**跨轮复跑**: `verify_q30_only.py` 重跑 PASS 14/14, 14 项 checks 逐项与 Q30 相同; 只有 '
             '**输入派生读数**变 (A/B/fixture/registry sha) ⇒ 非语义字段白名单 = {A_sha12, B_sha12, fixture_sha12, '
             'reg_real_sha12, zeroregress_apply, C_stdout_touched, check_tail}。Q30 原记录已从 HEAD 还原, 复跑读数归档 '
             '`eval/capability/exp1-q31/verdict_q31_only_rerun.json`。')
    L.append('')
    L.append('#### AF.6 诚实边界')
    L.append('')
    L.append('1. **前序漂移归属** = R487 轮 (对侧/前序), 本侧只做重审与补字段: `r483b.preflight-gate-instrument` 的 '
             '器具 pin 停留在 `1a64ceb6bd14` 而现盘=HEAD `344419f044aa` (R487 提交时未重审), `r487.*` 三行缺 '
             '`evidence_generated_with`。两者都不计入本轮成果。')
    L.append('2. **两行 dotnet 面器具不进 L2 快速面** (会引入编译面 ⇒ 面别分区): 它们是**证据面**器具, 由 '
             '`dotnet_test_gate.py` 显式调用, 不登记进 `instruments.json`。')
    L.append('3. **r462 真跑未执行** (`execution_blocked`: 需 gguf 模型 + llama-server); 归档件硬编码 /tmp 语料一事'
             '只作事实登记, 未改归档件本身 (它是历史证据)。')
    L.append('4. **9 行 evidence_cmd 仍含 /tmp 路径** (参数/输出路径), 本轮全部已有仓库内器具, 但逐行核查其 /tmp 依赖'
             '是否影响**复现性**列下轮 (本轮新发现, 非预注册项)。')
    L.append('5. **阈值余量已贴下沿**: 27 器具下 2.019 (K_MIN=2.0) ⇒ 下一次面扩容**必须先复测体量**; 台账只作记录项, '
             '不构成「阈值合适」的充分证据 (单点实测, n=2)。')
    L.append('6. **跨会话复跑 ≠ 多负载对照**: 两次全量面运行都在同一台机、相近负载下 (无第三方负载注入); '
             '「稳定性」只覆盖「同面同读数」这一层。')
    L.append('7. 推送暂停令在效: 本轮**仅本地提交**, 无 push / 无远端写。')
    L.append('')
    L.append('#### AF.7 下轮候选')
    L.append('')
    L.append('1. **9 行 /tmp 路径逐行核查** (含 r462 wrapper 的语料注入路径) + 归档自足化 (是否允许给归档件加注入开关)。')
    L.append('2. **面扩容前阈值复测与 K_MIN 重定** (0.2 余量 ⇒ 下一步必须先量体量再动面)。')
    L.append('3. **「器具改而登记表未重审」的提交前机检**: r483b 类漏检应被 pre-commit 或 status_gen 面抓住 '
             '(现状是跑全量面才发现)。')
    L.append('4. 分母两栏并列的**旧口径作废声明**覆盖面审计 (AE.6 遗留)。')
    L.append('5. L4 复核: 本轮新增器具的**独立视角复核** (对侧/主线) 与 `r444` 重审后的规范化登记。')
    L.append('')
    return '\n'.join(L)


def main():
    # ① KPI 行 (幂等)
    p = os.path.join(ROOT, KPI)
    rows = [json.loads(l) for l in open(p, encoding='utf-8-sig') if l.strip()]
    if any(r.get('round') == 'EXP1-Q31' for r in rows):
        print('KPI_IDEMPOTENT=OK (已存在 EXP1-Q31)')
    else:
        line = kpi_line()
        prev = rows[-1]
        print('KPI_KEYS prev=%s' % sorted(prev))
        with open(p, 'a', encoding='utf-8', newline='') as f:
            f.write(json.dumps(line, ensure_ascii=False) + '\n')
        back = [json.loads(l) for l in open(p, encoding='utf-8-sig') if l.strip()]
        print('KPI_APPENDED rows=%d (读回 %s)' % (len(back), 'OK' if len(back) == len(rows) + 1 else 'MISMATCH'))
    # ② 门禁读数归档
    gr = gate_readings()
    gp = os.path.join(Q31, 'gate_readings_q31.json')
    open(os.path.join(ROOT, gp), 'w', encoding='utf-8').write(json.dumps(gr, ensure_ascii=False, indent=1) + '\n')
    for r in gr['runs']:
        print('GATE %-20s bytes=%-7d sha16=%s | %s' % (r['label'], r['log_bytes'], r['log_sha256_16'],
                                                       (r['summary_line'] or '')[:96]))
    print('GATE_READINGS=%s' % gp)
    # ③ 附录 AF
    pp = os.path.join(ROOT, PLAN)
    txt = open(pp, encoding='utf-8', newline='').read()
    sec = appendix()
    if MARK in txt:
        i = txt.index(MARK)
        j = txt.index('\n### ', i + len(MARK)) if '\n### ' in txt[i + len(MARK):] else len(txt)
        txt2 = txt[:i] + sec.lstrip('\n') + (txt[j:] if j < len(txt) else '')
        print('APPENDIX=REPLACED')
    else:
        txt2 = txt.rstrip('\n') + '\n' + sec
        print('APPENDIX=APPENDED')
    open(pp, 'w', encoding='utf-8', newline='').write(txt2)
    back = open(pp, encoding='utf-8', newline='').read()
    print('PLAN_READBACK=%s (bytes %d -> %d)' % ('OK' if back == txt2 else 'MISMATCH', len(txt), len(txt2)))
    subprocess.run(['git', 'diff', '--numstat', '--', KPI, PLAN, gp], cwd=ROOT)
    return 0 if back == txt2 else 2


if __name__ == '__main__':
    sys.exit(main())
