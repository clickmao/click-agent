#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R622 收口写盘：文献台账追加（§19）+ KPI 行追加 + 验证登记表追加。

纪律（承 shared-artifact-integrity / R409）：
  - 台账用 `io.open(path,'a')` **追加**，禁整档回写；写后 `tail` + `wc -l` 复核。
  - 登记表改写前先断言「序列化器逐字节复现原文件」；不成立则改用**文本插入**（锚点处字符串拼接），
    绝不静默重排整份文件；写后读回校验（字面转义 / 逗号 / 缩进）。
"""
from __future__ import annotations
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
LEDGER = os.path.join(REPO, "docs/research/lit-review-ledger.md")
KPI = os.path.join(REPO, "eval/capability/kpi.jsonl")
REG = os.path.join(REPO, "docs/verification-registry.json")

LEDGER_BLOCK = """
## 19. R622 文献小步（2026-09-21；检索面 = 「impartial 组合博弈的胜负态刻画 / 判定」；预算 = 4 query / 1 摘要取件，未开子 agent）

### 19.1 检索（超上限 1 式，如实登记原因）
- 前三式（`"self-verification" program artifact LLM agent` / `"Nim" "game" theory LLM reasoning benchmark` / `"P-position" combinatorial game language model`）的**输出在本次上下文压缩中丢失** ⇒ 无法取证；按新检索计入 ⇒ 本轮累计 **4 式 > 3 上限**。纪律动作：该超额如实登记，不假装在预算内。
- 其间观测到**检索退化**（另计入 §19.2 不采信行）：引号短语被拆散 ⇒ 结果数虚高（179,869 / 1,046,258 / 1,323,028）、返回「当日最新」而非相关件。
- 有效式（1 条，命中相关件）：`impartial combinatorial game solver verifier agent`（cs.GT / math.CO 混排，max 6）⇒ 取件第 5 条。

### 19.2 台账（8 列，本轮追加 2 行）

| 日期 | 检索式 | 出处（含版本/取件） | 逐字引文（≤2 句） | 机制假设 | 改哪一格 KPI（预期方向） | 单变量轴 + 判据（阈值/可证伪点） | 状态 |
|---|---|---|---|---|---|---|---|
| 2026-09-21 | `impartial combinatorial game solver verifier agent`（max 6；命中 225,679 ⇒ 短语未收紧，逐条读标题/摘要筛） | arXiv **2606.25276v1**（cs.GT，2026-06-24）· comment = `19 pages, 1 table, 3 algorithms` · journal-ref = **N/A** ⇒ **纯预印本（权威代理最低档）**；近月预印本 cited_by_count 不可用（Semantic Scholar 无 key ⇒ 429）· 采集日 2026-09-21 | `We also show that deciding whether an LIA formula exactly characterizes the set of winning, losing, or draw states of an LIA-definable ICG is undecidable in general and decidable for terminating LIA-definable ICGs.` | 「某公式是否**恰好刻画**胜负态集合」在一般情形**不可判**、在**终止**情形可判 ⇒ 用谓词判 P 位必须先固定**终止性前提**（着法严格降序）并给**可判定的刻画校验**，否则谓词错没有上界保证 | ② 质量（族分列通过率 ↑） | 轴 = **该族判定位实现**（模型/学习谓词 → 构造性可判定过程：枚举 DP / SG 表 + 终止性前提显式化）；判据 = wythoff 用例级通过率 **0.585 → ≥0.80** ∧ `COLD_PRED_WRONG` 占比 **≥71% → ≤10%**；可证伪点 = 提升 **<10pt** 即机制假设证伪。**本仓现状代码证据**：`src/agent/r1/ArtifactCarryover.cs:9-19`（R600 修复环「带现状」）+ 同行注释 `产品默认档失败例次 100% 集中 wythoff 族，主桶 = 冷集构造层`；R622 实测把该桶**量化**到判定层 90.6%（`eval/rover/r622/verdict-r622.json`）⇒ 「有代码行 ≠ 生效」已由真机读数背书，但**机制未被替换**（谓词仍由模型产出） | **候选（L4 采信为机制假设，未实施）** |
| 2026-09-21 | `"self-verification" program artifact LLM agent`（cs.CL, sort=date, max 5）等三式 | **未取到原文 ⇒ 不采信**（结果数 179,869 / 1,046,258 / 1,323,028 = 引号短语被拆散信号；返回件为「Designer-RSI / CodeMidas / MintAct / 中子星」等当日最新，非本面机制） | — | — | — | — | 不采纳 |

