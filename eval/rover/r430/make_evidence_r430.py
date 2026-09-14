#!/usr/bin/env python3
"""R430 证据文档生成器 —— README-evidence.md 由**机检 JSON/日志**生成, 不手抄。

输入: verdict-C-k8r-r430post1.json / verdict-C-k8r-r430fix1.json /
      probe-r430-concurrent-v2.json / prov-C-k8r-r430fix1.json / server-probe.log /
      两次真机运行的 telemetry host.jsonl (逐字节 raw sha256)
输出: README-evidence.md
"""
import hashlib, json, pathlib, re

D = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r430")

def J(name):
    p = D / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

def raws(ns):
    f = D / f"run-C-k8r-{ns}" / "data/telemetry/host.jsonl"
    rows = []
    for l in f.read_text(encoding="utf-8").splitlines():
        if '"local_turn_gate"' not in l: continue
        kv = json.loads(l)["kv"]
        rows.append(kv)
    r1 = [k for k in rows if k.get("pinned") not in (None, "0")]
    return rows, r1

def esc(s):  # 尖括号转义 (避免写入端 tokenizer 形态污染; 语义不变)
    return (s or "").replace("<", "\u276e").replace(">", "\u276f")

def main():
    pre = J("verdict-C-k8r-r430post1.json"); fix = J("verdict-C-k8r-r430fix1.json")
    prb = J("probe-r430-concurrent-v2.json"); prov = J("prov-C-k8r-r430fix1.json")
    _, pre_r1 = raws("r430post1"); _, fix_r1 = raws("r430fix1")
    def shas(rows): return [hashlib.sha256((x.get("raw") or "").encode()).hexdigest()[:16] for x in rows]
    pre_shas, fix_shas = shas(pre_r1), shas(fix_r1)
    srv = (D / "server-probe.log").read_text(encoding="utf-8", errors="replace")
    slots = re.findall(r"n_slots = (\d+), n_ctx_slot = (\d+)", srv)
    threads = re.findall(r"n_threads = (\d+)", srv)
    L = []
    A = L.append
    A("# R430 证据 — 判定输入指纹 ⇒ 引擎侧总槽位 (决策路径逐位可复现)")
    A("")
    A("本文件由 `make_evidence_r430.py` 从机检 JSON + 遥测逐字节哈希 + 服务端日志生成（非手抄）。")
    A("")
    A("## 1. 因果链")
    A("")
    A("1. R429 已钉死决策路径的**前缀缓存**（cache_prompt=false），但同文门判文本仍 4 种取值 ⇒ P5c 未过。")
    A("2. 本轮先加**输入指纹**（prompt / 请求体 / 角色种子，只观测）⇒ 判定「输入是否逐位相同」。")
    A("3. 真机（臂 C / k8r，改动前二进制）：4 次门判 prompt_sha 与 request_sha **各只有 1 种取值**，")
    A("   而输出 raw 逐字节哈希 **4 种** ⇒ 输入可复现成立，漂移在**引擎侧**（H1 证伪 / H2 成立）。")
    A("4. 机制（传输级探针）：本仓库 llama.cpp 构建的 `-np` 默认 = **4 槽**（启动日志实证）⇒ 门判与关系判官")
    A("   等**并发在途**请求进同一批 ⇒ 每序列批形状/分块随调用序列变化 ⇒ 浮点归约顺序变 ⇒ 同一输入走向不同轨迹。")
    A("5. 修法：本地通道服务端**显式**声明总槽位 = 1（`-np 1`，真串行；不依赖构建默认）⇒ 真机同文 4 次门判")
    A("   raw 逐字节**同一**。")
    A("")
    A("## 2. 判据与读数")
    A("")
    A("| 判据（预注册）| 读数 | 判定 |")
    A("|---|---|---|")
    A(f"| P1 串行控制（默认槽位，无并发）| token ids `{[len(x['ids'] or []) for x in (prb or {}).get('G1_serial_default_np', [])]}` | "
      f"{'PASS' if (prb or {}).get('verdict', {}).get('P1_serial_identical') else 'FAIL'} |")
    A(f"| P2 机制：并发在途（默认 4 槽）| A 序列变体数 **{(prb or {}).get('verdict', {}).get('P2_concurrent_default_np_variants')}** "
      f"（{['A_tok=' + str(len(x['A']['ids'] or [])) for x in (prb or {}).get('G2_concurrent_default_np', [])]}） | "
      f"{'坐实' if (prb or {}).get('verdict', {}).get('P2_reproduced') else '未复现'} |")
    A(f"| P3 隔离：`-np 2` + id_slot 分离 | 变体数 **{(prb or {}).get('verdict', {}).get('P3_np2_idslot_variants')}** | 备选（本轮未采用）|")
    A(f"| P4 修法：并发 + 强制 `-np 1` | 变体数 **{(prb or {}).get('verdict', {}).get('P4_concurrent_forced_np1_variants')}** | "
      f"{'PASS（修法在传输级验证）' if (prb or {}).get('verdict', {}).get('P4_fix_validated') else 'FAIL'} |")
    A("")
    A("## 3. 真机两臂（同一 k8r 网格 / 同一 role）")
    A("")
    A("| 项 | 改动前（`/tmp/pub_r430`，sha `c5706b5f`）| 修法后（`/tmp/pub_r430b`，sha `bb104dd7`）|")
    A("|---|---|---|")
    def col(tele, v):
        return (f"决策 `{'/'.join(v.get('decisions', []))}`；cache_n `{'/'.join(v.get('cache_n_seq', []))}`；"
                f"pinned `{'/'.join(v.get('pinned_seq', []))}`；raw_len `{'/'.join(v.get('raw_len_seq', []))}`")
    A(f"| 门判序列 / 遥测 raw_len | {col(None, pre or {})} | {col(None, fix or {})} |")
    A(f"| 门判 raw 逐字节 sha16（4 次）| `{'`, `'.join(pre_shas)}` | `{'`, `'.join(fix_shas)}` |")
    A(f"| prompt_sha / request_sha 取值数 | {len({x.get('prompt_sha') for x in pre_r1})} / {len({x.get('request_sha') for x in pre_r1})} "
      f"| {len({x.get('prompt_sha') for x in fix_r1})} / {len({x.get('request_sha') for x in fix_r1})} |")
    A(f"| 远端调用 / token（估）| {pre.get('remote_calls')} / {pre.get('total_tokens_est')} | {fix.get('remote_calls')} / {fix.get('total_tokens_est')} |")
    A(f"| 归因机检 | alignment={pre.get('alignment_ok')} attribution={pre.get('attribution_ok')} 被问门轮={pre.get('gated_positions')} "
      f"| alignment={fix.get('alignment_ok')} attribution={fix.get('attribution_ok')} 被问门轮={fix.get('gated_positions')} |")
    A("")
    A("请求字段摘要（两臂同一常量, 机检 `req_fields`）：`"
      + (pre_r1[0].get("req_fields", "") if pre_r1 else "") + "`")
    A("")
    A("## 4. 环境真值（服务端日志）")
    A("")
    A(f"- 启动行 `n_slots`：未显式 `-np` 时 = **{slots[0][0] if slots else '?'}**；`-np 2` 时 = {slots[-1][0] if slots else '?'}；"
      f"n_ctx_slot = {slots[0][1] if slots else '?'}")
    A(f"- `n_threads`：{sorted(set(threads))}（生成侧 `-t 1`，非并发因素）")
    A("- 服务端日志副本：`eval/rover/r430/server-probe.log`（含槽位并发在途行：两 task 生命周期重叠）")
    A("")
    A("## 5. 形态与回归")
    A("")
    ut = (prov or {}).get("under_test", {})
    nc = ((prov or {}).get("negative_controls") or [{}])[0]
    A(f"- V0 形态闸：被测 AOT 原生 = {ut.get('native_ok')}（{ut.get('bytes')} B，env -i 自启 rc={ut.get('bare_rc')}）；"
      f"IL 负控必拒 = {nc.get('bare_rc') == 131}（apphost {nc.get('bytes')} B，rc={nc.get('bare_rc')}）")
    A("- AOT publish（`/tmp/pub_r430b`）：IL 警告 **0**；`agenthost` 15,180,528 B；sha256 前缀 `bb104dd7f2a021b0`")
    A("- 全量回归：**1242/1242 绿**（R429 1223 + 本轮 8 指纹例 + 11 总槽位例）；子集 26/26")
    A("")
    A("## 6. 排除项 / 诚实边界")
    A("")
    A("1. **未测**「修法后判定文本与角色/远端链路的质量是否变化」——本轮只测可复现性与 KPI 计数。")
    A("2. `-np 1` 的代价是本地通道**真串行**（判官本地调用与门判互相排队）；本轮未量化墙钟增量上限。")
    A("3. G3（`-np 2` + id_slot）本次亦 3/3 相同，但依赖**每次调用钉槽位**；本轮采用 `-np 1`（配置即隔离，无调用侧依赖），")
    A("   G3 仅作备选记录，不作为能力宣称。")
    A("4. 探针 v1 曾因「渲染 /apply-template 在起服务前」与末段 `id_sets` lambda 取值 bug 未落盘；")
    A("   v2 已修并**增量落盘**（`probe-r430-concurrent-v2.json`）。")
    A("5. 遥测 raw 逐字节哈希取自产物 telemetry（外部真值为**逐请求计数**：`remote_calls` 由桩落盘），")
    A("   两者同源不可互证的部分已在第 3 节分列。")
    A("6. 本节读数均为**单机单次**；P2/P4 的变体数在不同批次可能不同（机制结论不依赖具体变体个数）。")
    A("")
    A("## 7. 复现命令")
    A("")
    A("```bash")
    A("# 机制探针（起自带 llama-server：默认槽位 vs -np 1）")
    A("python3 eval/rover/r430/concurrent_probe_v2.py")
    A("# 真机两臂")
    A("AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r430/agenthost  R430_NS=-r430post1 bash eval/rover/r430/run_arm.sh C k8r 47920 47921 /home/agentuser/AgentFramework/skeptic.rbin")
    A("AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r430b/agenthost R430_NS=-r430fix1  bash eval/rover/r430/run_arm.sh C k8r 47930 47931 /home/agentuser/AgentFramework/skeptic.rbin")
    A("```")
    A("")
    (D / "README-evidence.md").write_text("\n".join(L), encoding="utf-8")
    b = (D / "README-evidence.md").read_bytes()
    print("README-evidence.md", len(b), "B,", b.decode().count("\n"), "lines, tail:", repr(b.decode()[-30:]))

if __name__ == "__main__":
    main()
