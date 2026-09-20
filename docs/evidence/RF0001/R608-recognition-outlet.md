# R608 证据 · RF0004.1 开放域识别统一出口 `{标签|abstain, 依据}`（M1 落地轮）

- 轮次 R608 · 日期 2026-09-21 · 级别 **L3（真机运行 + 发布形态冒烟）** · 单变量 `AGENTFRAMEWORK_RECOGNITION_VERDICT`
- 判决 `eval/rover/r608/verdict-r608.json`（`verdict=FAIL / rc=1`，唯一红项 `P2_ablation_bitwise_equivalent`）
- 轮工件 `eval/rover/r608/` · 报告 `eval/rover/r608/report-r608.md` · 预注册 `eval/rover/r608/prereg-r608.json`

## 1 能力与产出

| 项 | 内容 |
|---|---|
| 能力 | 开放域识别**统一出口**：每轮落一行 `{标签 | abstain, 依据}`；标签集**不固定**（由机制面产出：面标 + 判定依据），`abstain` = 本层无本地消化依据 ⇒ 交远端（依据串带机制原因）；不新增本体、不新增词表 |
| 新增产品件 | `src/agent.nlp/RecognitionVerdict.cs`（22 行：`Recognized/Abstained/Render`）· `src/agent.nlp/RecognitionOutlet.cs`（45 行：**只读**渲染器 + `IsEnabled()` 三态） |
| 接线点 | `src/agent/IndustrialAgentV2.cs:1880`（`nlp_shape` 之后，开关缺省 on） |
| 单变量 | `AGENTFRAMEWORK_RECOGNITION_VERDICT`：未设 = 产品缺省 on（出口落地）/ `off` = 旧行为（该面 0 打点） |
| 真机读数 | 治疗 ×3 跑次：出口事件 **2/2/2**（覆盖 == 轮数 2）· abstain **1/1/1** · 标签样本 `repeat` / `abstain`；对照 ×3 跑次：**0 事件** |
| abstain 率首读基线 | **0.5**（3/6 轮；无阈值，R609 出口闸判据面） |
| 构建形态 | JIT Release 构建 rc=0 · `10 Warning(s)` / **`0 Error(s)`**（log 在案） |
| 发布形态 | `dotnet publish … -r linux-x64`：**rc=0 / IL 警告 0 / error 0** · 原生 ELF **19,739,568 B** · 仓库外 cwd `env -i` 生产档装载冒烟 **×2 均 rc=0**（真回复 `promptTokens=4795/4779`），**新面 `recognition_verdict` 随 AOT 产物发出 ×2** |

## 2 复现命令（逐字）

```bash
# 起手闸（key 自备）
set -a; . ~/.agentframework/keys.env; set +a
python3 tools/roundcheck/roundcheck.py preflight --round R608 --min-avail-mb 285 --min-disk-gb 1 --need-key AGENTFRAMEWORK_KEYS_DEEPSEEK

bash eval/rover/r608/run_r608.sh            # 真机臂（先写后跑闸 → 远端预检 → 6 臂串行 → 收尾复原 + 回读断言）
python3 eval/rover/r608/judge_r608.py       # 主判决  → verdict-r608.json
python3 eval/rover/r608/judge_r608.py --negctl   # 负控（交换臂 ⇒ P1/P2/P3 必翻红）→ verdict-r608-negctl.json
bash eval/rover/r608/aot_r608.sh            # 发布形态（AOT）+ 生产档装载冒烟
bash eval/rover/r608/tests_r608.sh          # 全量单测 + 形式门禁
bash eval/rover/r608/reverify_r608.sh       # 器具修复验证（R7 敏感面 CLEAN / JIT 0 Error(s) / AOT 重跑）
python3 eval/capability/status_gen.py --check     # 违规 0 / 基准漂移 0 / 缺源 0
python3 eval/capability/decl_sweep.py --check     # 0 漂移（30 件）
python3 tools/roundcheck/roundcheck.py audit --round R608
```

