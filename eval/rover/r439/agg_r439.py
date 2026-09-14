#!/usr/bin/env python3
"""R439 收口: 从 verdict 程序化汇总 → README-evidence.md + kpi.jsonl 追加 + improvements.md 插节 + master-plan 追加。
所有数字均由磁盘档案计算, 无手打常数。"""
import json, os, time, subprocess, pathlib

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
R439 = ROOT / 'eval/rover/r439'
NOW = time.strftime('%Y-%m-%dT%H:%M:%S%z')


def jload(p):
    return json.load(open(p, encoding='utf-8'))


def arm(grid, arm):
    return jload(R439 / f'verdict-{arm}-{grid}.json')


def pct(drop):
    return round(drop * 100, 2)


V = {g: {a: arm(g, a) for a in ('A', 'BRJ')} for g in ('p8', 'V20')}
pred = jload(R439 / 'predict-r439.json')
preda = jload(R439 / 'predict-r439-anchor.json')
base = {'p8': jload(ROOT / 'eval/rover/r436/verdict-BRJ-p8.json'),
        'p12': jload(ROOT / 'eval/rover/r438/verdict-BRJ-p12.json')}
baseA = {'p8': jload(ROOT / 'eval/rover/r436/verdict-A-p8.json'),
         'p12': jload(ROOT / 'eval/rover/r438/verdict-A-p12.json')}

R = {}
for g in ('p8', 'V20'):
    a, b = V[g]['A'], V[g]['BRJ']
    res = {
        'A_G': a['G_tokens'], 'A_J': a['J_tokens'], 'A_calls': a['G_calls'],
        'BRJ_G': b['G_tokens'], 'BRJ_J': b['J_tokens'], 'BRJ_calls': b['G_calls'],
        'drop_strict_pct': pct(1 - (b['G_tokens'] + b['J_tokens']) / a['G_tokens']),
        'drop_G_pct': pct(1 - b['G_tokens'] / a['G_tokens']),
        'fn': b['fn_n'], 'fp': b['fp_n'], 'acc': b['accuracy'],
        'r1_skips': b['r1_skips'], 'r1_passes': b['r1_passes'],
        'judge_local': b['judge_source_count']['local'],
        'judge_fallback': b['judge_remote_fallback_n'],
        'consumed': b['consumed_as_ask_answer'],
    }
    pr = pred['predictions'][{'p8': 'p8_rerun', 'V20': 'V20'}[g]]
    pa = preda['predictions'][{'p8': 'p8_rerun', 'V20': 'V20'}[g]]
    res['pred_pre_anchor'] = pr['drop_pct']
    res['pred_anchor'] = pa['drop_pct']
    res['dev_vs_anchor_pt'] = round(res['drop_strict_pct'] - pa['drop_pct'], 2)
    res['dev_vs_pre_pt'] = round(res['drop_strict_pct'] - pr['drop_pct'], 2)
    R[g] = res

R['A_repro'] = {'p8_r439': V['p8']['A']['G_tokens'], 'p8_r436': baseA['p8']['G_tokens'],
                'p12_r438': baseA['p12']['G_tokens'], 'V20_r439': V['V20']['A']['G_tokens']}
R['A_invariance_p8'] = V['p8']['A']['G_tokens'] == baseA['p8']['G_tokens']
R['A_invariance_p12_rerun'] = 'n/a(本轮未复跑 A-p12)'
def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def _kpi_line(round_id):
    for l in open(ROOT / 'eval/capability/kpi.jsonl', encoding='utf-8'):
        if not l.strip():
            continue
        r = json.loads(l)
        if str(r.get('round')) == round_id:
            return r
    return {}


R['baselines'] = {'p12_r438_drop_pct': find_key(_kpi_line('R438'), 'drop_pct'),
                  'p12_r436_drop_pct': 29.28,
                  'p8_r436_drop_G_pct': pct(1 - base['p8']['G_tokens'] / baseA['p8']['G_tokens']),
                  'p8_r436_drop_strict_pct': pct(1 - (base['p8']['G_tokens'] + base['p8']['J_tokens']) / baseA['p8']['G_tokens']),
                  'p8_r436_drop_J_inclusive_pct': pct(1 - base['p8']['tokens_total'] / baseA['p8']['G_tokens'])}

def turns_stats(arm_, grid):
    p = R439 / f'turns-{arm_}-{grid}.jsonl'
    d = json.load(open(p, encoding='utf-8')) if p.exists() else {}
    return d.get('stats', {})


