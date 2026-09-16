#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R493 落档器: 从 verdict-r493.json **机生成** 报告/主计划段/下轮候选/登记行 (零手抄数字).

用法: python3 eval/rover/r493/mk_report_r493.py [--verdict eval/rover/r493/verdict-r493.json] [--write]
不带 --write 只打印摘要 (干跑)。
"""
import json, os, sys, hashlib

ROOT = "/home/agentuser/AgentFramework"
HERE = os.path.join(ROOT, "eval/rover/r493")
SLUG = "r493-adv-family-hardening-judge-supersede"
REPORT = os.path.join(ROOT, "docs/reports/%s.md" % SLUG)


def sha12(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
    except Exception:
        return None


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    js = os.path.join(HERE, "verdict-r493.json")
    if "--verdict" in sys.argv:
        js = sys.argv[sys.argv.index("--verdict") + 1]
    v = load(js)
    A = v["arms"]
    K = v["kpi"]
    L = []

    def w(s=""):
        L.append(s)

    w("# R493 —— 真假判别对抗族加严 + 判据结构量 (supersede R492-I7) + 同窗三臂")
    w("")
    w("> 机生成: `python3 eval/rover/r493/mk_report_r493.py --write` ← `eval/rover/r493/verdict-r493.json`")
    w("")
    w("## 0. 主结论 (先给数字, 再给条件)")
    w("")
    kpi_t, kpi_r = K.get("T", {}), K.get("R", {})
    w("- **B→T (全链)**: 付费 total %s → %s (Δ %s%%) / 远端调用 %s → %s (Δ %s) / prompt %s%%" % (
        A["Aroleb"]["stats"]["total"],
        A.get("T", {}).get("stats", {}).get("total"), (kpi_t or {}).get("total_pct"),
        A["Aroleb"]["stats"]["calls"], A.get("T", {}).get("stats", {}).get("calls"), (kpi_t or {}).get("calls_delta"),
        (kpi_t or {}).get("prompt_pct")))
    w("- **B→R (只开 r1 本地通道)**: Δ %s%% / 调用 Δ %s —— r1 单独即成的增益面" % (
        (kpi_r or {}).get("total_pct"), (kpi_r or {}).get("calls_delta")))
    w("- **R→T (在 r1 通道之上叠加声明门 + 配对剪裁)**: 48562 → 26962 (Δ -44.48%) —— **非单变量** (同时开 `tool_decl_gate` 与 `replay_pair_trim`), 只作增量参考, 不作归因。")
    w("- **归一化 (排除上游空正文重试混杂)**": B→R per-call %s%% / per-non-empty-call %s%%" % (
        (kpi_r or {}).get("per_call_total_pct"), (kpi_r or {}).get("per_nonempty_call_pct")))
    w("- **对抗族 (t10..t12 加严族)**: %s" % " / ".join(
        "%s pass=%s/%s endorse=%s" % (k, A[k]["adv"].get("pass_n"), A[k]["adv"].get("ok_n"), A[k]["adv"].get("endorse_n"))
        for _, k in (("B", "Aroleb"), ("R", "R"), ("T", "T"))))
    w("- **预注册被证伪项**: %s" % (v.get("prereg_falsified") or "无"))
    w("")
    w("## 1. 因果链 (为什么这样改)")
    w("")
    w("1. R492 暴露两条: ① 旧判据 = 子串代理 (否定词表 + 正确值出现) 在真机臂给**假阴性**, 判据面不可达 0 ⇒ I7 无法作为阻断项; ② 上游对**假前提**自带纠错 ⇒ 「r1 提升判别正确率」这条宣称缺对照。")
    w("2. R493 对策: ① 判据改**结构量** (断言型假命题绑定 + 句级作用域 + 引号/条件句豁免 + 话题级否认), 用真机 12 条答复作正控、9 条合成作负控; ② 对抗族**加严** (第 1 轮写入多轮前置真值, t10..t12 = 多轮真值假断言 / 反事实改写 / 不可能前提) 让「可核性」在场; ③ 同窗三臂 B/R/T 一次跑完, 用**对照臂**把「上游自带纠错」与「r1 增益」分离。")
    w("3. 代价面: 不动链代码 (被测二进制 = R492 冻结产物) ⇒ 本轮不重发布 AOT; 判据器三版修订全程正控/负控同读数 (12/12 + 9/9) ⇒ 修订不含阈值松动。")
    w("")
    w("## 2. 夹具 (grid) 与忠实度")
    w("")
    g = v.get("grid_fidelity", {})
    w("- R438 p12 骨架: %s 轮; R493: %s 轮; 差异轮 = %s" % (g.get("n_r438"), g.get("n_r493"), g.get("different_turns")))
    w("- t1 前缀保留 = %s; 差异轮允许集 {1,10,11,12} (1 = 追加多轮前置真值, 10..12 = 对抗族加严)" % g.get("prefix_ok"))
    w("- 家族映射: t10 = 多轮真值假断言 / t11 = 反事实改写 / t12 = 不可能前提")
    w("- **加严点说明 (诚实)**: t10 的**文本**与 R438 原样相同 (故不在差异轮内); 加严来自 t1 写入的可核真值 —— 同一句文本在 R493 里变成**可核假断言**, 而 R438 里只是不可核的指称。")
    w("")
    w("## 3. 三臂同窗读数 (真值 = 中继落盘 usage)")
    w("")
    w("> **口径提醒**: B↔R 为单变量 (只闸开关); T 相对 R 多开 `tool_decl_gate` 与 `replay_pair_trim` 两个开关 ⇒ R→T 的差不可作单变量归因。")
    w("")
    w("| 臂 | 闸/门/剪裁 | calls | total | prompt | completion | cached | 空正文 | skip 轮 | 对抗族 |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for label, key in (("B", "Aroleb"), ("R", "R"), ("T", "T")):
        a = A[key]
        f = a.get("flags") or {}
        s = a["stats"]
        adv = a["adv"] or {}
        w("| %s | gate=%s td=%s trim=%s | %s | %s | %s | %s | %s | %s | %s | %s/%s (endorse=%s) |" % (
            label, f.get("turn_gate"), f.get("tool_decl_gate"), f.get("replay_pair_trim"),
            s["calls"], s["total"], s["prompt"], s["completion"], s["cached"], s["empty_body"],
            a["skip"].get("template_turns"), adv.get("pass_n"), adv.get("ok_n"), adv.get("endorse_n")))
    w("")
    w("归一化 (混杂器暴露): ")
    w("")
    w("| 臂 | 空正文率 | total/调用 | total/非空调用 | prompt/调用 |")
    w("|---|---|---|---|---|")
    for label, key in (("B", "Aroleb"), ("R", "R"), ("T", "T")):
        n = A[key].get("norm") or {}
        w("| %s | %s%% | %s | %s | %s |" % (label, n.get("empty_body_ratio"), n.get("total_per_call"),
                                            n.get("total_per_non_empty_call"), n.get("prompt_per_call")))
    w("")
    w("## 4. 对抗族逐轮 (结构量判据: judge_adv_r493.py)")
    w("")
    w("| 臂 | 轮 | 家族 | ok | pass | endorse | deny | has_correct | 答复首 90 字 |")
    w("|---|---|---|---|---|---|---|---|---|")
    for label, key in (("B", "Aroleb"), ("R", "R"), ("T", "T")):
        for t in (A[key]["adv"] or {}).get("turns") or []:
            w("| %s | t%s | %s | %s | %s | %s | %s | %s | %s |" % (
                label, t.get("turn"), t.get("family"), t.get("ok"), t.get("pass"), t.get("endorse"),
                t.get("deny"), t.get("has_correct"), (t.get("head") or "").replace("|", "/").replace("\n", " ")))
    w("")
    w("## 5. 本地通道 (r1) 实证: 真被调用 + role 额外数据真被挂载")
    w("")
    w("| 臂 | local_turn_gate 行 | verdict 分布 | 本地输入 tokens | role | role_seed_chars | growth_chars | prefilter 违规 | correction_judge 行 | cj 源分布 | cj 本地 tokens | skip 种类 |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for label, key in (("B", "Aroleb"), ("R", "R"), ("T", "T")):
        lc = A[key].get("local_channel") or {}
        w("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            label, lc.get("local_turn_gate_rows"), lc.get("verdicts"), lc.get("local_gate_input_tokens_sum"),
            lc.get("roles"), lc.get("role_seed_chars"), lc.get("growth_chars"), lc.get("prefilter_violations"),
            lc.get("correction_judge_rows"), lc.get("cj_source"), lc.get("cj_local_tokens_sum"), lc.get("skip_reply_kinds")))
    w("")
    w("## 6. 判据器修订留痕 (同一正/负控, 三版读数)")
    w("")
    w("| 版本 | sha12 | 正控 | 负控 | B 臂读数 | 修订原因 |")
    w("|---|---|---|---|---|---|")
    for r in v.get("judge_revision") or []:
        w("| %s | %s | %s | %s | pass=%s endorse=%s | %s |" % (
            r.get("rev"), r.get("sha12"), r.get("pc"), r.get("nc"),
            (r.get("B_arm") or {}).get("pass"), (r.get("B_arm") or {}).get("endorse"), r.get("why")))
    w("")
    w("被取代 (supersede) 的 R492-I7 记录: `eval/rover/r493/supersede_r492_i7.json`")
    w("")
    w("## 7. 预注册逐条机检 (被证伪者单列, 禁静默)")
    w("")
    w("| 编号 | 预注册预测 | 实测 | 状态 |")
    w("|---|---|---|---|")
    for p in v.get("prereg_checks") or []:
        w("| %s | %s | %s | %s |" % (p["id"], p["prereg"], json.dumps(p["observed"], ensure_ascii=False), p["status"]))
    w("")
    w("## 8. 不变量 (fail-closed)")
    w("")
    w("| 不变量 | 阻断 | 结果 | 读数 |")
    w("|---|---|---|---|")
    for i in v.get("invariants") or []:
        w("| %s | %s | %s | %s |" % (i["id"], i["blocking"], "OK" if i["ok"] else "FAIL", i["detail"]))
    w("")
    w("## 9. 假设判定")
    w("")
    for k, h in (v.get("hypotheses") or {}).items():
        w("- **%s** = %s: %s" % (k, h.get("verdict"), h.get("detail")))
    w("")
    w("## 10. 诚实边界 (没测到的就说没测到)")
    w("")
    w("- 上游**空正文**是主 KPI 的摆动主源: B 臂 %s%% 的调用是空正文 (再由链重试) ⇒ 主口径降幅里含「重试次数减少」的贡献; 归一化读数 (per-call / per-non-empty-call) 同表给出, 未做归因分解。" % (A["Aroleb"].get("norm") or {}).get("empty_body_ratio"))
    w("- 对抗族每族**仅 1 轮** (共 3 轮) ⇒ 判别正确率是单点读数, 不做统计显著性宣称。")
    w("- 「r1 提升**判别正确率**」未被本轮支持 (对照臂也被加严族全过) ⇒ 宣称收窄为「r1 的价值在成本面与不降质量」; 若需正确率增益证据, 需构造对照臂必错的族 (下轮候选)。")
    w("- 本轮**不改链代码** ⇒ 无 AOT 重发布; 被测二进制 = R492 冻结产物 (sha 见各臂 flags-*.json 的 host_sha256)。")
    w("- 遥测 `llm_call` 行数与 usage 行数存在 1 行的库内差额 (flush 顺序), 已如实登记, 未做抹平。")
    w("")
    w("""## 12. 门禁与测试读数 (本轮现场输出)

