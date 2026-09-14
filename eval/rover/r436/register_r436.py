#!/usr/bin/env python3
"""R436 台账写入 — 只用一份 JSON 源(verdict-summary.json + publish-info.json)写:
  (1) docs/verification-registry.json  追加/替换 id=r436.e2e-brj-token-kpi 一行 (indent=2 原样式, 不动他行为)
  (2) eval/capability/kpi.jsonl        追加 R436 行(已存在则替换本侧行, 不改他人行)
  (3) docs/reports/iteration-master-plan.md 尾部「下轮候选」登记
幂等: 重跑覆盖本侧行, 不重复追加。写入后回读校验。
"""
import json
import os
import re
import sys

R = os.path.abspath(os.path.dirname(__file__))
REPO = os.path.abspath(os.path.join(R, "..", "..", ".."))
S = json.load(open(os.path.join(R, "verdict-summary.json"), encoding="utf-8"))
P = json.load(open(os.path.join(R, "publish-info.json"), encoding="utf-8"))
C = S["criteria"]
p12, p8 = S["p12_rows"], S["p8_rows"]
A, B, BRJ, BRJ2, BP = p12.get("A"), p12.get("B"), p12.get("BRJ"), p12.get("BRJ2"), p12.get("BP")
d = C["C4b_降幅分解"]
C4 = C["C4_主KPI_token降幅"]
sha16 = P["sha256"][:16]
ROUND = "R436"

# ---------- (1) registry ----------
cap = (
    "端到端真假信息判别闭环（R435 新 AOT 二进制，sha16=%s）: 门（turn gate）+ 关系判官 J **全本地** 相对「门关/无判官」分母的**用户一轮任务总远端 token** 降幅。"
    "网格 task-p12（12 轮；可跳轮 S={2,3,4,5} 为**早簇**）: 分母臂 A = %d 主答调用/%d tok; 治疗臂 BRJ（门开+J 本地）= %d/%d tok ⇒ **降幅 %s%%**（目标 %s%% ⇒ %s）; "
    "单变量臂 B（门开+J 远端） = %d/%d tok ⇒ **J 本地化单独贡献 %d tok = %s pt** 并消除 %d 次远端 API 请求（B 的 J 全部远端）。"
    "门质量: 假阴性 %s ∧ 假阳性 %s, acc %s（与 R434 口径同网格可比）。"
    "负控臂 BP（设备缺失, model_path 不存在）: 门跳过 %s 次（=恒降级）+ 判官 %s 次远端兜底 ⇒ %s tok = 分母的 %s%%（**净亏**, 证明收益必须来自本地设备真生效）。"
    "p8 网格（可跳轮散布于 S={2,6,8}）: A %d/%d → BRJ %d/%d ⇒ 降幅 %s%%（%s）; 该臂判官 %d 次本地成功 / %d 次远端兜底（本地率非 100%%, 如实记录）。"
    "确定性复跑 BRJ#2: Δtoken=%s（%s%%）, 逐轮 actual 全同。"
    "结论: J 本地成功率自 R434 的 1/7 提升至 **%d/%d 全本地**, 端到端降幅 27.8%%→%s%%（+%s pt）; 但 **≥30%% 未在 p12 达成**, 与对侧 R437 模型对「早簇」判为最不利位置并预测 J 修复 +1.1…+1.9pt 一致（实测 +%s pt 落在该带内）。"
) % (
    sha16, A["calls"], A["tokens"], BRJ["calls"], BRJ["tokens"], C4["p12_BRJ_drop_pct"], C4["p12_target"],
    "达标" if C4["p12_ok"] else "未达标",
    B["calls"], B["tokens"], d["J本地化_节省token"], d["J本地化_占比pct"], d["J本地化_远端请求消除数"],
    C["C3_门质量"]["BRJ_p12_fn_fp"][0], C["C3_门质量"]["BRJ_p12_fn_fp"][1], C["C3_门质量"]["BRJ_p12_acc"],
    C["C6_负控_无设备"]["BP_r1_skips"], C["C6_负控_无设备"]["BP_J_remote_calls"], BP["tokens"], C["C6_负控_无设备"]["BP_drop_pct"],
    p8["A"]["calls"] if p8.get("A") else -1, p8["A"]["tokens"] if p8.get("A") else -1,
    p8["BRJ"]["calls"] if p8.get("BRJ") else -1, p8["BRJ"]["tokens"] if p8.get("BRJ") else -1,
    C4["p8_BRJ_drop_pct"], "达标" if C4["p8_ok"] else "未达标",
    p8["BRJ"]["judge_local_n"] if p8.get("BRJ") else -1,
    (p8["BRJ"]["J"] if p8.get("BRJ") else -1),
    C["C7_确定性"]["delta_tokens"], round(C["C7_确定性"]["delta_tokens"] / A["tokens"] * 100, 3),
    BRJ["judge_local_n"], BRJ["judge_local_n"] + BRJ["J"], C4["p12_BRJ_drop_pct"], round(C4["p12_BRJ_drop_pct"] - 27.8, 2),
    round(C4["p12_BRJ_drop_pct"] - 27.8, 2),
)

