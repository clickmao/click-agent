#!/usr/bin/env python3
"""R432 证据文档生成器 —— README-evidence.md 全部由机检 JSON 生成 (臂1 + 臂2), 不手抄。"""
import json, pathlib

D = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r432")


def J(name):
    p = D / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def esc(s):
    return (s or "").replace("<", "\u276e").replace(">", "\u276f").replace("|", "/")


def crit_table(A, v):
    A("| 判据 | 读数 | 判定 |")
    A("|---|---|---|")
    A(f"| C1 r1 路径判别力（同现 Pass 与 Skip）| r1 判决序列 `{'/'.join(str(x) for x in v['r1_decisions'])}` | "
      f"{'PASS' if v['C1_r1_discriminates'] else 'FAIL'} |")
    A(f"| C1p 组合级判别力（机械门 Pass ∧ r1 Skip）| 机械 {v['gate_mechanical']} 条 / r1 {v['gate_r1']} 条 | "
      f"{'PASS' if v['C1p_pair_discriminates'] else 'FAIL'} |")
    A(f"| C2 同文逐位可复现（ack / cont 各≥2 次同文）| ack raw_len `{v['C2_details'].get('ack',{}).get('raw_len')}` / "
      f"cont raw_len `{v['C2_details'].get('cont',{}).get('raw_len')}` | "
      f"ack={'PASS' if v['C2_ack_repeat_stable'] else 'FAIL'} cont={'PASS' if v['C2_cont_repeat_stable'] else 'FAIL'} |")
    A(f"| C3 时间窗对齐 + 归因 | alignment={v['alignment_ok']}（未命中 {len(v['alignment_unmatched'])} / 歧义 {len(v['alignment_ambiguous'])}）、"
      f"attribution={v['attribution_ok']} | {'PASS' if v['C3_alignment_and_attribution'] else 'FAIL'} |")
    A(f"| C4 隔离旁路负控（无 [隔离任务] 回复）| 命中位 `{v['isolation_hits']}` | {'PASS' if v['C4_no_isolation'] else 'FAIL'} |")
    A(f"| C5 机械负控位不进 r1 | 机械负控位 = `{[s['pos'] for s in v['sequence'] if s['family'] == 'mechanical_control']}`，"
      f"其中 r1 记录 {sum(1 for s in v['sequence'] if s['family'] == 'mechanical_control' and s['branch'] == 'r1')} 条 | "
      f"{'PASS' if v['C5_mechanical_control_ok'] else 'FAIL'} |")
    A("")


