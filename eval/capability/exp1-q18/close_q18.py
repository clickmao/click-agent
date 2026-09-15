#!/usr/bin/env python3
"""EXP1-Q18 收尾: ① kpi.jsonl 幂等追加登记行 ② 首跑自污染臂标 VOID+改名。

幂等: 以 round == "EXP1-Q18" 去重 (已有则跳过)。
"""
import json
import pathlib
import shutil
import datetime

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
Q18 = ROOT / "eval/capability/exp1-q18"
KPI = ROOT / "eval/capability/kpi.jsonl"
RID = "EXP1-Q18"

v = json.loads((Q18 / "verdict_q18.json").read_text(encoding="utf-8"))
ck = v["checks"]
rv = json.loads((Q18 / "verdict_q18_replay.json").read_text(encoding="utf-8"))
ra = json.loads((Q18 / "verdict_q18_replay_old.json").read_text(encoding="utf-8"))
art_v = next(iter(rv["artifacts"].values()))
art_c = next(iter(ra["artifacts"].values()))
prov = v["provenance"]

line = {
    "round": RID,
    "ts": datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
    "kind": "fix+replayability(exp1-L.8候选①落地)",
    "artifact": "eval/capability/exp1-q18/{prereg_q18.json,build_q18_probe.py,probe_v270.py,drive_q18.py,"
                "finalize_q18.py,verdict_q18.json,evidence_q18.txt,verdict_q18_replay.json,"
                "verdict_q18_replay_old.json,verdict_q18_provenance.json,verdict_q18_provenance_old.json,"
                "drive_q18.json,build_q18.json,baseline_shas_before.txt,frozen/arm_v260, frozen/arm_v270}; "
                "eval/capability/q18a-v260|q18a-v270/(双臂自洽器具链); "
                "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md 附录S",
    "change": "L.8 候选① 只推进一步 = 白名单落地修法 + 独立重放性证明。v2.6.0→v2.7.0 **单变量两行**"
              "（PROBE_VERSION 常量 + citations.jsonl 落盘白名单追加 symbol_faces/relocated_symbol_faces），"
              "其余逐字相同；在**冻结语料快照**（/tmp/q18_corpus, fingerprint bcde4dfc…997 行）上跑"
              "**双臂对照**（同语料 + 仅器具版本一个变量）⇒ 治疗臂 n_symbol_faces 622/622 逐位复算、"
              "symbol_face_rungs 六桶全等、不可重放 **4→2**（余 stale_like_n=SELF_REFERENTIAL_CROSS_ARTIFACT / "
              "symbol_occurrences=PARAM_SCOPE）；对照臂（旧器具）仍判 ARCHIVE_FACE_FIELD_ABSENT。"
              "q10 冻结件（probe_v260.py / citations.jsonl / attribution_q10.json）sha256 逐位未变；"
              "未改 src/、skills/、docs/verification-registry.json、eval/rover/、unit_axis_guard.py、"
              "archive_field_provenance.py；**零 dotnet，不占主线轮号**（对侧正跑 R462 AOT E2E）。",
    "readings": {
        "instrument": "probe_v270.py (v2.6.0 + 2 单变量) sha256=fe8dc0d7e3d3f75c; 判据器具零改动",
        "corpus": {"frozen_snapshot": "/tmp/q18_corpus", "fingerprint": v["corpus_fingerprint"],
                   "rows": 997, "md_cs_files": 718},
        "replay_ab": {
            "treatment_not_replayable": art_v.get("not_replayable"),
            "treatment_typed": art_v.get("not_replayable_typed"),
            "control_not_replayable": art_c.get("not_replayable"),
            "control_typed": art_c.get("not_replayable_typed"),
            "n_symbol_faces": {"registered": 622, "replayed": 622, "equal": True},
            "symbol_face_rungs_equal": art_v["C1_replay"]["all_equal"],
            "C1_checked": art_v["C1_replay"]["checked"]},
        "keyset": {"A_size": [art_c and 24, prov["v270"]["A_size"]], "D_size": prov["v270"]["D_size"],
                   "archive_key_count": [24, 25]},
        "field_presence": {"present": 887, "nonempty": 488, "relocated_symbol_faces": 0,
                           "rows_total": 997, "early_returns_before_face_assign": 7},
        "class_distribution": {"v270": prov["v270"]["class_distribution"],
                               "v260": prov["v260"]["class_distribution"],
                               "conserved_sum": prov["v270"]["class_conserved_sum"],
                               "omitted_fields_v270": prov["v270"]["omitted_fields"]},
        "findings_ab": {"v270": art_v["counts"], "v260": art_c["counts"], "identical": True},
        "semantic_zero_regression": {"equal_after_strip": ck["C2_语义零回归"]["detail"]["equal_after_strip"],
                                     "stripped_fields": ck["C2_语义零回归"]["detail"]["ignored_nonsemantic_fields"]},
        "checks": {k: val["status"] for k, val in ck.items()},
        "n_pass": sum(1 for x in ck.values() if x["ok"] is True),
        "n_fail": v["n_fail"], "n_waived": v["n_waived"],
        "corpus_drift": {"rows": [928, 997], "face_rungs_sum": [575, 622]}},
    "criterion": "C1 单变量 diff 恰 2 行 | C2 剥非语义字段后语义逐位相等 | C5 治疗臂 not_replayable==2 且"
                 "typed 集合 == {stale_like_n, symbol_occurrences} | C9 对照臂仍判 ARCHIVE_FACE_FIELD_ABSENT"
                 "（成对负控）| C6b v2.7.0 归档 == {archived 25, omission 7, branch_unhit 3} Σ=35 守恒 |"
                 " C7 同语料双臂 findings 逐键相同 | C8 q10 冻结件 sha 逐位未变",
    "evidence_level": "L1-static（冻结语料快照 + 真源码 AST 派生 + 双臂同语料对照 + 判据器具零改动；"
                      "无编译/测试/AOT ⇒ 不报 L3/L4）",
    "honest": "① 三条预注册判据被**证伪**并如实入档: C4（预测 rows_with_symbol_faces=921, 实测 presence 887/"
              "nonempty 488 —— 预测模型把「未早退」当成「有 face」的充分条件）、C5b（登记数值面 575/absent79 "
              "不可与冻结语料并列: 行数 928→997 系同机对侧 R462 推进 + 文档增长所致, 登记数值**声明作废**）、"
              "C6（预注册 omission 9→8, 实测 9→**7**: 键一旦进白名单即**构造性**移出 omission 类, 我的 8 是推导错误）。"
              "② 首跑 A/B **作废（VOID）**: 两臂在**非冻结**语料上跑且我的臂副本/产物自身落进被测语料 ⇒ 3571 处差异"
              "全属语料漂移 + 自我污染, 不是器具差异 —— 已改名 arm_*_VOID_self_include 留档, 不参与任何结论。"
              "③ 9 枚漏字段中本轮只补 2 枚（被已登记读数派生链消费的那 2 枚）; 其余 7 枚仍不落盘 ⇒ **不得**宣称"
              "「整体可重放面提升」。④ relocated_symbol_faces 在本语料**分支未命中**（0 命中）⇒ 其可重放性**未证明**。"
              "⑤ 字段存在性(887) ≠ 字段非空(488) 两个数分开报, 不得混用。⑥ 本轮零产品代码改动 ⇒ 无产品性能读数; "
              "形式校验（VerificationForm|SkillGeneralization|DevPlanDocRef）**结转**: 对侧 R462 AOT 真跑在场, "
              "起手闸 MemAvailable 2097MB < 2650MB。",
    "debt": "(1) 其余 7 枚漏字段是否补白名单（按「是否被已登记读数消费」逐枚判，不得一次补全）| "
            "(2) relocated 面正例语料（触发分支以证明其可重放）| (3) L2 器具登记（对侧空闲 + 全量面复跑）| "
            "(4) 形式校验结转清账 | (5) 登记数值面重锚（用冻结语料重刷 Q16/Q17 的数值登记，声明旧值作废）",
    "next": "L.8 剩余候选：① L2 器具登记（对侧空闲 + 全量面复跑）→ ② 形式校验结转清账 → ③ relocated 面正例语料"
            "（独立预注册轮次）→ ④ 阶段 B 可配语言集（独立预注册轮次）。",
    "owner_round": "EXP1-Q18(60m 自检作业; 不占主线轮号)",
    "covers": ["eval/capability/exp1-q18/prereg_q18.json", "eval/capability/exp1-q18/build_q18.json",
               "eval/capability/exp1-q18/probe_v270.py", "eval/capability/exp1-q18/verdict_q18.json",
               "eval/capability/exp1-q18/evidence_q18.txt", "eval/capability/exp1-q18/verdict_q18_replay.json",
               "eval/capability/exp1-q18/verdict_q18_replay_old.json",
               "eval/capability/exp1-q18/verdict_q18_provenance.json",
               "eval/capability/exp1-q18/verdict_q18_provenance_old.json",
               "eval/capability/exp1-q18/drive_q18.json",
               "eval/capability/exp1-q18/frozen/arm_v260/citations.jsonl",
               "eval/capability/exp1-q18/frozen/arm_v270/citations.jsonl",
               "eval/capability/q18a-v260/probe_v260.py", "eval/capability/q18a-v270/probe_v270.py",
               "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md"],
    "negative_control": "成对双臂: 同一冻结语料 + 同一 emit 面, 仅器具版本一个变量 ⇒ 治疗臂 not_replayable=2 / "
                        "对照臂 not_replayable=4（两枚面字段 typed ARCHIVE_FACE_FIELD_ABSENT）。判据器具"
                        "（unit_axis_guard.py v1.3 / archive_field_provenance.py）**零改动**，两臂读数差异只能归因到"
                        "白名单那一行。另: C2 语义零回归证明该行不进任何判决/计数（唯一残余 = 2 个墙钟字段）。",
}

