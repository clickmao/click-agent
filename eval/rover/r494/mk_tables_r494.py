#!/usr/bin/env python3
# R494 表格发生器 —— 报告里的**每个数字**都从产物派生 (禁手抄)。
# 输出: eval/rover/r494/tables-r494.md (供 docs/reports/r494-*.md 引用)
import json, os, subprocess, sys

D = "/home/agentuser/AgentFramework/eval/rover/r494"
OUT = os.path.join(D, "tables-r494.md")

def jl(p):
    if not os.path.exists(p): return []
    with open(p, encoding="utf-8-sig") as f: return [json.loads(l) for l in f if l.strip()]

def load(p):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

def main():
    kpi = load(os.path.join(D, "kpi-r494.json"))
    base = load(os.path.join(D, "kpi-r494-baseline.json")) or load(os.path.join(D, "baseline-r493-kpi.json"))
    ev = load(os.path.join(D, "evidence-r494.json")) or {}
    L = []
    L.append("### 1) 臂矩阵 (机取, 来自 flags-<arm>.json)\n")
    L.append("| 臂 | turn_gate | repeat_skip | 声明门(意图轴) | **通道轴** | pair_trim | host_sha12 |")
    L.append("|---|---|---|---|---|---|---|")
    for a in ("B", "T0", "T1"):
        f = load(os.path.join(D, "flags-%s.json" % a))
        if not f: continue
        L.append("| %s | %s | %s | %s | **%s** | %s | %s |" % (
            a, f.get("turn_gate"), f.get("repeat_skip"), f.get("tool_decl_gate"),
            f.get("tool_decl_channel"), f.get("replay_pair_trim"), (f.get("host_sha256") or "")[:12]))
    L.append("")
    L.append("### 2) 逐臂 KPI (机取, 来自 usage/calls 产物)\n")
    L.append("| 臂 | 远端调用 | total_tokens | prompt_tokens | cached_tokens | 新算 tokens | completion | 隔离调用 | 隔离调用带工具 | 带工具调用总数 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    if kpi:
        for a in ("B", "T0", "T1"):
            s = kpi["arms"].get(a)
            if not s: continue
            newt = s["prompt_tokens"] - s["cached_tokens"]
            L.append("| %s | %d | %d | %d | %d | %d | %d | %d | **%d** | %d |" % (
                a, s["calls"], s["total_tokens"], s["prompt_tokens"], s["cached_tokens"], newt,
                s["completion_tokens"], s["iso_calls"], s["iso_calls_with_tools"], s["calls_with_tools"]))
    L.append("")
    L.append("### 3) 阶梯差 (同窗单变量)\n")
    L.append("| 对照 | calls | Δcalls | tokens | Δtokens |")
    L.append("|---|---|---|---|---|")
    if kpi:
        for l in kpi["ladder"]:
            L.append("| %s | %s→%s | %+.1f%% | %s→%s | %+.1f%% |" % (
                l["pair"], l["calls"][0], l["calls"][1], l["calls_drop_pct"],
                l["total_tokens"][0], l["total_tokens"][1], l["total_tokens_drop_pct"]))
    L.append("")
    if base:
        L.append("### 4) 跨轮对照 (R493 同网格基线, 仅作竖直参照 —— 禁与 R494 相减)\n")
        L.append("| R493 臂 | 旗标 | 远端调用 | total_tokens |")
        L.append("|---|---|---|---|")
        for a, fl in (("B(R493)", "全关"), ("R(R493)", "gate+skip"), ("T(R493)", "gate+skip+声明门+pair_trim")):
            st = base.get(a.split("(")[0])
            if st: L.append("| %s | %s | %d | %d |" % (a, fl, st["calls"], st["total_tokens"]))
        L.append("")
    L.append("### 5) 实发面断言 (机跑, assert_face_r494.py)\n")
    L.append("```")
    L.append(ev.get("assert_face", "(未采集)").rstrip())
    L.append("```\n")
    L.append("### 6) 判据器读数 (judge_adv_r494.py, 与 R493 逐字节同)\n")
    L.append("| 臂 | 对抗族 PASS | endorse | swallowed |")
    L.append("|---|---|---|---|")
    for a in ("B", "T0", "T1"):
        adv = load(os.path.join(D, "adv-%s.json" % a))
        if not adv: continue
        L.append("| %s | %s/%s | %s | %s |" % (a, adv.get("pass_n"), adv.get("total"), adv.get("endorse_n"), adv.get("swallowed_n")))
    L.append("")
    L.append("### 7) 器具与产物 (机取)\n")
    for k in ("aot_size_bytes", "aot_sha256", "il_warnings", "test_total", "test_passed", "test_failed",
              "grid_sha256", "judge_sha256", "host_sha256"):
        if k in ev: L.append("- `%s` = `%s`" % (k, ev[k]))
    L.append("")
    L.append("### 8) 能力自检面只读复核 (候选④)\n")
    au = load(os.path.join(D, "audit-capability-face.json"))
    if au:
        L.append("verdict=**%s** · 断言 %d · 红 %d · 只读(未写 eval/capability/)\n" % (
            au.get("verdict"), len(au.get("assertions", [])), au.get("red_count", 0)))
        L.append("| 面文件 | face | 注入 | total/passed | rc(红项) |")
        L.append("|---|---|---|---|---|")
        for f in au.get("faces", []):
            if not f.get("present"): continue
            bad = ",".join("%s(rc=%s)" % (r["id"], r["rc"]) for r in f.get("rows", []) if r.get("pass") is False)
            L.append("| %s | %s | %s | %s/%s | %s |" % (f["file"], f.get("face"), f.get("inject_mode") or "-",
                                                          f.get("passed"), f.get("total"), bad or "-"))
    L.append("")
    open(OUT, "w", encoding="utf-8").write("\n".join(L))
    print("[tables] → %s (%d 行)" % (OUT, len(L)))
    return 0

if __name__ == "__main__":
    sys.exit(main())