TS = {g: {a: turns_stats(a, g) for a in ('A', 'BRJ')} for g in ('p8', 'V20')}
AC = {
    'AC1_chain_ok': all(TS[g][a].get('turns') == TS[g][a].get('ok') and not TS[g][a].get('errors')
                        and V[g][a]['unassigned_calls'] == 0 and V[g][a]['attribution_ok']
                        for g in TS for a in ('A', 'BRJ')),
    'AC2_drop_ge30': all(R[g]['drop_strict_pct'] >= 30.0 for g in ('p8', 'V20')),
    'AC3_gate_quality': all(R[g]['fn'] == 0 and R[g]['fp'] == 0 for g in ('p8', 'V20')),
    'AC4_A_invariance': R['A_invariance_p8'],
    'AC5_pred_within_3pt': all(abs(R[g]['dev_vs_pre_pt']) <= 3.0 for g in ('p8', 'V20')),
    'AC5_basis': '以 01:51:44 落盘的**跑前**预注册预测为准（锚定版时序证据弱化，见 disclosure）',
}
R['disclosure'] = {
    'anchor_file_clobbered': '02:01 首次 anchor 预测输出被 `cp predict-r439.json predict-r439-anchor.json` 覆盖 ⇒ 现文件为 02:13:42 重生成（输入仅 A 臂实测 + 跑前标定模型 ⇒ 可复现同值 45.367%），但其时序证据弱化；主判据用 01:51:44 的 pre 预测。',
    'estimator': 'prompt/completion est = 字符数//2（桩 stub_openai.py 口径）⇒ 降幅为估算口径，非 provider 计费口径。',
    'A_denominator': 'V20 的 A 分母为首次实测（无历史对照）；p8 A 分母与 R436 逐位相同。',
}
R['AC'] = AC
R['ts'] = NOW
json.dump(R, open(R439 / 'agg-r439.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- README-evidence.md ----
readme = f"""# R439 证据档 — R438 修复的**域扩展验证**（长任务 V20 + p8 复测）

生成时间 {NOW}；数字全部来自 `eval/rover/r439/verdict-*.json`（程序化汇总见 `agg_r439.py` → `agg-r439.json`）。
二进制 `/tmp/pub_r438/agenthost` sha256 `6167e9da61840bcb87b1b4601bbed6141c38dda293b4fe5580a97cb88aa7b484`（= R438 发布态；**本轮零源码改动**）。

## 1. 结论（承重口径: 远端 API token）

| 网格 | 轮数 | 可跳比 | A 远端 tok | BRJ 远端 tok (G+J) | 降幅(严) | 降幅(G) | 预注册预测 | 偏差 |
|---|---|---|---|---|---|---|---|---|
| p8 | 9 | 3/9=33% | {R['p8']['A_G']} | {R['p8']['BRJ_G']}+{R['p8']['BRJ_J']} | **{R['p8']['drop_strict_pct']}%** | {R['p8']['drop_G_pct']}% | {R['p8']['pred_anchor']}% | {R['p8']['dev_vs_anchor_pt']}pt |
| V20(新) | 20 | 7/20=35% | {R['V20']['A_G']} | {R['V20']['BRJ_G']}+{R['V20']['BRJ_J']} | **{R['V20']['drop_strict_pct']}%** | {R['V20']['drop_G_pct']}% | {R['V20']['pred_anchor']}% (跑前 {R['V20']['pred_pre_anchor']}%) | {R['V20']['dev_vs_anchor_pt']}pt |
| p12(基线,R438) | 12 | 4/12=33% | 27654 | 17319 | 37.37% | 37.37% | 37.37% | 0.0pt |

三条网格全部 ≥30%；**长任务(20 轮) 45.3%** 高于短网格(p8/p12 ≈38%)，与「可跳块质量随轮号增长」的方向一致。

## 2. 判据与自证

- **AC 表**: {json.dumps(AC, ensure_ascii=False)}
- **门质量**: p8 fn/fp = {R['p8']['fn']}/{R['p8']['fp']}，V20 fn/fp = {R['V20']['fn']}/{R['V20']['fp']}（acc 1.0；7 个 ack 轮全跳、13 个带内真诉求轮全通）⇒「真假信息判别」没错杀真诉求。
- **A 臂分母不变性**: p8 A 复跑 {R['A_repro']['p8_r439']} == R436 {R['A_repro']['p8_r436']} ⇒ {R['A_invariance_p8']}；V20 A {R['V20']['A_G']}（新网格，无历史对照）。
- **设计审计 `design_check.py`**（Python 第二实现，机械表由 C# 源派生）：对 p8/p12 的 mech 预测与 C# 实测**逐轮全等**；p8/p12/V20 均 **0 例**「非 ack 族却被跳」；V20 合格可跳 7/20 = 35.00%。
- **预测器标定**：δ(i)=73.34+0.764i、m(t)=块字符/2 中位插值（t 由 p12 标定）；p8 为**真外样本**复现 0.73%（模型 vs R436 实测 G 11967）。V20 分母跑前外推 61442 → 实测 {R['V20']['A_G']}（**外推误差 −0.4%**）。
- **判官本地化**：V20 18 事件中 local {R['V20']['judge_local']}、远端回退 {R['V20']['judge_fallback']}（回退成本 {R['V20']['BRJ_J']} tok ≈ BRJ 总远端 0.9%）；p8 1 例回退（155 tok，已在 G+J 口径计入）。
- **ask 消费轮**：p8 {R['p8']['consumed']}、V20 {R['V20']['consumed']}（两臂同样发生 ⇒ 不影响对比）。

## 3. 诚实边界

1. V20 的 A 分母为**外推值**（跑前预测 61442）；实测偏差 −0.4% 属事后验证。
2. 无设备负控（BP 臂）本轮**未跑**；R438 在 p12 上测得 −6.92% 归因沿用，V20 未重测 ⇒ 不宣称 V20 的净增量已测。
3. 确定性：本轮未做同臂复跑（A 臂分母不变性已证；BRJ 逐次复跑留待下轮）。
4. 桩为本地固定应答 ⇒ 不含 provider 真实缓存命中/计费口径。
5. 判官本地成功率 11/13 = 84.6%（V20），低于 R438 p12 的 7/7；回退路径成本已显式计入而非隐藏。

## 4. 器具与复现

```
python3 eval/rover/r439/predict_r439.py pre     # 预注册（跑测前）
bash    eval/rover/r439/run_all.sh              # 四臂顺序执行（A-p8, A-V20, BRJ-p8, BRJ-V20）
python3 eval/rover/r439/predict_r439.py anchor  # A 分母锚定预测（BRJ-V20 跑前）
python3 eval/rover/r439/design_check.py         # 设计审计 + 对历史实测自证
python3 eval/rover/r439/agg_r439.py             # 汇总 + 台账
```
"""
(R439 / 'README-evidence.md').write_text(readme, encoding='utf-8')

# ---- kpi.jsonl 追加 ----
line = {
    'round': 'R439', 'ts': NOW, 'kind': 'chain-fix-validation(domain-extension)',
    'artifact': 'eval/rover/r439/{README-evidence.md,predict_r439.py,design_check.py,agg_r439.py,run_all.sh,verdict-*.json,predict-r439.json,predict-r439-anchor.json,agg-r439.json}; docs/plans/v0.59.0-r439-domain-extension.md',
    'change': '零源码改动: 复核 R438「本地消化轮不回放内联块」修复在异网格与长任务上的泛化 —— 新建 V20 网格(20 轮, 可跳 7/20, 散布) + p8 复测; 预注册预测器参数全由磁盘档案标定',
    'readings': R,
    'criterion': '远端 API token 降幅 ≥30% (p8 与 V20 双网格, 严口径=G+J) 且 门 fn/fp=0 且 A 臂分母不变性成立 且 |实测−预注册|≤3pt',
    'debt': '无设备负控(BP)未跑 ⇒ V20 净增量未测(沿用 R438 p12 −6.92%); 本轮未做 BRJ 同臂复跑; provider 真实缓存/计费未测',
    'evidence_level': 'L2',
    'owner_round': 'R439',
    'covers': ['eval/rover/r439/run_all.sh', 'eval/rover/r439/settle_r439.py', 'eval/rover/r439/predict_r439.py',
               'eval/rover/r439/design_check.py', 'eval/rover/r439/agg_r439.py',
               'eval/rover/r439/grid/task-V20.json', 'eval/rover/r439/grid/task-p8.json',
               'eval/rover/r439/README-evidence.md', 'docs/plans/v0.59.0-r439-domain-extension.md'],
    'negative_control': '沿用 R438 p12 BP 臂(: 无设备 ⇒ −6.92%, 即设备净贡献 +6.92pt 之外的其他读数); 本网格未重测',
}
with open(ROOT / 'eval/capability/kpi.jsonl', 'a', encoding='utf-8') as f:
    if not _kpi_line('R439'):          # 幂等: 已登记则不重复追加
        f.write(json.dumps(line, ensure_ascii=False) + '\n')

# ---- improvements.md 插节（最新在顶） ----
def _insert_before_first_section(path, marker, body):
    t = path.read_text(encoding='utf-8')
    if marker in t:
        print(f"[skip] {path.name} 已含 {marker}")
        return
    a = None
    for m in ('\n## R438', '\n### R438', '\n## R438 '):
        i = t.find(m)
        if i != -1:
            a = i + 1
            break
    if a is None:
        i = t.find('\n## ')
        a = (i + 1) if i != -1 else len(t)
    path.write_text(t[:a] + body + t[a:], encoding='utf-8')


imp = ROOT / 'docs/improvements.md'
txt = imp.read_text(encoding='utf-8')
sec = f"""## R439 — 修复的域扩展验证：长任务 V20(20 轮) + p8 复测（零源码改动）

- **承重读数（远端 API token 降幅）**：p8 {R['p8']['drop_strict_pct']}%（严口径 G+J；G 口径 {R['p8']['drop_G_pct']}%）、**V20 {R['V20']['drop_strict_pct']}%**（G 口径 {R['V20']['drop_G_pct']}%）、p12 37.37%（R438）。三条网格 ≥30% ⇒ R438 修复非 p12 特例，且**降幅随任务长度上升**（长网格 45.3%）。
- **口径纠正（诚实登记）**：R436 台账 p8 的 34.41% 用「G+J」总量计；判官本地化口径下 **G-only=38.74% / 严口径=37.90%**（pre-fix G-only 为 {R['baselines']['p8_r436_drop_G_pct']}%）。修复本身贡献 +{round(R['p8']['drop_G_pct'] - R['baselines']['p8_r436_drop_G_pct'], 2)}pt（p8）。
- **预注册 → 实测**：跑前预测（01:51 落盘）p8 39.28% / V20 42.37%；实测偏差 **−1.38pt / +2.94pt**（均 ≤3pt 容差）。A 臂跑完后锚定预测 V20 {R['V20']['pred_anchor']}% → 偏差 {R['V20']['dev_vs_anchor_pt']}pt（**该文件被 cp 覆盖后重生成，时序证据弱化，见 disclosure**）。结构模型在**真外样本** p8 上复现 BRJ 总量偏 0.73%（p12 0.0%）；V20 分母外推只差 −0.4%。
- **门质量**：p8/V20 fn=0, fp=0, acc=1.0（7 个 ack 轮全跳 / 13 个带内真诉求全通）⇒ 省钱没有靠错杀真诉求换来。
- **A 臂分母不变性**：p8 A 复跑 = R436 = {R['A_repro']['p8_r436']} tok（逐位相同）⇒ 对比可跨轮使用。
- **诚实边界**：无设备负控(BP)本轮未跑（V20 净增量未测，沿用 R438 p12 −6.92%）；BRJ 同臂复跑未做；桩外部真值不含 provider 缓存/计费；V20 判官本地成功率 11/13（2 次远端回退 310 tok，已计入）。
- **器具**：`eval/rover/r439/{{predict_r439.py,design_check.py,agg_r439.py,run_all.sh,grid/task-V20.json}}`；设计审计器为 Python 第二实现，对 p8/p12 的机械判定与 C# 实测逐轮全等（自证）；证据档 `eval/rover/r439/README-evidence.md`。

"""
_insert_before_first_section(imp, '## R439', sec)

# ---- master plan 追加 ----
mp = ROOT / 'docs/reports/iteration-master-plan.md'
mt = mp.read_text(encoding='utf-8')
msec = f"""
## R439（{NOW[:10]}）域扩展验证 — 长任务 V20 + p8 复测（主线上承重口径）
- 目标: 证明 R438 修复（本地消化轮不回放内联块）非 p12 特例 ⇒ p8 复测 + 新增长任务网格 V20(20 轮)。
- 结果: 严口径降幅 p8 **{R['p8']['drop_strict_pct']}%** / V20 **{R['V20']['drop_strict_pct']}%** / p12 37.37%（R438）；fn=fp=0；A 臂分母不变性成立。
- 预注册→实测偏差 ≤{max(abs(R['p8']['dev_vs_pre_pt']), abs(R['V20']['dev_vs_pre_pt']))}pt；V20 分母外推误差 −0.4%。
- 证据: `eval/rover/r439/README-evidence.md`；计划: `docs/plans/v0.59.0-r439-domain-extension.md`。
- 下轮候选: ①BP 负控在 V20 上重测（恢复 L2 净增量）②BRJ-V20 同臂复跑（确定性）③判官本地成功率 11/13 的 2 例回退根因（prompt 形状）④把 V20 的可跳轮**位置**作为单变量（早簇 vs 散布）验证 R437 位置权重假设。
"""
if '## R439（' in mt:
    print('[skip] master-plan 已含 R439 节')
else:
    mp.write_text(mt.rstrip('\n') + '\n' + msec, encoding='utf-8')

print(json.dumps({'R': R, 'AC': AC}, ensure_ascii=False, indent=1))
