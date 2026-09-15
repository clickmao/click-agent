#!/usr/bin/env python3
"""EXP1-Q12 读数入台账 eval/capability/kpi.jsonl（幂等：同 round 已存在则跳过）。"""
import json
import os
import sys

ROOT = "/home/agentuser/AgentFramework"
S = os.path.join(ROOT, "eval/capability/exp1-q12")
KPI = os.path.join(ROOT, "eval/capability/kpi.jsonl")


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


main = load(os.path.join(S, "form_check_q12.json"))
rerun = load(os.path.join(S, "rerun", "form_check_q12.json"))
final = load(os.path.join(S, "final", "form_check_q12.json"))
st = load(os.path.join(S, "selftest_q12.json"))
first = load(os.path.join(S, "preflight.txt".replace("preflight.txt", "form_check_q12.json")))


def slim(d):
    return {"verdict": d["verdict"], "exit": d["exit_code"],
            "counts": d["detail"]["results"], "families": d["detail"]["families"],
            "gate": {"concurrent": d["detail"]["gate"].get("gate_concurrent_procs"),
                     "MemAvailable_MB": d["detail"]["gate"].get("gate_MemAvailable_MB")},
            "peak_mem": d.get("peak_memory_posthoc")}


entry = {
    "round": "EXP1-Q12",
    "ts": json.loads('"' + final["ts"] + '"') if False else final["ts"],
    "kind": "verification-form-recheck(debt-closeout)+gate-defect-fix",
    "artifact": ("eval/capability/exp1-q12/{prereg_q12.json,prereg_q12_amend1.json,"
                 "run_form_check_q12.sh,parse_form_check_q12.py,form_check_q12.json,"
                 "run_form_check.log,trx/form_check_q12.trx,rerun/,final/,selftest_q12.json,mem_samples.txt,"
                 "apply_doc_edits_q12.py,preflight.txt}; "
                 "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md 附录M; "
                 "docs/plans/v0.22.0-longterm-backlog.md(L3 exp1 行)"),
    "change": ("L.7 #4 只推进一步 = 形式校验补跑（第四轮结转清账）：新增 eval/capability/exp1-q12/ 四件套"
               "（预注册 + 修正件 + runner + 三态判定器），真机 dotnet test 过滤三族；未改仪器 v2.6.0、"
               "未动 src/、skills/、docs/verification-registry.json。同轮抓出并修掉 3 处判定/器具缺陷"
               "（D1 新鲜度粒度、D2 闸门与能力判据同码、D3 闸门自伤=先读闸后收尾）；"
               "起手闸原档位 2800MB 落在本机读数噪声带内 ⇒ 首跑被拦（测量失败），"
               "以修正件按测量类重定档位（>=2600）后执行，C1–C6 能力判据一字未改。"),
    "readings": {
        "run1_gate_blocked": {"reason": "GATE_MEMORY", "MemAvailable_MB": 2675, "threshold_orig": 2800,
                              "concurrent": 0, "exit": 3},
        "run2_main": slim(main),
        "run3_rerun_after_doc_edits": slim(rerun),
        "run4_final_after_all_doc_edits": slim(final),
        "judge_selftest": {"n_fixtures": st["n_fixtures"], "n_pass": st["n_pass"], "exit": st["exit"],
                           "note": "含注入缺陷负控（Failed/NotExecuted/缺族/低于基线/计数不一致/无Counters/构建失败/陈旧证据/同秒边界/闸门两态/归属缺失）"},
        "threshold_noise_band": {"readings_MB": [2916, 2675, 2677], "spread_MB": 241,
                                 "orig_threshold": 2800, "amended_threshold": 2600,
                                 "verdict": "orig threshold inside oscillation band => gate not reproducible"},
        "reproduction_judge": {"two_runs_identical": True, "by": "verdict+counts+families",
                               "trx_sha_identical": False,
                               "note": "trx sha 内含运行时间/ID ⇒ 不作复现判据（防假红）"},
        "baseline_compare": {"exp1_q2_form_check": "13/13", "this_round": "13/13",
                             "same_conclusion": True},
        "docs_touched": {"exp1_plan_lines_1152_to_1269": True, "backlog_row": 22,
                         "registry_touched": False}
    },
    "criterion": ("C1 rc==0（显式标记，非末条命令）| C2 failed==0 ∧ skipped==0 ∧ other==0 | C3 total>=13 | "
                  "C4 三族各>=1 | C5 trx 不早于 prereg（防复用旧证据）| C6 归属指纹(HEAD+registry sha+skills 面) | "
                  "C7 环境闸 并发==0 ∧ MemAvailable>=阈值（阈值单一权威源=修正件）；"
                  "两源交叉（Counters vs 逐条结果）不一致判测量失败；三态退出码 0/2/3 分列"),
    "evidence_level": "L3",
    "honest": ("本轮 PASS 取自修正件档位；run2/3/4 起手读数 2701/2649/2xxx MB 均 **低于原档位 2800** "
               "⇒ 按首版预注册会被再次拦截：原档位在本机稳态余量下**结构性不可达**，两种口径并报不合并。"
               "预注册 P3（峰值占用<500MB）**被实测证伪**：首跑 725MB（含首次编译）、增量跑 177MB ⇒ "
               "峰值口径必须带构建态，且该字段只作信息量不作判据。证据等级 L3（未做跨机/跨工作目录复现）。"
               "13/13 与此前 exp1-q2 同计数，但两次之间 src/ 被对侧改过多轮 ⇒ 只证明这 13 条判据未被破坏，"
               "不代表被改动的源码面已覆盖。D3 修正的复跑中触发进程已自行退出（pre_shutdown_matches 空），"
               "但顺序缺陷是结构性的、不因偶发自行退出而消失。观察（未清）：对侧 6 个 r415 fake_llama 桩"
               "（>22h、连接 0、RSS≈42MB）未清理。"),
    "debt": ("(1) L.7 #1 裁定非 .cs 处理方式（前置未动）| (2) L.7 #2 两条真候选人工复核未做 | "
             "(3) L.7 #3 两计数分离升为仪器不变量未做 | (4) 新增候选：阈值噪声带机检项、先收尾→再读闸不变量未落仪器 | "
             "(5) 对侧 6 个 fake_llama 孤儿进程仅登记未清"),
    "next": ("L.7 #1 裁定「非 .cs 被引文件」处理方式（单列 index-scope-out vs 扩声明索引语料根）——"
             "后者改 strong/weak 可比性 ⇒ 独立预注册轮次；或先落本轮两条新候选的机检项"),
    "owner_round": "EXP1-Q12(60m 自检作业; 不占主线轮号)",
    "covers": [
        "eval/capability/exp1-q12/prereg_q12.json",
        "eval/capability/exp1-q12/prereg_q12_amend1.json",
        "eval/capability/exp1-q12/run_form_check_q12.sh",
        "eval/capability/exp1-q12/parse_form_check_q12.py",
        "eval/capability/exp1-q12/form_check_q12.json",
        "eval/capability/exp1-q12/run_form_check.log",
        "eval/capability/exp1-q12/trx/form_check_q12.trx",
        "eval/capability/exp1-q12/rerun/",
        "eval/capability/exp1-q12/final/",
        "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md"
    ],
    "negative_control": ("判定器 13 夹具全部双向可判（--selftest 13/13）：注入 Failed⇒exit 2；NotExecuted(跳过冒充通过)⇒2；"
                         "缺一族⇒2；total<13⇒2；归属指纹缺失⇒2；Counters 与逐条不一致⇒3；缺 Counters⇒3；"
                         "rc!=0 且零结果(构建失败)⇒3；复用陈旧 trx⇒3；并发闸>0⇒3；内存低于档位⇒3；"
                         "同秒落盘⇒0(不误判陈旧)。另有真机负控：run1 被闸真实拦下（exit 3 非 2），"
                         "attempt1 被并发闸真实拦下（VBCSCompiler pid 落盘）。")
}

existing = ""
if os.path.exists(KPI):
    existing = open(KPI, "r", encoding="utf-8").read()
if "\"EXP1-Q12\"" in existing:
    print("SKIP: EXP1-Q12 already in ledger (idempotent)")
    sys.exit(0)

line = json.dumps(entry, ensure_ascii=False)
assert "\n" not in line
with open(KPI, "a", encoding="utf-8") as f:
    f.write(line + "\n")

# 写后读回校验：解析末行 + 计数
back = open(KPI, "r", encoding="utf-8").read().splitlines()
assert back[-1] == line, "读回校验失败：末行不等于写入行"
parsed = json.loads(back[-1])
assert parsed["round"] == "EXP1-Q12"
print(f"APPENDED ok: lines={len(back)} round={parsed['round']} verdicts="
      f"{parsed['readings']['run2_main']['verdict']}/"
      f"{parsed['readings']['run3_rerun_after_doc_edits']['verdict']}/"
      f"{parsed['readings']['run4_final_after_all_doc_edits']['verdict']}")
sys.exit(0)
