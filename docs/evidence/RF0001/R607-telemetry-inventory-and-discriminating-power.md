# R607 · RF0004.0 盘点+打点（零产品改动）：三面打点盘点 + 打点面判别力真机行使

- 轮次: R607 | 日期: 2026-09-21 | 类型: 里程碑盘点轮（**零产品源码改动**，提交面零 `src/`）
- 权威面: `docs/plans/RF0004-three-capability-development-plan.md` §3 出口闸（R607 行）+ §4 排期；协议 `docs/plans/RF0005-completion-protocol.md` §2 固定环 0–9
- 起手闸: `python3 tools/roundcheck/roundcheck.py preflight --round R607 --min-avail-mb 285 --min-disk-gb 1 --need-key AGENTFRAMEWORK_KEYS_DEEPSEEK` ⇒ **rc=0**（285 = r603 洁净窗 swing；R606 无自产 window-samples ⇒ 沿用）
- 二进制: `src/agent.host/bin/Release/net10.0/agenthost`，**从现盘 src 重建**后 sha256 `fe1fb720fb5eedb044014b1c27cd18352e851960102f93920bfb2f57e0820dd3` = **与 R583 登记的 sha 逐位相同** ⇒ 重建可复现、二进制与 HEAD（`f8128c6b`）同源（R583 的 bin 与现盘 mtime 新于它的文件只是 mtime 差异，内容未变）

---

## 1. 盘点的对象与口径（RF0004 §0.3 / §7.4）

RF0004 的三能力面 = ①开放域识别出口 ②生成类档 ③多轮工具编排。RF0004.0 的出口闸 = 「**打点面治疗 >0 且对照 ==0** ∧ 全量绿 ∧ 恒前缀 ≥97% ∧ 起手闸 rc=0」。因此本轮要回答两个问题：

1. **三面各有哪些既有打点、发射点在现盘哪一行、是否被主链消费**（= 盘点件，可机检，防漂移）；
2. **打点面是否真有判别力**（能区分「机制在」与「机制不在」），而不是「有代码行」或「有生成就跑」的错觉。

## 2. 盘点件（新增，可机检）

`eval/rover/r607/inventory_r607.py`（--write 生成 / --check 现盘核对）：

- 15 键 / 3 面，逐键记录 **发射点（file:line，由现盘 grep 派生，不手打）**、**独立发射点计数**、**现读数（`data/telemetry/host.jsonl` 全史计数）**、**面/键缺口**；
- 缺口的判据 = `emit_count_sites == 0`（面级：编排面 `ActionLoopRunner.cs` 的 `Emit(` 计数），非「我觉得没有」；
- 机检 = 逐键断言「发射点仍在现盘该行 ∧ 该行含该键字面」；**负控（有牙）**：故意错一格行号 ⇒ 必判红；错键名 ⇒ 必判红；
- 自检 + 负控在 `--check` 内每次同跑，rc：0 过 / 1 漂移 / 2 器具缺陷（自检或负控不成立）/ 3 输入缺失。
- **C3 读数判据 = 追加单调不变量（v2 修，自捕仪器缺陷）**：`data/telemetry/host.jsonl` **只追加** ⇒ 现读数只增不减；v1 写「逐键相等」⇒ 盘点件落盘后**每次新轮都会把 C3 判红**（实测跑完本轮 6 臂后 8 键全体「漂移」，读起来像盘点过期，实为「追加」这一正常动作）⇒ **判据与语义脱钩**。改为 `disk >= inventory`（回退才判红）并把 `delta = disk − inventory` 一并落盘（本轮实测全键 delta=0）。**注意：C3 的这个假红只在跑后出现，跑前不值绿也不值红 —— 它是「盘点件冻结值 vs 追加日志」的口径问题，不是被测失效；负控仍在 C1/NC（改错发射点行号必判红）。**

**盘点读数（本轮实测，`telemetry-inventory-r607.json`）**

| 面 | 键数 | 主链消费 | 全史读数 | 缺口（现盘事实） |
|---|---|---|---|---|
| 开放域识别出口 | 3（`local_turn_gate_config` / `local_turn_gate` / `nlp_shape`） | ✅ 有（`IndustrialAgentV2` 直发 + `TurnGateJudge` 判定） | 319 / 16 / 19 行 | **无统一 `{标签\|abstain, 依据}` 出口打点**（RF0004.1 的前置） |
| 生成类档 | 3（`tool_decl_gate` 不计入；实为 `TaskKindHint` 五档） | ⚠ 部分 | — | **`TaskKindHint` 无 `Generation` 档** ⇒ 生成面**结构性无档**（RF0004.3 前置） |
| 多轮工具编排 | 0 | — | — | **`ActionLoopRunner.cs` 与 `ActionLoopGate.cs` 的 `Emit(` 计数 = 0** ⇒ 编排面**零专用打点**（RF0004.2 前置） |