## 3 负控（判据有牙）

| 负控 | 形态 | 结果 |
|---|---|---|
| 臂读数交换 | `judge_r608.py --negctl`（T↔C） | `P1_treatment_positive` / `P2_control_zero` / `P3_outlet_coverage` **同时翻红**（rc=1）⇒ 判据非恒真 |
| 非平凡 | T/C 三键计数互异 | `nontrivial_T_vs_C_differ=true` |
| 只读性 | `RecognitionVerdictTests`：`Render(...)` 前后 `NlpGate.Counters` 不变 + 轴三态（缺省 on / `off`·`0` 关 / 非法值 ⇒ on） | 3 组断言全过 |
| 影子自检 | 判据器头部断言布尔归一（`.NET "True"` / JSON `true` / 缺失 ⇒ `None`）+ 键名契约 | assert 不过即 rc=2（fail-closed） |
| 前态同形（全量唯一红） | 按起臂前字节切分 `data/telemetry/host.jsonl` | 缺键 `llm_call` 行 **2/2 落在起臂前字节**（`2026-09-20T20:17:52Z` / `20:17:59Z`）；本轮新增 20 行缺键 **0** ⇒ 非本轮引入 |
| 敏感面 | `roundcheck` 自身 `scan_secrets()` 扫本轮脚本 | `aot_r608.sh` 修复后 **CLEAN**（原 `AGENTFRAMEWORK_KEYS_*=` 字面形态已改为运行期拼名 + 值仅经环境变量） |

## 4 判决明细（预注册原样）

| 判据 | 结果 |
|---|---|
| P1 治疗 >0（三键，reps≥3） | PASS（[2,2,2] / [1,1,1] / [1,1,1]） |
| P2 对照 ==0（三键） | PASS（全 0） |
| P2 消融逐位等价（判定面序列 T vs C 逐 rep） | **FAIL**（rep1 同 / **rep2 异** / rep3 同） |
| P3 出口覆盖 == 轮数 | PASS（[2,2,2]） |
| P4 恒前缀冻结（`F_env.prefix.chars`=15291 ∧ check rc=0） | PASS（命中率项**未测**） |
| P5 有牙 | PASS |

**P2 红的定因（不翻案、不改阈值）**：rep2 的 C 跑次走 `gate:repeat_no_replayable_prev→remote`（上一轮模型回复形态不同 ⇒ 无回放源），调用数 **8 vs T 1**、新算 **62,041 vs 4,228** ⇒ **执行面摆动 ≥ 轴效应**；按协议 §3「加 reps/扩窗（禁调阈值）」处置，产品改动**不回撤**（P1/P3/P4/P5 全过）。
可比域形态（`checks_posthoc`，不入 verdict）：逐 rep 逐位等价 **2/3** ∧ turn1 读数 **6/6 臂唯一**（`mechanical:pass→remote`）⇒ 口径可用；下一轮预注册改**分层（可比域）判据**，阈值与判据集不变。

## 5 归属与诚实边界

1. **归属**：全部读数为 **self**（本侧起臂 + 本侧判据器）；起臂前无兄弟写者、无 `roundcheck`/`runner` 在飞。
2. **能力面未行使**：无质量对照臂（codex 跳步）⇒ **不宣称任何质量/成本降幅**；成本三列标「参考」，且由摆动主导（池化 T 6 调用/16,341/4,547 vs C 13/74,314/9,847）。
3. **恒前缀命中率 ≥97% 未测**（REPL 面不产该口径，无中继 dump）。
4. **单窗 n=1/臂**：只证「接线 + 可消融 + 发布形态可用」，不作能力结论。
5. **AOT 产物 sha256 不跨次稳定**：两次发布尺寸同为 19,739,568 B、内容不同（`3f7873b8…` / `4bfcbb9d…`）⇒ 该 sha 只作**单次产物留痕**，**不作同源身份锚**；同源判据 = 尺寸 ∧ rc ∧ 冒烟新面发出。
6. **冒烟副作用已披露**：AOT 冒烟把遥测追加在**已记录臂偏移之后**；判据按字节偏移切片，不受影响。
7. **文献小步**：3 式（`cs.CL` + 引号短语）**3/3 零结果** ⇒ 采信 0 / 候选 0 / 证伪 0 / 顺延 0；连续 0 采信 = 第 1 轮（台账 `docs/research/lit-review-ledger.md` §10）。
8. **全量单测 1 红（前态同形）**：`PromptCacheChannelTests.溯源`（`cs:170 KeyNotFoundException`，缺键 `llm_call` 行）⇒ 见 §3 前态同形行。