### 19.3 连续 0 采信计数
- 本轮采信 1 条（L4，纯预印本、**仅机制假设**）⇒ 反空转计数归零，**检索不降频**（仍每轮一次）。
- 「引号短语退化」为**工具面**问题（非检索面零结果）⇒ 下轮改 `ti:`/`abs:` 前缀 + 复测同式，并把「结果数」继续当**非判据**。
"""

KPI_ROW = {
    "round": "R622",
    "ts": None,  # 由脚本填真实时钟
    "kind": "RF0004.2 · M3 **承重缺口定因轮（只读）**：R621 定位「wythoff 族 = 承重缺口（T 223/270 · C 158/270 · 真值 45/45）」后，本轮按 skill「逐例归因」节做**独立 oracle 复算 + 四分归因 + 行为式机制归因**。零产品源码改动 / 零新臂 / 零远端调用 / 零新增夹具语义（oracle 与被测零共享代码，来源 = 冻结题面逐字规格）。读数：J0 oracle 正控 15/15 · J1 变异负控（v2 逐例对应 mismatch 0/45；**v1 判据首跑即证伪，原样入档不翻案**）· J2 复算 == R621 冻结裁决（期望从 `verdict-r621.json` **派生**，非写死）· J3 四分覆盖 100% · J4 目标子型 71.1% ≥50% · J5 真值 45/45 全对（非夹具缺陷、非两侧同败）。机制：**判定层 = 113(COLD_PRED_WRONG) + 31(CRASH 同源) = 144/159 = 90.6%**；选点层 9、枚举序 2、未分类 4。CRASH 有代码级证据（`games/wythoff.py:48` `i, j = best` 上 `TypeError`：谓词全否 ⇒ `best=None` ⇒ 未自验即交付）。rc=0（仅表本轮判据全绿）。",
    "change": "产品侧改动 = **零**（只读复算 R621 冻结快照；未改 src/、未加臂、未调远端）。器具面新增 5 件（`wythoff_oracle.py` 独立 oracle / `attrib_r622.py` 四分 / `mech_r622.py` 机制 / `aux_r622.py` 副读数 / `closeout_r622.py` 机械裁决）+ 预注册（跑前落盘）+ DAG；**未改判定器/夹具语义**，冻结件逐字节未动。",
    "readings": {
        "arms_recomputed": "39 跑次（T×18 / C×18 / C1×3；窗集 w217..w219，与历史不相交）",
        "quality_wythoff_family": {"T": "223/270 (0.8259)", "C": "158/270 (0.5852)", "C1": "45/45 (1.0)"},
        "per_window": {"w217": {"T": "90/90", "C": "50/90"}, "w218": {"T": "78/90", "C": "68/90"},
                       "w219": {"T": "55/90", "C": "40/90"}},
        "four_way": {"TRUE_WRONG": 74, "STATE_FLIP": 52, "HARD_CRASH": 31, "LEGAL_NONMIN": 2, "FORMAT": 0},
        "mechanism_tally": {"COLD_PRED_WRONG": 113, "CRASH": 31, "ILLEGAL_MOVE": 9,
                            "UNCLASSIFIED": 4, "ENUM_ORDER": 2},
        "judgment_family_share": 0.9057,
        "cost_decomp_posthoc": {"new_prompt_T": 29871, "new_prompt_C": 28939, "net_delta_C_minus_T": -932,
                                "abs_sum": 10952, "top1_share": 0.1402, "concentrated": False,
                                "verdict": "NO_CONCENTRATED_SOURCE"},
        "determinism": {"percase_sha256_twice": "344ffa227f07c108…", "identical": True,
                        "run_wall_s": 13.1},
        "crash_repro": {"rc": 1, "stdout_empty": True, "site": "games/wythoff.py:48",
                        "line": "i, j = best", "error": "TypeError: cannot unpack non-iterable NoneType"},
        "fixture_census_posthoc": {"always_lose_correct": "4/15", "max_win_correct": "12/15",
                                   "min_subtype_exercised": "3/15"},
        "precond_rc": "本轮未跑（零新臂 ⇒ 无新落盘摘要可验收）；沿用 R621 的 rc=1 ⇒ 质量/成本面仍「参考（未可验收）」",
    },
    "baselines": ["F_env.gate.prev_swing_mb", "F_env.gate.ceiling_mb", "F_merge.quality.cases_median_truth",
                  "F_merge.quality.allpass", "F_orch.cost.calls_sum", "F_merge.cost.new_prompt_sum",
                  "F_merge.cache.hit_v_all", "F_merge.gate.precondition_rc", "F_orch.wythoff.pass_r606",
                  "F_orch.wythoff.pass_r605"],
    "prereg": "eval/rover/r622/prereg-r622.json",
    "evidence": "eval/rover/r622/report-r622.md",
    "verdict": "定因成立：判定层 90.6%（113 谓词错 + 31 同源硬崩）· rc=0（只表本轮判据全绿）· 零产品改动 ⇒ **无降幅可宣称**，质量/成本面沿用 R621「参考（未可验收）」",
}

REG_ROW = {
    "id": "r622.wythoff-attribution-and-mechanism",
    "round": "R622",
    "owner_round": "R622",
    "level": "L3",
    "evidence_generated_with": {
        "evidence_kind": "artifact",
        "pin_status": "frozen",
        "pin_reason": "archived-per-round",
        "artifact_sha12": "",
        "instrument": "eval/rover/r622/closeout_r622.py",
        "instrument_sha12": "",
        "binding": "audit-pin",
        "audited_by_round": "R622",
    },
    "capability": ("RF0004.2 · M3 **承重缺口定因（只读轮）**：R621 已把 wythoff 族定位为承重缺口"
                   "（T 223/270 · C 158/270 · codex 真值 45/45），但未定「失败落在哪一层」。本轮以"
                   "**与被测零共享代码**的独立 oracle（来源 = 冻结题面逐字规格，路线 = 按 a+b 升序的定义式 DP，"
                   "非被测/生成器可能用的冷点公式）对 R621 冻结产物**只读复算** 39 跑次 × 15 例，做逐例四分 + "
                   "行为式机制归因。**读数**：J0 oracle 正控 15/15 · J1 变异负控 v2 逐例对应 mismatch 0/45 · "
                   "J2 复算 == 冻结裁决（期望从 verdict-r621.json 派生）· J3 四分覆盖 100%（无残留桶）· "
                   "J4 目标子型 71.1% ≥50% · J5 真值全对（非夹具缺陷、非两侧同败）。**机制**：判定层 "
                   "= 113(COLD_PRED_WRONG) + 31(CRASH，同源) = **144/159 = 90.6%**；选点层 9 · 枚举序 2 · 未分类 4；"
                   "`LEGAL_NONMIN` 仅 2/159 ⇒ 判据僵硬非主因。**硬崩取证**：产物树副本上 `python3 -B -m games wythoff` "
                   "⇒ rc=1 / stdout 空 / `games/wythoff.py:48` `i, j = best` 上 `TypeError: cannot unpack non-iterable NoneType`"
                   "（谓词全否 ⇒ best=None ⇒ 未自验即交付）。**未成立/未判明**：① precond（铁律 11）rc=1 ⇒ 质量/成本面一律"
                   "**参考（未可验收）**；② 预注册 J1 v1 判据（变异体非 OK == 15/15）**首跑即证伪**（实得 4/15 · 12/15），"
                   "原样入档不翻案，修正判据为 post-hoc；③ 夹具判别力缺口登记（「字典序最小」子型仅 3/15 例被行使，"
                   "退化解 M2 拿 12/15=80%）——受「禁新增夹具」令约束，须用户放行；④ 判定层与选点层的因果顺序未判明。"),
    "evidence_path": "eval/rover/r622/report-r622.md",
    "evidence_cmd": "python3 -B eval/rover/r622/attrib_r622.py --negctl && python3 -B eval/rover/r622/aux_r622.py && python3 -B eval/rover/r622/closeout_r622.py && python3 eval/capability/status_gen.py --check",
    "negative_control": ("① 变异负控三分支（`attrib_r622.py --negctl`）：M1 恒判必败 4/15 · M2 取字典序最大 12/15 · "
                         "M3 与 oracle 同解 15/15 ⇒ 判据器**逐例对应**（tag==OK ⟺ 该例字节等于期望，mismatch 0/45）；"
                         "② oracle 正控（J0）：独立 oracle 复现冻结期望字节 15/15，否则归因不可采信；"
                         "③ 真值臂（J5）：codex 45/45 全对 ⇒ 排除「两侧同败＝夹具缺陷」（R512 教训）；"
                         "④ 复算确定性：同一产物两次独立跑次 sha256 同值（344ffa22…）。"),
    "covers": ["F_merge.quality.allpass", "F_merge.quality.cases_median_truth", "F_merge.gate.precondition_rc",
               "F_orch.wythoff.pass_r606"],
    "runs": 39,
    "verdict": "定因成立（判定层 90.6%）· rc=0（仅表本轮判据全绿）· 零产品改动 ⇒ 无降幅可宣称 · precond rc=1",
    "aot": "未重发布（本轮零产品源码改动、零新臂 ⇒ 复用 R621 冻结产物逐字节；AOT 面不适用本轮）",
}


def main():
    # ---- ① 文献台账（追加语义）----
    n0 = sum(1 for _ in io.open(LEDGER, encoding="utf-8"))
    with io.open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(LEDGER_BLOCK)
    n1 = sum(1 for _ in io.open(LEDGER, encoding="utf-8"))
    assert n1 > n0, "台账未增长"
    print("ledger: %d -> %d 行" % (n0, n1))

    # ---- ② KPI 行（追加）----
    import datetime
    row = dict(KPI_ROW)
    row["ts"] = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    with io.open(KPI, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    last = [l for l in io.open(KPI, encoding="utf-8").read().splitlines() if l.strip()][-1]
    back = json.loads(last)
    assert back["round"] == "R622" and back["baselines"], "KPI 行回读失败"
    print("kpi: 追加 R622 行 ok, baselines %d 条, ts=%s" % (len(back["baselines"]), back["ts"]))

    # ---- ③ 登记表（先断言序列化器逐字节复现，否则文本插入）----
    raw = io.open(REG, encoding="utf-8").read()
    obj = json.loads(raw)
    import hashlib
    def sha12(p):
        return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]
    inst = REG_ROW["evidence_generated_with"]
    inst["instrument_sha12"] = sha12(os.path.join(REPO, "eval/rover/r622/closeout_r622.py"))
    inst["artifact_sha12"] = hashlib.sha256(
        io.open(os.path.join(REPO, "eval/rover/r622/verdict-r622.json"), "rb").read()).hexdigest()[:12]

    rendered = json.dumps(obj, ensure_ascii=False, indent=1) + "\n"
    if rendered == raw:
        print("registry: 序列化器逐字节复现原文件 ⇒ 允许 JSON 改写")
        obj["rows"].append(REG_ROW)
        obj["updated_round"] = "R622"
        out = json.dumps(obj, ensure_ascii=False, indent=1) + "\n"
        io.open(REG, "w", encoding="utf-8").write(out)
    else:
        print("registry: 序列化器**未**逐字节复现 ⇒ 改用文本插入（末行前补逗号）")
        row_txt = json.dumps(REG_ROW, ensure_ascii=False, indent=1)
        row_txt = "\n".join(" " + ln for ln in row_txt.splitlines())
        idx = raw.rstrip().rfind("\n]")
        new = raw.rstrip()[:idx] + ",\n" + row_txt[1:] + raw.rstrip()[idx:]
        io.open(REG, "w", encoding="utf-8").write(new)

    back = json.loads(io.open(REG, encoding="utf-8").read())
    ids = [r["id"] for r in back["rows"]]
    assert "r622.wythoff-attribution-and-mechanism" in ids, "登记行未落盘"
    assert back["updated_round"] == "R622", "updated_round 未刷"
    print("registry: 行数 %d, 末行 id=%s, updated_round=%s" % (len(back["rows"]), ids[-1], back["updated_round"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