> 这三条缺口就是 RF0004.1–RF0004.3 的**开工前置**：不是「先实现能力再补打点」，而是「先有判别力打点才谈消融」。本轮把该结论从散文变成 `--check` 可核对的件。

## 3. 打点面判别力的真机行使（本轮主证据）

**单变量** = `AGENTFRAMEWORK_GATE_REPEAT_SKIP`（`TurnGateJudge.cs` 读；`!= "off"` ⇒ 缺省 on）
- T 臂 = **未设**（产品缺省档，重复轮直 Skip）
- C 臂 = **显式 `off`**
- 两侧同二进制（sha256 见上）、同夹具、同轮序、同 role；**唯一自由度 = 该环境变量**。

**夹具与轮序 = 逐字复用，不重造**（禁新增夹具）
- `eval/rover/r583/turns-S0.txt`（2 轮：wythoff 提问 → 「重新来一遍」）
- `data/nlp/gate-shapes.txt` ← `eval/rover/r583/fixture-shapes-line1.txt` 逐字（sha256 `c98f8ab3e8a49acb5363ae62920fca9174b25dced7a8430dcb1870347cb05a8d`），跑后 `rm -rf data/nlp` 复原为 **absent**（回读断言 OK）
- reps = 3/臂，严格串行，逐臂独立 session（`r607t{1,2,3}` / `r607c{1,2,3}`），6/6 rc=0，耗时 11–31 s

**读数（`verdict-r607.json`，打点面三键，逐臂 1 行内）**

| 臂 | rep | `local_turn_gate{verdict=Skip}` | `nlp_shape{shape=1∧face=repeat∧route=local_skip}` | `local_gate_skip_reply{kind=repeat_verbatim}` |
|---|---|---|---|---|
| T | 1 / 2 / 3 | 1 / 1 / 1 | 1 / 1 / 1 | 1 / 1 / 1 |
| C | 1 / 2 / 3 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |

⇒ **治疗面 >0（三个键、三个跑次全 >0）∧ 对照面 ==0（三个键、三个跑次全 ==0）**，判据 P1/P2 PASS。

**轴归因（同输入指纹，`checks_posthoc`，不入 verdict）**：两臂 turn2 的输入指纹**逐位相同**（`msg_sha16 = 147757f75f39bd44`），但 `basis` 互斥：

```
T  msg 147757f7…  basis = mechanical:repeat→local     （+ local_gate_skip_reply kind=repeat_verbatim, chars=477）
C  msg 147757f7…  basis = mechanical:nonack→remote
```

⇒ 差异**只**来自门轴判定，不是输入/环境差异。这是「单变量净」的直接证据（同 `msg_sha16` 配对）。

## 4. 判决（机制面 / 能力面分判）

| 面 | 判据 | 结果 | rc |
|---|---|---|---|
| 机制面 P1 治疗>0 | T×3 三键各 ≥1 | **PASS**（[1,1,1]×3） | 0 |
| 机制面 P2 对照==0 | C×3 三键逐一 ==0 | **PASS**（[0,0,0]×3） | 0 |
| 前置 P3 闸前置 | 每跑次 `local_turn_gate_config{turn_gate_enabled=真 ∧ role=skeptic}` | **PASS**（6/6） | 0 |
| 恒前缀 P4 | 冻结不变量 `F_env.prefix.chars`=15291 ∧ sha `f1280f71…4d4a` 现盘核对 | **PASS**；命中率 ≥97% **未测**（REPL 面不产恒前缀命中口径，无中继 dump） | 0 |
| 器具 P5 有牙 | 负控（向 C 注入一条 Skip 行 ⇒ P2 必红）∧ 非平凡（T/C 读数互异） | **PASS** | 0 |
| 能力面 | — | **本轮未行使**（零产品改动；无质量对照臂，见 §6 跳步） | — |

**汇总 rc=0**（`eval/rover/r607/judge_r607.py` ⇒ `verdict=PASS`）。

## 5. 器具缺陷与披露式重注册（v1 → v2，阈值不变）