existing = []
if KPI.is_file():
    existing = [json.loads(l) for l in KPI.read_text(encoding="utf-8").splitlines() if l.strip()]
if any(r.get("round") == RID for r in existing):
    print("KPI_ALREADY_PRESENT -> skip append")
else:
    with KPI.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    print("KPI_APPENDED", len(line.__str__()), "chars")

# --- 首跑作废臂: 标 VOID + 改名 (留档, 不参与结论)
marker = Q18 / "VOID_FIRST_ATTEMPT.md"
marker.write_text(
    "# VOID: 首跑 A/B (非冻结语料 + 自我污染)\n\n"
    "首跑把 v2.6.0/v2.7.0 直接跑在**活动工作树**上，且我的臂副本与产物（arm_v260_now/probe_v260.py、"
    "arm_v270/*）**落进了被测语料** ⇒ 两臂看到的语料不同（3571 处差异，全属语料漂移与自我污染）。\n"
    "处置: 全部作废（VOID），改名留档；正式结论只取 `frozen/` + `eval/capability/q18a-*/`（冻结快照双臂）。\n"
    "教训: 被测量语料必须**冻结快照**，且测量产物必须落在语料之外。\n", encoding="utf-8")


def rename(old, new):
    o, n = Q18 / old, Q18 / new
    if o.exists() and not n.exists():
        o.rename(n)
        return f"{old} -> {new}"
    return f"{old}: skip"


print(rename("arm_v260_now", "arm_v260_VOID_self_include"),
      "|", rename("arm_v270", "arm_v270_VOID_self_include"))
print("KPI rows now:", len([l for l in KPI.read_text(encoding='utf-8').splitlines() if l.strip()]))
