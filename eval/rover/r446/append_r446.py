#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R446 台账追加: docs/verification-registry.json (4 行) + eval/capability/kpi.jsonl.

铁律: registry EOF 无换行 (json.dumps 后不加 \n); 行内 evidence_path 必须是**单个**真实路径;
     covers 必须纯路径; L>=2 必填 negative_control; 写入后回读校验 (行数 + 新 id)。
"""
import json
import pathlib
import sys

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
REG = ROOT / "docs/verification-registry.json"
KPI = ROOT / "eval/capability/kpi.jsonl"


def add_rows(rows):
    raw = REG.read_text(encoding="utf-8")
    doc = json.loads(raw)
    have = {r.get("id") for r in doc["rows"]}
    n0 = len(doc["rows"])
    added = []
    for r in rows:
        if r["id"] in have:
            print(f"[skip] 已存在 {r['id']}")
            continue
        doc["rows"].append(r)
        added.append(r["id"])
    out = json.dumps(doc, ensure_ascii=False, indent=2)
    if not raw.endswith("\n"):
        out = out.rstrip("\n")
    REG.write_text(out, encoding="utf-8")
    back = json.loads(REG.read_text(encoding="utf-8"))
    assert len(back["rows"]) == n0 + len(added), "回读行数不符"
    assert all(any(x.get("id") == i for x in back["rows"]) for i in added), "回读 id 缺失"
    print(f"[registry] {n0} -> {len(back['rows'])} 行, 新增 {added}")
    return back


def rows_def(a):
    return [
      {"id": "r446.judge-determinism", "capability": "判官路径确定性(真机产品路径)",
       "level": "L1", "owner_round": "R446",
       "evidence_cmd": "R446_GRID=JDET24 R446_NS=-s1 bash eval/rover/r446/run_judge_det.sh 48330 48332",
       "evidence_path": "eval/rover/r446/verdict-JDET24-s1.json",
       "negative_control": "预注册门槛 n_local>=8: 12 轮版仅 5 次判官调用 ⇒ INVALID_PREMISE(未事后改阈值, 加长 24 轮重测); D2 要求 prompt_len 唯一且样本数达标; D3 记账 ev-new=0 全行; D4 形态 argv 直取(-np 1/f32/flash-attn off)",
       "covers": ["eval/rover/r446/analyze_judge_det.py", "eval/rover/r446/grid/task-JDET24.json", "eval/rover/r446/README-evidence.md"]},
      {"id": "r446.zero-token-settlement-precheck", "capability": "判官 0-token 结算可行性(消息面) —— 负结论",
       "level": "L1", "owner_round": "R446",
       "evidence_cmd": "python3 eval/rover/r446/l1_ext_precheck.py >/dev/null; python3 eval/rover/r446/l1_ext_precheck_v2.py >/dev/null",
       "evidence_path": "eval/rover/r446/l1_ext_precheck.json",
       "negative_control": "v1 必须检出 Correct->Adopt 误赏(实测 9 行 ⇒ FAIL); v2 按 run 划分被自纠为方法缺陷(同消息跨半泄漏) ⇒ 其 Q1 PASS 不成立",
       "covers": ["eval/rover/r446/l1_ext_precheck_v2.py", "eval/rover/r446/README-evidence.md"]},
      {"id": "r446.channel-marks-multivariant", "capability": "器具: 判官 prompt 多形态派生(公共前缀标记) + 零回归",
       "level": "L3", "owner_round": "R446",
       "evidence_cmd": "python3 eval/rover/r444/channel_marks.py",
       "evidence_path": "eval/rover/r446/toolregress-channel-marks.json",
       "negative_control": "改动前同脚本抛 ValueError: 未找到 BuildJudgePrompt 函数体(rc=1); 零回归对照: settle 复跑 R444 归档 calls-BRJ-M20-s4 得 32968/13 调用逐位同 + S1 5 档案 match",
       "covers": ["eval/rover/r443/channel_marks.py", "eval/rover/r444/channel_marks.py"]},
      {"id": "r446.judge-prompt-compact", "capability": "判官 prompt 瘦身消融(开关默认关)",
       "level": "L1", "owner_round": "R446",
       "evidence_cmd": "bash eval/rover/r446/run_all_r446.sh",
       "evidence_path": "eval/rover/r446/verdict-r446-analysis-M20.json",
       "negative_control": "N1 非空心: 两臂各须 >=3 条 local 判官行; D4 远端 token 逐位零回归; 分母取同网格 A 臂实测(禁跨网格代理)",
       "covers": ["src/agent.roles/CorrectionDetector.cs", "eval/rover/r446/analyze_r446.py", "eval/rover/r446/grid/task-M20.json"]},
    ]


def kpi_lines(a):
    A, B, C = a["arms"]["A"], a["arms"]["BRJ"], a["arms"]["BRJC"]
    base = {"round": "R446", "grid": a["grid"], "bin_sha": a.get("bin_sha", ""),
            "owner_round": "R446", "evidence_path": "eval/rover/r446/verdict-r446-analysis-M20.json"}
    out = []
    for tag, s in (("A", A), ("BRJ", B), ("BRJC", C)):
        out.append(dict(base, arm=tag, remote_tokens=int(s["remote"]), local_tokens=int(s["local_total"]),
                        judge_local_calls=s["judge_local"], judge_local_tokens=int(s["judge_tok"]),
                        letters="".join(s["letters"])))
    out.append(dict(base, arm="KPI", kpi_brj=round(a["kpi_brj"], 4), kpi_brjc=round(a["kpi_brjc"], 4),
                    checks=a["checks"]))
    return out


def main():
    ap = ROOT / "eval/rover/r446"
    verdict = ap / "verdict-r446-analysis-M20.json"
    if not verdict.exists():
        print("[致命] 双臂分析裁决缺失, 拒绝写台账 (fail-closed)")
        return 2
    a = json.loads(verdict.read_text(encoding="utf-8"))
    # bin_sha 从 arm verdict 里取 (A 臂)
    av = ap / "verdict-A-M20-s1.json"
    if av.exists():
        a["bin_sha"] = json.loads(av.read_text(encoding="utf-8")).get("bin_sha", "")
    if not a["checks"]["D1_字母逐轮一致"]["pass"]:
        print("[警告] D1 字母不一致 ⇒ 台账照记(诚实), 但宣称收窄")
    add_rows(rows_def(a))
    lines = kpi_lines(a)
    with KPI.open("a", encoding="utf-8") as f:
        for l in lines:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    back = [json.loads(x) for x in KPI.read_text(encoding="utf-8").splitlines() if x.strip()]
    got = [x for x in back if x.get("round") == "R446"]
    print(f"[kpi] 追加 {len(lines)} 行, 回读 R446 行 = {len(got)}")
    print(json.dumps({"kpi_brj": a["kpi_brj"], "kpi_brjc": a["kpi_brjc"],
                      "letters_same": a["checks"]["D1_字母逐轮一致"]["pass"],
                      "judge_tok": [a["arms"]["BRJ"]["judge_tok"], a["arms"]["BRJC"]["judge_tok"]]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