- **v1（保留）**：`eval/rover/r607/verdict-r607-v1-RED-boolexact.json` ⇒ `VOID(rc=3)`，失败项 P3/P1/P2/P5。
- **v1 根因 = 读数口径错（器具缺陷，非被测失效）**：`turn_gate_enabled` 以 .NET `bool.ToString()` 形态落盘为 **`"True"`**，判据器按字面 `"true"` 比较 ⇒ 前置判 False ⇒ 有效跑次 0 ⇒ P1/P2/P5 连带失败。这正是「裁决器报 RED 的第一假设是器具读法错」。
- **v2（本件）**：只加读数归一 `_boolish()`（`"True"/"true"/1` ⇒ 真；缺失/其它 ⇒ None，fail-closed），**阈值与判据集一字未改**；原始遥测与字节偏移未变 ⇒ **同一跑次复判，非重跑、无新臂、无新窗**。
- **防回归**：`_boolish` 两侧形态（`.NET` 与 JSON）写入判据器头部**影子自检**（assert 不过即 rc=2），v1 缺陷不可能静默回来。
- 纪律遵守：**判据器改版禁相减** —— v1 的 VOID **未翻案**，v1 文件原样保留并单列。

## 6. 门禁与构建读数（收口硬读数）

| 项 | 命令 | 读数 |
|---|---|---|
| 构建 | `dotnet build src/agent.host/agent.host.csproj -c Release` | **0 Error(s)** / 10 Warning(s)，39.17 s（重建后二进制 sha256 = R583 登记值，逐位相同） |
| 形式门禁 | `dotnet test … --filter "VerificationForm|SkillGeneralization|DevPlanDocRef"` | **14/14** PASS（首跑 13/14：R2e 冻结 pin 判红，根因 = 登记表 `artifact_sha12` 误钉 `verdict` 而非证据文档 ⇒ 重钉后转绿） |
| 全量 | `dotnet test src/agent.tests/agentframework.tests.csproj` | **1942/1943**（1 红 = `PromptCacheChannelTests.溯源_夹具必须是活遥测的子集不得凭空造数`，**与 R606 登记的「前置红」同形**：遥测错误行缺 `prompt_tokens`，与本轮零产品改动无关） |
| 收口机检 | `python3 eval/capability/status_gen.py --check` | **PASS**（违规 0 / 基准漂移 0 / 缺源 0） |
| 器具声明 | `python3 eval/capability/decl_sweep.py` | **0 处漂移**（提交钩子同跑） |
| 轮次审计 | `python3 tools/roundcheck/roundcheck.py audit --round R607` | 见提交后重跑 |

## 7. 跳步与诚实边界

| 项 | 状态 | 一行原因 |
|---|---|---|
| AOT 发布面 | **跳步** | 零产品源码改动（提交面 `src/` = 0）；且 publish 会抬高同窗 `PREV_SWING`（RF0004 §6.2）⇒ 不在本轮 publish |
| C1 codex 外部真值臂 | **跳步** | 打点面盘点轮无质量对照项（§3 出口闸不含质量列），codex 臂对「打点是否可区分」零信息量（见 `prereg-r607.json::arm_table_deviation`） |
| 恒前缀命中率 ≥97% | **未测** | REPL 面不产恒前缀命中口径（无中继 dump）⇒ 只报冻结不变量现盘核对，不报命中率 |
| 三面的能力收益 | **未测** | 三面均未接线（§2 缺口表），本轮只行使**打点面**，禁作能力宣称 |
| 窗集 | 本轮为 REPL 臂，非 w1xx 题集窗；与历史轮**不相交**（新 session 命名空间 `r607*`） | — |

## 8. 收口五件

1. 轮工件：`eval/rover/r607/{dag-r607.json, prereg-r607.json, inventory_r607.py, telemetry-inventory-r607.json, telemetry-inventory-r607-verdict.json, run_r607.sh, offsets-r607.json, arm-meta.txt, pre-arm-state.txt, gate-pre-r607.txt, arm-T-r{1,2,3}.out.txt, arm-C-r{1,2,3}.out.txt, judge_r607.py, verdict-r607.json, verdict-r607-v1-RED-boolexact.json, close_r607.py}`
   - 归档名注：臂日志原以 `.log` 落盘，命中 `eval/rover/.gitignore:6:*.log` ⇒ 证据不入库 ⇒ 跑后改为 `.out.txt`（逐字复用 r583 的 `arm-*.out.txt` 约定），**仅命名变更、字节未动**；`run_r607.sh` 同步改写落盘名。
2. 证据文档：本件
3. registry 行：`r607.telemetry-inventory-and-discriminating-power`（`docs/verification-registry.json`）
4. kpi 行：`eval/capability/kpi.jsonl`（带 `baselines` id 列表）
5. 提交：本仓库一次本地 commit（推送暂停令在效，禁 push）

## 9. 复现命令

```bash
cd /home/agentuser/AgentFramework
set -a; . ~/.agentframework/keys.env; set +a
python3 eval/rover/r607/inventory_r607.py --check      # 盘点 + 现盘核对 + 负控
bash    eval/rover/r607/run_r607.sh                    # T×3 / C×3（依赖 keys）
python3 eval/rover/r607/judge_r607.py                  # ⇒ verdict-r607.json, rc 由 verdict 派生
```
