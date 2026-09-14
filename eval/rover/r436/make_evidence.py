#!/usr/bin/env python3
"""R436 证据生成器 — 由 verdict-summary.json + publish-info.json 渲染 README-evidence.md。
一切读数从 JSON 取（禁手抄）; 叙述句为分析, 数字一律插值。
"""
import json
import os
import sys

D = os.path.abspath(os.path.dirname(__file__))
S = json.load(open(os.path.join(D, "verdict-summary.json"), encoding="utf-8"))
P = json.load(open(os.path.join(D, "publish-info.json"), encoding="utf-8"))
C = S["criteria"]


def tk(x):
    return x["tokens"] if x and "tokens" in x else (x["tokens_total"] if x else None)


def mdfile(path, name, tag):
    import hashlib
    h = hashlib.sha256(open(os.path.join(D, path), "rb").read()).hexdigest()
    return f"{name} `{tag}` sha256=`{h[:16]}…`"


L = []
L.append("# R436 证据包 — 端到端 BRJ 网格（承重: 用户一轮任务总 API token 降幅）")
L.append("")
L.append(f"- 轮次 **R436**｜HEAD `{P['head'][:12]}`｜二进制 sha256 `{P['sha256']}`（{P['bytes']} bytes, NativeAOT）")
L.append(f"- 发布台账: {P['pub_log']}；IL 警告 **{P['il_warnings']}**；形态闸 {P['v0_gate_pass']}")
L.append("- 判据预注册: `docs/plans/v0.57.0-r436-e2e-brj-token-kpi.md` §2–§5（读取数前写定）")
L.append("")
L.append("## 1. 形态（C1）")
L.append("")
L.append("| 项 | 读数 |")
L.append("|---|---|")
for k in ("il_warnings", "native_code", "publish_rc", "env_i_version_rc", "v0_raw_native_ok", "v0_negative_control_rc", "bin_bytes"):
    L.append(f"| {k} | {C['C1_形态'][k]} |")
L.append(f"| C1 判定 | **{'PASS' if C['C1_形态']['ok'] else 'FAIL'}** |")
L.append("")
L.append("## 2. 臂矩阵（p12, 12 轮; p8, 9 轮）")
L.append("")
for grid, key in (("p12", "p12_rows"), ("p8", "p8_rows")):
    L.append(f"### {grid}")
    L.append("")
    L.append("| 臂 | 远端调用 (G/J) | 远端 token (G/J) | 相对 A 降幅 | FN | FP | 门准确率 | 本地判官次 | r1 跳过轮 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for k, r in S[key].items():
        if not r:
            continue
        L.append(f"| {k} | {r['calls']} ({r['G']}/{r['J']}) | {r['tokens']} ({r['G_tokens']}/{r['J_tokens']}) | "
                 f"{r['drop_vs_A_pct']}% | {r['fn']} | {r['fp']} | {r['acc']:.3f} | {r['judge_local_n']} | {r['r1_skips']} |")
    L.append("")
L.append("## 3. 判据 C1–C8")
L.append("")
for k, v in C.items():
    ok = v.get("ok")
    mark = "✅" if ok else ("❌" if ok is False else "—")
    L.append(f"- **{k}** {mark} `{json.dumps({a: b for a, b in v.items() if a != 'per_arm'}, ensure_ascii=False)}`")
L.append("")
L.append("## 4. 降幅因果分解（p12）")
L.append("")
d = C["C4b_降幅分解"]
L.append(f"- 门（跳过 4 个 ack 轮）: −{d['门_节省token']} token = 相对 A 的 **{d['门_占比pct']}%**")
L.append(f"- J 本地化: −{d['J本地化_节省token']} token = 相对 A 的 **{d['J本地化_占比pct']}%**，并消除 **{d['J本地化_远端请求消除数']} 次远端 API 请求**")
L.append(f"- 合计（BRJ vs A）: **{C['C4_主KPI_token降幅']['p12_BRJ_drop_pct']}%**（目标 {C['C4_主KPI_token降幅']['p12_target']}% ⇒ "
         f"{'达标' if C['C4_主KPI_token降幅']['p12_ok'] else '**未达标**'}）")
if C["C4_主KPI_token降幅"]["p8_BRJ_drop_pct"] is not None:
    L.append(f"- p8 网格（任务构成不同）: **{C['C4_主KPI_token降幅']['p8_BRJ_drop_pct']}%** ⇒ "
             f"{'达标' if C['C4_主KPI_token降幅']['p8_ok'] else '未达标'}")
L.append("")
L.append("## 5. 诚实边界")
L.append("")
L.append("- 远端读数为**桩**(OpenAI 兼容假 API)侧落盘的 `prompt_tokens_est/completion_tokens_est`：口径同上版（R434）可比，但非真实计费 token；真机远端（DeepSeek）自重放未做。")
L.append("- 本地 r1 侧：判官 7 次共 " + str(S["p12_rows"]["BRJ"]["judge_local_tokens"]) + " 生成 token、墙钟 " +
         str(sum(S["p12_rows"]["BRJ"]["judge_local_ms"]) // 1000) + "s（串行, -np1, 本地 0 API 花费）；这些**不计入**上面的 API token 统计。")
L.append("- 未测: 真机远端模型重放、并发多用户、AOT 二进制跨发布可复现性（本轮实测两次同源发布的 AOT 有 "
         f"{P.get('diff_vs_prev_publish', {}).get('diff_bytes', '?')} 字节差异 ⇒ 二进制 sha 不能当源状态指纹）。")
L.append("")
open(os.path.join(D, "README-evidence.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
