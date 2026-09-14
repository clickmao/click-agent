#!/usr/bin/env python3
"""R440b 预注册 — **V2b（短任务格, 冗余认可轮）** 的**分支预测**。

起因（仪器自捕, 非事后编故事）: V2（N=3, 认可轮在 t2）实测 −3.86% ⇒ 读逐轮发现 t2 被**产品澄清问句吞并**
(`consumed_as_ask_answer=True`, 0.0s/reply_len=170) ⇒ 门根本没机会判它 ⇒ 该格**未测到**目标变量。
本轮修法 = 目标轮**冗余布置**（4 轮里放 2 个认可轮）+ **跑前**声明所有可能 realization 的预测。

参数**程序化取自** `predict-r440-pre.json`（不得手打）; A 分母为 p8 逐轮实测的下标代理（与 V1/V2 同法）。
"""
import json
import pathlib
import subprocess

OUT = pathlib.Path('/home/agentuser/AgentFramework/eval/rover/r440')
PRE = json.load(open(OUT / 'predict-r440-pre.json', encoding='utf-8'))
DELTA = PRE['model']['delta_role_offset']
A_P8 = {int(k): v for k, v in PRE['model']['A_measured_per_turn']['p8'].items()}


def A(i):
    """p8 逐轮实测的下标代理; 缺下标 ⇒ 用 p8 末点（保守, 记 src）"""
    if i in A_P8:
        return A_P8[i], 'measured'
    return A_P8[max(A_P8)], 'extrapolated'


def delta(i):
    return DELTA['d0'] + DELTA['d1'] * i


def predict(skips, consumed):
    """consumed=被澄清问句吞并的轮（既不跳也不远端）; 其余轮正常远端。"""
    calls = [i for i in range(1, 5) if i not in skips and i not in consumed]
    a_tot = sum(A(i)[0] for i in calls)
    brj = sum(A(i)[0] + delta(i) for i in calls)
    return {'realized_S': sorted(skips), 'consumed': sorted(consumed), 'calls': calls,
            'A_total_proxy': round(a_tot, 1), 'BRJ_total': round(brj, 1),
            'pred_drop_pct': round(100 * (1 - brj / a_tot), 4)}


branches = {
    'B1_no_consumption': predict([2, 4], []),
    'B2a_t2_eaten': predict([4], [2]),
    'B2b_t4_eaten': predict([2], [4]),
    'B3_both_acks_eaten': predict([], [2, 4]),
    'B4_real_t3_eaten': predict([2, 4], [3]),
}
out = {
    'round': 'R440b', 'kind': 'pre_registered_prediction_branching', 'ts': subprocess.run(['date', '-Iseconds'], capture_output=True, text=True).stdout.strip(),
    'grid': 'V2b (N=4, 认可轮 t2 与 t4 ⇒ 冗余布置)',
    'selector': '实测 realized 配置（由 verdict 逐轮 r1_skips/consumed_as_ask_answer 给出）选定唯一分支; 判据 = |实测降幅 − 该分支预测| ≤ 3.0 pt',
    'branches': branches,
    'tolerance_pt': 3.0,
    'falsification': '无论落在哪个分支, |实测 − 该分支预测| > 3.0 pt ⇒ 短档模型失效, 须重标定并披露。',
    'design_defect_lesson': '目标轮必须冗余布置: 产品澄清问句会吞并任意后续轮（实测于 V2 t2 / V4 t3,t11 / V5 t3 / V20 t4）⇒ 单点目标格会得到「未测到」而非「测到失败」。',
    'source_params': 'predict-r440-pre.json:model.delta_role_offset / model.A_measured_per_turn.p8',
}
json.dump(out, open(OUT / 'predict-r440b-pre.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
for k, v in branches.items():
    print(f'  {k}: S={v["realized_S"]} consumed={v["consumed"]} calls={v["calls"]} A_proxy={v["A_total_proxy"]} BRJ={v["BRJ_total"]} drop={v["pred_drop_pct"]}%')
print('wrote', OUT / 'predict-r440b-pre.json')