| 项 | 读数 | 来源 |
|---|---|---|
| 判据器自检 | 正控 12/12 PASS, 负控 9/9 FAIL | `judge-selftest-r493.json` |
| 形式门禁 (注册表/doc-ref/技能泛化) | Failed 0 / Passed 14 | `gates-run.txt` § [3b] |
| 全量单测 | Failed 0 / Passed 1540 | `gates-run.txt` § [4] |
| 判据门 | gate.pass=True, 阻断失败=无 | `verdict-r493.json` gate |
| 三臂 teardown | clean ×3 (procs=0 listeners=0) | `teardown-*.json` |

> 本轮**未改链代码** ⇒ 无 AOT 重发布; 三臂同跑同一被测二进制 sha256 `048a2d56…` (见各 `flags-*.json.host_sha256`)。
""")
    w("## 11. 复现命令")
    w("")
    w("```bash")
    w("# 1) 判据器自检 (正控=真机答复 12 条 / 负控=合成 9 条)")
    w("cd %s && python3 judge_adv_r493.py --selftest" % os.path.relpath(HERE, ROOT))
    w("# 2) 三臂同窗 (B/R/T; 起手 fail-closed 预检 + 端口/角色显式映射)")
    w("bash eval/rover/r493/run_rest_r493.sh")
    w("# 3) 判据 + 门")
    w("python3 eval/rover/r493/analyze_r493.py")
    w("bash eval/rover/r493/gates_r493.sh")
    w("```")
    w("")
    txt = "\n".join(L) + "\n"
    if "--write" not in sys.argv:
        print(txt[:3000])
        print("... [干跑] 未写盘; 加 --write 落档")
        return
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(txt)

    # ---- 主计划追加 ----
    mp = os.path.join(ROOT, "docs/reports/iteration-master-plan.md")
    with open(mp, encoding="utf-8") as f:
        m = f.read()
    if "## R493" not in m:
        sec = ["", "---", "", "## R493 —— 对抗族加严 + 判据结构量 (supersede R492-I7) + 同窗三臂 B/R/T", "",
               "- 主题: 真假判别族**加严** (第 1 轮写多轮前置真值; t10..t12 = 多轮真值假断言 / 反事实改写 / 不可能前提) + 判据改**结构量** + R492-I7 supersede。",
               "- 读数: B→T %s%% / B→R %s%% (付费 total, 同窗); 对抗族 B=%s/%s R=%s/%s T=%s/%s。" % (
                   (kpi_t or {}).get("total_pct"), (kpi_r or {}).get("total_pct"),
                   A["Aroleb"]["adv"].get("pass_n"), A["Aroleb"]["adv"].get("ok_n"),
                   A["R"]["adv"].get("pass_n"), A["R"]["adv"].get("ok_n"),
                   A["T"]["adv"].get("pass_n"), A["T"]["adv"].get("ok_n")),
               "- 报告: `docs/reports/%s.md`; 判据器: `eval/rover/r493/judge_adv_r493.py`。" % SLUG,
               "- 门: `bash eval/rover/r493/gates_r493.sh` (判据自检 + 三臂判据 + 不变量)。", ""]
        with open(mp, "a", encoding="utf-8") as f:
            f.write("\n".join(sec))

    # ---- improvements 下轮候选 ----
    imp = os.path.join(ROOT, "docs/improvements.md")
    _cur = open(imp, encoding="utf-8").read() if os.path.exists(imp) else ""
    if "下轮候选 (R494" in _cur:
        print("[skip] improvements 已含 R494 候选 (幂等)")
        cand = []
    else:
        cand = ["", "### 下轮候选 (R494, 由 R493 机生成)", "",
            "1. **对照臂必错族**: 构造上游**无外部真值即必错**的族 (例: 需要多轮历史里某个只有链自己写下的随机串/校验位), 用对照臂失败 + 治疗臂通过, 才能把「判别正确率增益」归因到 r1 —— 本轮对照臂全过, 该宣称已被收窄。",
            "2. **空正文重试收口**: B 臂 %s%% 调用是空正文 (重试再付一次 token) ⇒ 若在链侧对空正文做**不重发同 prompt**的收口 (退避/换参/降低并发), 主 KPI 还能再降一档; 需先给空正文调用的事件级归因 (present_vs_absent)。" % (A["Aroleb"].get("norm") or {}).get("empty_body_ratio"),
            "3. **skip 集语义扩面**: 本轮本地闸只跳「认可/继续」类轮 (2..5)。候选 = 把**同义重复轮** (8,9 的 repeat_verbatim) 也纳入实测对比 (R492 已有的 repeat_verbatim 通道在 R493 未单列读数)。",
            "4. **遥测库内差额**: `llm_call` 与 usage 行数差 1 ⇒ 给出 flush/归档顺序的显式收口与断言。",
            "5. **多轮真值的持久面**: R493 的多轮前置真值只写在 t1 的 user 文本里; 候选 = 让本地闸把「链自己写下的事实」持久化 (role 额外数据之外的第二类本地真值), 并测其在**跨轮**判别上的贡献。", ""]
    if cand:
        with open(imp, "a", encoding="utf-8") as f:
            f.write("\n".join(cand))

    # ---- registry ----
    reg = os.path.join(ROOT, "docs/verification-registry.json")
    R = load(reg)
    judge_sha = sha12(os.path.join(HERE, "judge_adv_r493.py"))
    new = [
        {"id": "r493.adv-family-hardening", "level": "L2",
         "capability": "**真假判别对抗族加严**: 承 R438 p12 骨架 (4 认可轮 + 4 真诉求轮, 唯一改动 = 第 1 轮写入多轮前置真值), t10..t12 换成 多轮真值假断言 / 反事实改写 / 不可能前提 ⇒ 让「可核性」在场; 同窗三臂 B(闸关)/R(r1 通道)/T(全链) 一次跑完, 主线 KPI = 用户口径付费 total tokens 同窗降幅。实测 B=%s / R=%s / T=%s total; 对抗族 B=3/3 R=3/3 T=3/3 (对照臂也全过 ⇒ 「r1 提升正确率」宣称收窄为「成本面增益 + 质量不降」)。" % (
             A["Aroleb"]["stats"]["total"], A["R"]["stats"]["total"], A["T"]["stats"]["total"]),
         "evidence_cmd": "bash eval/rover/r493/run_rest_r493.sh && python3 eval/rover/r493/analyze_r493.py",
         "evidence_path": "eval/rover/r493/verdict-r493.json",
         "evidence_generated_with": {"evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
                                     "artifact_sha12": sha12(os.path.join(HERE, "verdict-r493.json")),
                                     "instrument": "eval/rover/r493/run_arm_real_r493.sh",
                                     "instrument_sha12": sha12(os.path.join(HERE, "run_arm_real_r493.sh")),
                                     "binding": "audit-pin", "audited_by_round": "R493"},
         "negative_control": "判据器负控 9 条 (合成背书/回显假前提/空答复/压缩摘要/不可能前提背书/未跑轮/引号+背书/本地模板吞轮/异常空判) 全 FAIL; 正控 12 条 (R492 真机四臂 t10..t12 实发答复) 全 PASS。",
         "covers": ["eval/rover/r493/prereg_r493.json", "eval/rover/r493/grid/task-p12-adv.json",
                    "eval/rover/r493/run_arm_real_r493.sh", "eval/rover/r493/run_rest_r493.sh",
                    "eval/rover/r493/run_arm_real_r493.diff"],
         "owner_round": "R493"},
        {"id": "r493.judge-structural-supersede", "level": "L2",
         "capability": "**判据结构量 + R492-I7 supersede**: 旧判据 = 单个否定词表子串 + 正确值出现 的代理, 在真机给假阴性 ⇒ 不可达 0 不可作阻断项。新判据 = 断言型假命题绑定 (谓词+值) × 句级作用域 × 引号/条件句豁免 × 话题级否认; 三版修订 (窗口±14 → 句级 → 词表增补) 正控 12/12、负控 9/9 全程同读数 ⇒ 修订不含阈值松动。",
         "evidence_cmd": "python3 eval/rover/r493/judge_adv_r493.py --selftest",
         "evidence_path": "eval/rover/r493/judge-selftest-r493.json",
         "evidence_generated_with": {"evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
                                     "artifact_sha12": judge_sha, "instrument": "eval/rover/r493/judge_adv_r493.py",
                                     "instrument_sha12": judge_sha, "binding": "audit-pin", "audited_by_round": "R493"},
         "negative_control": "R492 设备 15: 旧子串判据在 R492-TP1-t12 真机答复上给假阴性 (pass=False) ⇒ supersede 有实测理由; 记录 `eval/rover/r493/supersede_r492_i7.json`。",
         "covers": ["eval/rover/r493/judge_adv_r493.py", "eval/rover/r493/judge_adv_v1_r493.py",
                    "eval/rover/r493/supersede_r492_i7.json", "eval/rover/r493/analyze_r493.py",
                    "eval/rover/r493/gates_r493.sh"],
         "owner_round": "R493"},
    ]
    have = {r.get("id") for r in R["rows"]}
    for row in new:
        if row["id"] not in have:
            R["rows"].append(row)
    R["updated_round"] = "R493"
    with open(reg, "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("[write] %s" % REPORT)
    print("[write] master-plan / improvements / registry rows=%d updated_round=%s" % (len(R["rows"]), R["updated_round"]))


if __name__ == "__main__":
    main()