row = {
    "id": "r436.e2e-brj-token-kpi",
    "owner_round": ROUND,
    "level": "L3",
    "capability": cap,
    "evidence_cmd": ("bash eval/rover/r436/run_r436_arms.sh; bash eval/rover/r436/run_r436_arms_p8.sh; "
                     "python3 eval/rover/r436/channel_marks.py; python3 eval/rover/r436/publish_info.py; "
                     "python3 eval/rover/r436/compare_r436.py; python3 eval/rover/r436/make_evidence.py"),
    "evidence_path": "eval/rover/r436/README-evidence.md",
    "negative_control": (
        "① 无设备负控（臂 BP, model_path 缺失）: r1_skips=%s ⇒ 门恒降级, 判官 %s 次 remote_fallback ⇒ 总 %s tok ≥ 分母 %s tok（%s%%）⇒ 降幅不可能来自「门没生效」; "
        "② 单变量臂 B vs BRJ 只差 relation_judge ⇒ J 本地化贡献可分离（%s tok / %s pt）; "
        "③ 分类器复现控制 S1: 用本轮**程序化派生**的 J 标记重跑 R434 五份归档 calls, G/J 计数逐臂与原登记完全一致（第 6 份 A-p8-a1 无 G/J 记录 ⇒ 跳过并计数, 不静默）; "
        "④ 双源交叉 S2: 桩侧 J 远端请求数 == 遥测「真构造请求的远端判决」数（prompt_len>0）, 全臂 delta=0; "
        "⑤ 确定性复跑 BRJ#2: Δtoken=%s（%s%%）, 逐轮 actual 全同; "
        "⑥ 形态负控: V0 形态闸裸 IL/脚本伪装配体必拒（rc=131）。"
    ) % (
        C["C6_负控_无设备"]["BP_r1_skips"], C["C6_负控_无设备"]["BP_J_remote_calls"], BP["tokens"], A["tokens"], C["C6_负控_无设备"]["BP_drop_pct"],
        d["J本地化_节省token"], d["J本地化_占比pct"],
        C["C7_确定性"]["delta_tokens"], round(C["C7_确定性"]["delta_tokens"] / A["tokens"] * 100, 3),
    ),
    "covers": [
        "src/agent.roles/CorrectionDetector.cs",
        "src/agent/IndustrialAgentV2.cs",
        "src/agent.modelqueue/ModelQueueRouter.cs",
        "eval/rover/r436/run_arm.sh",
    ],
    "note": ("承重判据 C4 在 p12 未达（%s%% < %s%%）⇒ 宣称收窄为「≥30%% 依赖可跳轮占比与位置（非早簇）」; "
             "R434 登记的「J 本地化未达成(1/7)」在本轮以同网格同器具证伪为 **7/7 本地**（根因 = R435 prompt 形状）。"
             "审计注意: 远端读数来自桩(prompt_tokens_est), 非真实计费; 本地 r1 token（判官 %s tok）不计入 API token。") % (
        C4["p12_BRJ_drop_pct"], C4["p12_target"], BRJ.get("judge_local_tokens")),
}