## 6 本工件 pin（sha256，采集日 2026-09-21）

| 件 | sha256 |
|---|---|
| `eval/rover/r608/prereg-r608.json` | `808262c1f3ad2cc901a43ddc674d4ef290c1b82c3644342d94484f8719b235fc` |
| `eval/rover/r608/dag-r608.md` | `7dad397f4e66dd7b60022b7c7eb4e3e5c77ecad74647474481e6cb0817846d30` |
| `eval/rover/r608/run_r608.sh` | `13313783a8a10b0e944e4ba2cb7447208ce88918d126b579c843a079d6e1d021` |
| `eval/rover/r608/judge_r608.py` | `3dc224c6e80a2a5142a1f34332f0b87867defd30a6abc1908896ca6c5ac7411a` |
| `eval/rover/r608/verdict-r608.json` | `23029b6a7328a46772d22e3b5d222bac5a2d01d72accb594441759485426564b` |
| `eval/rover/r608/verdict-r608-negctl.json` | `76ec470594a9e80a09e5eaa6776b13ee2c7c483fc30f3bc47861ce91f40443ee` |
| `eval/rover/r608/offsets-r608.json` | `fc726710ef3f39a8dae5931ad8086e0de181648e07f331a157f7a84066e08538` |
| `eval/rover/r608/report-r608.md` | `9ebc554e91201a9f21be9c6dc09c46b0cdb56cf46b3e60d8ea47ce2f48222bb6` |
| `eval/rover/r608/aot_r608.sh` | `d5c6401ca7fd3419dc4e7ede604a651bbc5eebea4b295b27c893ebe9d65af46d` |
| `eval/rover/r608/tests_r608.sh` | `7f0c725a7ea0788b7ee49d6355c8dabfe38eef9362c52295873b398c1b97dcdb` |
| `eval/rover/r608/reverify_r608.sh` | `6c026c53347d4a61e36b5565e1b94b6f0a0d437bb3587b3d33f99c4de90d7a67` |
| `eval/rover/r608/registry_add_r608.py` | `129ac29484b0358924bc92fdfcb01a108c1275342d30a13061fc6918898fa069` |
| `eval/rover/r608/build-jit-r608.out.txt` | `abd69926ffbd3c8015c4f12b9f11f692c1a684b490ffda422085f5d8f14810ff` |
| `src/agent.nlp/RecognitionVerdict.cs` | `9dbbf2c7766246ae902c5f952abbacd6feeee4c4ab4800e9331cf44d20a89999` |
| `src/agent.nlp/RecognitionOutlet.cs` | `218f02fe8d45a5cddef72762a55693066c1c0de56e3c555fde21d37285fd75b5` |
| `src/agent.tests/RecognitionVerdictTests.cs` | `07d77f0c14c69dd54f6da0b16dd94b2f7c0fc25f38b34897b6d451e0eabb7021` |
| AOT 产物 `~/.agentframework/artifacts/pub_r608/agenthost`（19,739,568 B） | `4bfcbb9dc22f901484ea2e789fb0920bb555d390d59cfd24f35ed80d8ce38ccf`（**不跨次稳定**，见 §5.5） |

采集命令 = 对上述路径逐件 `sha256sum`（逐字见 §2 各脚本内）。