def seq_table(A, v):
    A("| 轮 | 族 | 输入 | 分支 | 判决 | basis | raw_len | raw前缀sha16 | cache_n | pinned | prompt_sha | 窗内远端调用 | 回复形态 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for s in v["sequence"]:
        A(f"| t{s['pos']} | {s['family']} | {esc(s['msg'])} | {s['branch']} | {s['decision']} | {esc(s['basis'])} | "
          f"{s['raw_len']} | `{s['raw_prefix_sha16']}` | {s['cache_n']} | {s['pinned']} | `{s['prompt_sha']}` | "
          f"{s['remote_calls_in_window']} | {s['reply_shape']} |")
    A("")
    A(f"- 进门位 `{v['gated_positions']}`；未进门位 `{v['ungated_positions']}`（按 R380「未测到 ≠ 通过」不计入判据分子/分母）")
    A(f"- 桩侧远端调用 {v['remote_calls']} 次；token 估计 {v['prompt_tokens_est']} + {v['completion_tokens_est']} = **{v['total_tokens_est']}**")
    A(f"- 二进制 sha256 `{v['binary_sha256'][:16]}…`（{v['binary_bytes']} B）")
    A("")


def main():
    v1 = J("verdict-C-r432dp1.json"); v2 = J("verdict-C-r432dp2.json")
    prov = J("prov-C-r432dp-r432dp1.json") or J("prov-C-r432dp2-r432dp2.json") or {}
    L = []; A = L.append
    A("# R432 证据 — 门判**判别力**与**确定性**成对判据（残余带内）")
    A("")
    A("本文件由 `make_evidence_r432.py` 从机检 JSON 生成（非手抄）：`verdict-C-r432dp1.json`（臂 1）、`verdict-C-r432dp2.json`（臂 2）、`prov-C-r432dp*-r432dp*.json`（形态闸）。")
    A("")
    A("## 0. 撞号登记（R431 让号 → R432）")
    A("")
    A("- 本侧起手时的占用序列读取被终端截断（只回 1 行）⇒ 曾以 R431 / v0.52.0 命名建器具；复核发现**对侧并发作业已占用 R431 与 v0.52.0**（本侧起臂时在途未提交；对侧随后提交为 `f319198`："
      "`src/agent.modelqueue/LocalGenerationPort.cs`、`ModelQueueRouter.cs`、`src/agent.roles/RoleGrowthLedger.cs`、`IndustrialAgentV2.cs` 的门判遥测 "
      "`gate_prompt_len`/`role_seed_chars`/`growth_chars`/`growth_lines`，加 `src/agent.tests/TurnGateGrowthMountTests.cs` 与 `docs/plans/v0.52.0-r431-growth-mount.md`）。")
    A("- 处置：**本侧让号** ⇒ 轮号 R432、版本号 v0.53.0；r431 命名下的中止臂读数作废；对侧 `src/**`、对侧计划文档与对侧 `eval/rover/r431/**` 一字未动、未 add。")
    A("- 被测二进制 = `/tmp/pub_r430b/agenthost`（**提交态 `627dd23`** 构建）⇒ 与对侧 R431 改动无关；本轮不重发布 AOT。")
    A("")
    A("## 1. 因果链")
    A("")
    A("1. R429（`14b6156`）钉死决策路径前缀缓存 ⇒ 同文门判恒定、token −51.6%，但**判别力负控落空**（新诉求消息走 `[隔离任务]` 旁路，没进 r1 门）⇒ 「钉死后门仍能 Pass/Skip 正确」无证据。")
    A("2. R430（`627dd23`）补上**字节级确定性**（`raw_len_seq` 全等、4/4 同 sha）⇒ 遗留的不对称 = **确定性已证、判别力未证**（用户审计逻辑：只证「恒 Skip」= 空心指标风险）。")
    A("3. 本轮在同一二进制上构造**残余带网格**（机械词表覆盖不到的短消息：`好的`/`继续`/`重来一次`/`那个方案先放放`/`嗯`），"
      "把「同文重复」「对抗输入（语义带纠正/丢弃诉求但机械表未覆盖）」「机械负控」成对放入同一网格。")
    A("4. 仪器改进（相对 R430）：门遥测按 **时间窗**（`gate.ts ∈ [t_start,t_end]`）对齐到唯一轮，弃用 `secs>=5` 位置启发式；归因取桩侧 jsonl 的逐请求时间戳（外部真值）。")
    A("5. 臂 1 机检出**可达位偏移**：可达位 = 奇数位（seed 轮回复含问询 ⇒ 其下一轮被「ask 消费」进计划参数槽，实测 0.04 s、不进门）⇒ 臂 1 预注册族位落在被消费位；"
      "据此**在读数前**预注册臂 2 的**偏移无关网格**（每族 4 连排、负控置可达位）。")
    A("")
    A("## 2. 判据与判决规则（预注册：`docs/plans/v0.53.0-r432-gate-discrimination.md` §2 / §2.1 / §3.1）")
    A("")
    A("- C1 r1 路径判别力；C1p 组合级判别力；C2 同文逐位可复现（ack / cont）；C3 时间窗对齐 + 归因；C4 隔离旁路负控；C5 机械负控位不进 r1。")
    if v2:
        A("- 判决合成：" + v2["verdict_rule"])
    A("")
    A("## 3. 臂 1（网格 `r432dp`，NS `-r432dp1`）— 族位错配读数")
    A("")
    if v1:
        A(f"- 判决 **{v1['verdict']}**（预注册族位落在被 ask 消费的偶数位 ⇒ C2/C5 无法评估；C3 仪器成立：alignment={v1['alignment_ok']} / attribution={v1['attribution_ok']}）")
        A(f"- 门记录 {v1['gate_records_all']}（r1 {v1['gate_r1']} / 机械 {v1['gate_mechanical']}）；r1 判决 `{'/'.join(map(str,v1['r1_decisions']))}`；raw_len `{'/'.join(map(str,v1['raw_len_seq']))}`；"
          f"r1 全部 `prompt_sha` 唯一值 {len({str(s['prompt_sha']) for s in v1['sequence'] if s['branch']=='r1'})} 个 ⇒ 8 条读数**同文**（`嗯`）")
        A(f"- 该臂的 8 条同文读数（每条 raw_len 170、前缀 sha 同、cache_n 0、pinned 递增 1→8）作为 `checks_posthoc` 记录：支持「同文恒定」，但**不**支撑族级 C1/C2")
    else:
        A("- （verdict 缺失）")
    A("")
    A("## 4. 臂 2（网格 `r432dp2`，NS `-r432dp2`）— 族位校正后的裁决读数")
    A("")
    if v2:
        crit_table(A, v2)
        A("")
        seq_table(A, v2)
        A("")
        A(f"- 逐族判决：{json.dumps({k: v for k, v in v2['family_decisions'].items()}, ensure_ascii=False)}")
        A(f"- C2 明细：{json.dumps(v2['C2_details'], ensure_ascii=False)}")
    else:
        A("| （verdict 缺失）| — | 未测到 |")
    A("")
    A("## 4b. 通道分离后验（post-hoc，非预注册）")
    A("")
    A("预注册 C3 用「窗内远端调用数」做归因 ⇒ 被证伪（Skip 轮也出现远端调用）。后验按桩侧**提示签名**分通道重做归因：")
    A("通道 G = 生成/回答通道（system 含「你是一个智能助手」）；通道 J = 关系判官通道（system 恰为「只输出一个字母。」）。")
    A("")
    ch2 = J("channels-C-r432dp2-r432dp2.json"); ch1 = J("channels-C-r432dp-r432dp1.json")
    for tag, ch in (("臂 1", ch1), ("臂 2", ch2)):
        if not ch:
            continue
        ck = ch["checks"]
        A(f"- **{tag}**：桩调用 {ch['calls_total']} = G {ch['channels']['G']} / J {ch['channels']['J']} / 其他 {ch['channels']['?']}；token G {ch['tokens']['G']} / J {ch['tokens']['J']} / 其他 {ch['tokens']['?']}；"
          f"**Skip 轮数 {ck['skip_turns_total']}，其中带 J 调用 {ck['skip_turns_with_J']} 条**；`Pass ⇔ 窗内 G 调用` = {ck['gate_Pass_iff_G_in_window']}")
    if ch2:
        A("")
        A("| 轮 | 族 | 判决 | secs | G | J |")
        A("|---|---|---|---|---|---|")
        for r in ch2["per_turn"]:
            A(f"| t{r['turn']} | {r['family']} | {r['decision']} | {r['secs']} | {r['G']} | {r['J']} |")
        A("")
        A(f"- 结论：**生成通道零泄漏**（Skip 轮 G = 0）⇒ 门判 Skip 的省 token 机制成立；泄漏仅存在于关系判官通道（8 次 × ≈47 token = {ch2['tokens']['J']}），"
          "因果指向「本地判官被门判占死单飞槽 ⇒ 回退远端」（R429 诚实边界 ③ 的因果坐实；未做消融，待下轮隔离）。")
    A("")
    A("## 5. 形态闸（V0，fail-closed）")
    A("")
    ut = (prov.get("under_test") or {}); nc = ((prov.get("negative_controls") or [{}])[0])
    A(f"- 被测 AOT 原生 = {ut.get('native_ok')}（{ut.get('bytes')} B，sha `{str(ut.get('sha256'))[:16]}…`，`env -i` 自启 rc={ut.get('bare_rc')}）")
    A(f"- IL 负控必拒 = {nc.get('bare_rc') == 131}（rc={nc.get('bare_rc')}）⇒ 形态判据有判别力")
    A("")
    A("## 6. 诚实边界 / 排除项")
    A("")
    A("1. 本臂与**对侧并发作业**（R431，后被其提交为 `f319198`）在同一台 2 vCPU / 3.57 GiB 机器上交错；两臂均在「安静窗口闸」（无对侧 dotnet/llama-server 且 MemAvailable ≥ 2650 MB，连续 2 次）后点火，"
      "但**未证明**整段测量期间零重叠。判据不含墙钟项（判定/指纹/对齐均由内容与外部真值决定）。")
    A("2. 被测二进制 = 提交态 `627dd23` 的 AOT；对侧 R431 改动当时仍在工作树（现已提交为 `f319198`）⇒ 本轮不重发布 AOT，也不宣称「与工作树一致」。")
    A("3. 遥测 `raw` 截断到 120 字符 ⇒ 前缀 sha 仅覆盖前 120 字符；`raw_len` 另行给出（本臂 raw_len 170 ⇒ 尾部 50 字符未逐字节覆盖）。")
    A("4. 判据只在**进了门的轮**上成立；未进门轮记 `ungated`（臂 1 的 18 轮中有 9 轮未进门）。")
    A("5. 「可达位偏移」（seed 后第 2 轮被 ask 消费）本身是**产品/驱动交互的实测性质**；臂 2 用 4 连排设计使其与本判据无关，但该偏移未被单独隔离验证。")
    A("6. 单机单次读数；不宣称跨机/跨构建/跨上下文长度可复现。")
    A("")
    A("## 7. 复现命令")
    A("")
    A("```bash")
    A("bash /tmp/r432_fire.sh    # 安静窗口闸 v2（排除空闲构建服务 MSBuild/VBCSCompiler）")
    A("AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r430b/agenthost R432_NS=-r432dp1 bash eval/rover/r432/run_arm.sh C r432dp  47930 47931 /home/agentuser/AgentFramework/skeptic.rbin")
    A("bash /tmp/r432_fire2.sh   # 臂 2 点火闸")
    A("AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r430b/agenthost R432_NS=-r432dp2 bash eval/rover/r432/run_arm.sh C r432dp2 47930 47931 /home/agentuser/AgentFramework/skeptic.rbin")
    A("python3 eval/rover/r432/make_evidence_r432.py")
    A("```")
    A("")
    (D / "README-evidence.md").write_text("\n".join(L), encoding="utf-8")
    b = (D / "README-evidence.md").read_bytes()
    print("README-evidence.md", len(b), "B,", b.decode().count("\n"), "lines, tail:", repr(b.decode()[-32:]))


if __name__ == "__main__":
    main()