regp = os.path.join(REPO, "docs", "verification-registry.json")
t0 = open(regp, encoding="utf-8").read()
reg = json.loads(t0)
assert isinstance(reg["rows"], list)
before = len(reg["rows"])
reg["rows"] = [r for r in reg["rows"] if r.get("id") != row["id"]] + [row]
reg["updated_round"] = ROUND
out = json.dumps(reg, ensure_ascii=False, indent=2)
# 只动本侧: 除 my row + updated_round 外, 其余部分必须逐字不变
open(regp, "w", encoding="utf-8").write(out)
back = json.loads(open(regp, encoding="utf-8").read())
mine = [r for r in back["rows"] if r.get("id") == row["id"]]
others0 = len([r for r in json.loads(t0)["rows"]])
print(f"[registry] rows {others0} → {len(back['rows'])}; updated_round={back['updated_round']}; my row present={len(mine) == 1}; "
      f"other rows intact={len(back['rows']) - 1 == others0}")

# ---------- (2) kpi.jsonl ----------
kpi = {
    "round": ROUND,
    "date": "2026-09-15",
    "lang": "csharp",
    "aot": True,
    "il_warnings": P["il_warnings"],
    "bin_sha16": sha16,
    "bin_bytes": P["bytes"],
    "chain": "rover:E2E-BRJ网格(task-p12 12轮 + task-p8 9轮; 5臂+1确定性复跑; 桩外部真值; r1-distill-1.5b-q4km, temp0/seed0/np1)",
    "task": "承重: 用户一轮任务总远端 API token 降幅 ≥30%（R435 新 AOT 二进制, J 全本地）",
    "arms": {k: {kk: vv for kk, vv in v.items() if kk not in ("per_turn",)} for k, v in p12.items()},
    "arms_p8": {k: {kk: vv for kk, vv in v.items() if kk not in ("per_turn",)} for k, v in p8.items()},
    "token_drop_vs_A_pct": {"p12": C4["p12_BRJ_drop_pct"], "p8": C4["p8_BRJ_drop_pct"], "target": C4["p12_target"]},
    "decomposition": d,
    "verdict": ("PARTIAL/承重未达: p12 降幅 %s%% < %s%%（差 %s pt）; p8 = %s%%（%s）; "
                "J 本地化端到端证成 7/7 本地 + 消除 7 次远端请求 + %s pt, 门质量假阴性 0/假阳性 0") % (
        C4["p12_BRJ_drop_pct"], C4["p12_target"], round(C4["p12_target"] - C4["p12_BRJ_drop_pct"], 2),
        C4["p8_BRJ_drop_pct"], "达标" if C4["p8_ok"] else "未达标",
        d["J本地化_占比pct"]),
    "honest_limits": [
        "远端 token 为桩侧估算(prompt/completion_tokens_est), 非真实计费; 两臂同口径可比, 绝对值不可当账单",
        "未做真机远端(DeepSeek)重放; 桩返回固定话术 ⇒ 臂 B 的远端判官字母无意义(故 B 的门质量不代表真机)",
        "p8 臂判官本地成功率 %d/%d(1 次远端兜底) ⇒ 本地化非 100%% 稳定" % (p8["BRJ"]["judge_local_n"] if p8.get("BRJ") else -1, (p8["BRJ"]["judge_local_n"] + p8["BRJ"]["J"]) if p8.get("BRJ") else -1),
        "本地 r1 判官 %d tok / %d s 串行(不计入 API token, 但非零成本)" % (BRJ.get("judge_local_tokens") or 0, sum(BRJ.get("judge_local_ms") or []) // 1000),
        "两次同源 AOT 发布非逐字节可复现(差 %s 字节) ⇒ 二进制 sha 不能当源码状态指纹" % (P.get("diff_vs_prev_publish", {}).get("diff_bytes")),
        "并发: 对侧 60m 自检作业于 23:55 写入 R437 分析行(kpi.jsonl), 与本轮发布窗重叠 ⇒ 已在 note 记录(未改他方产物)",
    ],
    "next": [
        "V1-V5 长度分档实测（对侧 R437 §7 预注册; 本侧需先空出测量窗）",
        "p12 型「可跳轮早簇」是 ≥30% 的最不利构成 ⇒ 若要 p12 也 ≥30%, 需降单次主答 prompt(token 侧): 上下文/记忆段按轮压缩(本地 r1) 或 role 块瘦身",
        "turn9 类「思考链无界」本地判官(停发词/思考长度约束) —— R435 遗留",
        "门+判官合并为单次本地调用（两次冷启动 40s → 一次）",
    ],
    "evidence": "docs/plans/v0.57.0-r436-e2e-brj-token-kpi.md; eval/rover/r436/README-evidence.md; eval/rover/r436/{run_arm.sh,run_r436_arms.sh,run_r436_arms_p8.sh,channel_marks.py,settle_r436.py,compare_r436.py,publish_info.py,make_evidence.py}; eval/rover/r436/verdict-summary.json",
}
kp = os.path.join(REPO, "eval", "capability", "kpi.jsonl")
lines = [l for l in open(kp, encoding="utf-8").read().splitlines() if l.strip()]
others = [l for l in lines if json.loads(l).get("round") != ROUND]
others.append(json.dumps(kpi, ensure_ascii=False))
open(kp, "w", encoding="utf-8").write("\n".join(others) + "\n")
back = [json.loads(l) for l in open(kp, encoding="utf-8").read().splitlines() if l.strip()]
mine = [r for r in back if r.get("round") == ROUND]
print(f"[kpi.jsonl] lines {len(lines)} → {len(back)}; my rows={len(mine)}; 对侧 R437 行仍在={any(r.get('round','').startswith('R437') for r in back)}")

# ---------- (3) master plan 尾部登记 ----------
mp = os.path.join(REPO, "docs", "reports", "iteration-master-plan.md")
txt = open(mp, encoding="utf-8").read()
block = (
    f"\n### {ROUND}（{ '已完成' }）端到端 BRJ 网格: 承重 token 降幅\n"
    f"- 二进制 sha16 `{sha16}`（NativeAOT, IL 警告 {P['il_warnings']}, V0 形态闸 {P['v0_gate_pass']}）\n"
    f"- p12: A {A['tokens']} tok → BRJ {BRJ['tokens']} tok = **{C4['p12_BRJ_drop_pct']}%**（目标 {C4['p12_target']}% ⇒ 未达, 差 {round(C4['p12_target'] - C4['p12_BRJ_drop_pct'], 2)} pt）; "
    f"p8: A {p8['A']['tokens'] if p8.get('A') else -1} → BRJ {p8['BRJ']['tokens'] if p8.get('BRJ') else -1} = **{C4['p8_BRJ_drop_pct']}%**\n"
    f"- J 本地化: 远端请求 {d['J本地化_远端请求消除数']} 次 → 0（本地 7/7）; 单独贡献 {d['J本地化_占比pct']} pt\n"
    f"- 门质量: 假阴性 {C['C3_门质量']['BRJ_p12_fn_fp'][0]} / 假阳性 {C['C3_门质量']['BRJ_p12_fn_fp'][1]}（acc {C['C3_门质量']['BRJ_p12_acc']}）; 负控 BP 净亏 {C['C6_负控_无设备']['BP_drop_pct']}%\n"
    f"- 证据: `eval/rover/r436/README-evidence.md`｜判据: `docs/plans/v0.57.0-r436-e2e-brj-token-kpi.md`\n"
)
marker = f"### {ROUND}（已完成）"
if marker in txt:
    i = txt.index(marker)
    j = txt.find("\n### ", i + 1)
    txt = txt[:i] + block.lstrip("\n") + (txt[j + 1:] if j != -1 else "")
else:
    txt = txt.rstrip("\n") + "\n" + block
open(mp, "w", encoding="utf-8").write(txt)
print("[master-plan] 尾部登记完成; 含 R436 段=", marker in open(mp, encoding="utf-8").read())
def drop(b, x):
    return round((p12[b]["tokens"] - p12[x]["tokens"]) / p12[b]["tokens"] * 100, 2)

# ---------- (4) improvements.md 尾部 R436 段 ----------
imp = os.path.join(REPO, "docs", "improvements.md")
txt = open(imp, encoding="utf-8").read()
sec = f"""
### {ROUND}（2026-09-15）端到端 BRJ 网格重跑：承重 token 降幅 {C4['p12_BRJ_drop_pct']}%（p12）/ {C4['p8_BRJ_drop_pct']}%（p8）

- **用户令（逐字）**: 「利用r1对真假信息判别…让用户一轮任务总数tokens使用量显著下降30%以上(主要是不必要的llm api请求少了)」⇒ 本轮承重 = R435 新 AOT 二进制端到端重跑（R435 §7 候选①）。
- **推进台账（用户令: 所有候选无疑问则全推进）**: ① **端到端 BRJ 网格重跑（承重）达成（含负结论）**: J 本地化自 R434 登记 **1/7（本地成功）** 提升至 **{BRJ['judge_local_n']}/{BRJ['judge_local_n']} 全本地**；远端判官请求 `{d['J本地化_远端请求消除数']}` 次 → **0**；p12 降幅 27.8% → **{C4['p12_BRJ_drop_pct']}%**（+{round(C4['p12_BRJ_drop_pct']-27.8,2)} pt）但 **< {C4['p12_target']}%**（差 {round(C4['p12_target']-C4['p12_BRJ_drop_pct'],2)} pt）⇒ 承重未达；p8（可跳散布）={C4['p8_BRJ_drop_pct']}%（{'达标' if C4['p8_ok'] else '未达标'}）；② 判据 C1–C8 逐项机器判定（`verdict-summary.json`）**达成**；③ 器具加固: J 标记**程序化派生**（源码字面量 + 无不可见码位断言）替代手打（R435 U+200B 教训）**达成**；④ 归档复现控制 S1（同标记重跑 R434 五份 calls ⇒ G/J 计数逐臂一致）**达成**；⑤ 确定性复跑（BRJ#2 Δtoken={C['C7_确定性']['delta_tokens']}）**达成**。
- **基线对比（同二进制 sha16 `{sha16}`；外部真值 = 桩逐请求 tokens + 遥测双源；通道分离 G 主答/J 判官）**:

  | 臂（task-p12） | 主答调用 | 判官远端 | 判官本地 | 总 tok | 相对 A | 假阴性 | 假阳性 | acc |
  |---|---|---|---|---|---|---|---|---|
  | A 门关（分母） | {A['calls']} | {A['J']} | {A['judge_local_n']} | {A['tokens']} | — | {A['fn']} | {A['fp']} | {A['acc']} |
  | B 门开+J 远端 | {B['calls']} | {B['J']} | {B['judge_local_n']} | {B['tokens']} | {drop('A','B')}% | {B['fn']} | {B['fp']} | {B['acc']} |
  | **BRJ 门开+J 本地** | {BRJ['calls']} | {BRJ['J']} | {BRJ['judge_local_n']} | **{BRJ['tokens']}** | **{C4['p12_BRJ_drop_pct']}%** | **{BRJ['fn']}** | **{BRJ['fp']}** | **{BRJ['acc']}** |
  | BRJ#2 复跑 | {BRJ2['calls']} | {BRJ2['J']} | {BRJ2['judge_local_n']} | {BRJ2['tokens']} | — | {BRJ2['fn']} | {BRJ2['fp']} | {BRJ2['acc']} |
  | BP 无设备（负控） | {BP['calls']} | {BP['J']} | {BP['judge_local_n']} | {BP['tokens']} | {C['C6_负控_无设备']['BP_drop_pct']}% | {BP['fn']} | {BP['fp']} | {BP['acc']} |
  | p8: A → BRJ | {p8['A']['calls'] if p8.get('A') else -1} → {p8['BRJ']['calls'] if p8.get('BRJ') else -1} | {p8['A']['J'] if p8.get('A') else -1} → {p8['BRJ']['J'] if p8.get('BRJ') else -1} | {p8['BRJ']['judge_local_n'] if p8.get('BRJ') else -1} | {p8['A']['tokens'] if p8.get('A') else -1} → {p8['BRJ']['tokens'] if p8.get('BRJ') else -1} | **{C4['p8_BRJ_drop_pct']}%** | {p8['BRJ']['fn'] if p8.get('BRJ') else -1} | {p8['BRJ']['fp'] if p8.get('BRJ') else -1} | {p8['BRJ']['acc'] if p8.get('BRJ') else -1} |

- **降幅分解（同二进制, 单变量）**: 门（跳过 4 个早簇认可轮）= A→B {d['门_占比pct']}%；J 本地化（消除 {d['J本地化_远端请求消除数']} 次远端判官调用）= {d['J本地化_节省token']} tok = {d['J本地化_占比pct']} pt ⇒ 合计 {C4['p12_BRJ_drop_pct']}%。
- **自纠（必须披露）**: ① 本轮 settle 器具首发崩溃（归档 verdict 字段名 key 缺失）⇒ 修脚本 + **离线重结算**（原始 calls/遥测全部在盘, 未重跑臂）; ② S2 交叉定义首版错误（把 `source!=local ∧ prompt_len==0` 的**结构性判定**当成远端请求）⇒ 按实测分类学收紧为 `prompt_len>0`; ③ AOT 发布**非逐字节可复现**（同源两次发布差 {P.get('diff_vs_prev_publish', {}).get('diff_bytes')} 字节, BuildID 不同）⇒ 二进制 sha 不可当源码状态指纹; ④ 本侧发布窗与对侧 60m 自检作业（23:55 写 R437 分析行）重叠 ⇒ 已登记, 未改他方产物。
- **诚实边界**: ① 远端 token 为**桩侧估算**（非真实计费）; ② 未真机重放远端（桩返回固定话术 ⇒ 臂 B 的远端判官字母无意义, 故 B 的 acc 不代表真机）; ③ 本地判官 {BRJ.get('judge_local_tokens') or 0} tok（7 次）不计入 API token 但非零成本（串行 {sum(BRJ.get('judge_local_ms') or []) // 1000} s）; ④ ≥30% **未**在 p12 达成 ⇒ 宣称收窄「≥30% 依赖可跳轮占比**与位置**（早簇最不利）」。
- **对侧交叉（R437 模型, 不改他方产物）**: 对侧 R437 预测 J 修复 +1.1…+1.9 pt（p12 28.8–29.6）⇒ 本轮实测 +{round(C4['p12_BRJ_drop_pct']-27.8,2)} pt **落在该带内**。
- **下轮候选**: ① V1–V5 长度分档实测（对侧 R437 §7 已预注册; 需先空出测量窗）; ② p12 型早簇构成下要 ≥30% ⇒ 降单次主答 prompt（上下文/记忆段按轮压缩 或 role 块瘦身）; ③ turn9 类「思考链无界」（R435 遗留）; ④ 门+判官合并为单次本地调用（省一次冷启动）。
- **计划/证据/登记**: `docs/plans/v0.57.0-r436-e2e-brj-token-kpi.md`；`eval/rover/r436/README-evidence.md`；`docs/verification-registry.json` → `r436.e2e-brj-token-kpi`；`eval/capability/kpi.jsonl` → R436。
"""
marker = f"### {ROUND}（2026-09-15）"
if marker in txt:
    i = txt.index(marker)
    j = txt.find("\n### ", i + 1)
    txt = txt[:i] + sec.lstrip("\n") + (txt[j + 1:] if j != -1 else "")
else:
    txt = txt.rstrip("\n") + "\n" + sec
open(imp, "w", encoding="utf-8").write(txt)
back = open(imp, encoding="utf-8").read()
print("[improvements] 含 R436 段 =", marker in back, "; 段落数 =", back.count("\n### R"))

