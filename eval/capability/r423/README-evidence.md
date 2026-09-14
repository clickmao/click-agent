# R423 证据归档 —— 跨会话检索打分：词元频次饱和 + 可分性预检

判决：**PASS**（主判据 C0–C7 + C4b 全绿；C8 为边界登记，不参与红绿）
判决书：`eval/capability/r423/verdict-r423.json` ｜ harness：`eval/capability/r423/run_r423.py` ｜ 计划：`docs/plans/v0.44.0-r423-tf-saturation.md`

## 1. 可分性预检（先于实现，且据其结果改写靶点）
R422 的残留并列对，取**机检**特征向量（单测 `R423_FrozenCorpus_FeatureVector_IsMachinePinned_NotHandCounted`，
经 `JsonSessionMemoryStore.Load` + `BuildDocument` + `CountTokens`）：

| 文档 | distinct 词元数 | tf(存在) |
|---|---|---|
| `probe-0914125816-p004` | 90 | 4 |
| `probe-0914125831-p005` | 90 | 4 |

⇒ 词袋计数特征向量**逐项相等** ⇒ 频次信号对该对**恒为空操作**。
⇒ 该并列登记为**词袋计数信号族的不可分边界**（需换信号族：语义/位置），本轮**不作**"R422 残留已消除"的全称宣称。
> 首版人工复算得 `87 / 2`，**被 C4 当场证伪**（真值 `90 / 4`）⇒ 预检数字一律机检（见 §4）。

## 2. 两臂真机读数（AOT，隔离 cwd + 通道级遥测 + stdout 原文）
| 臂 | 二进制 | sha256（前 12） | 语料 B：等长 2 词元 tf 3 vs 1 | 语料 A：tf=1 | 语料 A：tf=4 |
|---|---|---|---|---|---|
| T（R423） | `/tmp/pub_r423/agenthost` | `2d363b6d132b` | `[1.0286, 0.4901]` **分档** | `0.2798` | `[0.1408, 0.1408]` |
| N（R422 负控） | `/tmp/pub_r422/agenthost` | `55e1ed1a5d45` | `[0.4901, 0.4901]` **全等** | `0.2798` | `[0.059, 0.059]` |

- 语料 B 比值：`1.0286/0.4901 = 2.098755` vs 闭式 `1+ln3 = 2.098612`（相对误差 **6.8e-5**）；隐含 tf `exp(r-1)=3.000`。
- 语料 A 比值：`0.1408/0.059 = 2.3866` vs 闭式 `1+ln4 = 2.386294`；隐含 tf `4.0006`（与机检钉死值 4 **两源一致**）。
- tf=1 文档 `0.2798` == R422 判决书登记值 **逐位不变**（因子的单位元）；负控臂语料 A 读数与登记值逐位相同 ⇒ **臂身份自证**。

## 3. 判据结果
`C0`（语料目录条目集纯净）· `C1`（六查询命中集两臂逐元素相同）· `C2`（负控全等 ∧ 治疗分档）·
`C3`（比值 == 1+ln3）· `C4`（tf=1 逐位不变 ∧ tf=4 == 登记值×(1+ln4) ∧ 隐含 tf == 钉死值）· `C4b`（负控 == 登记值）·
`C5`（极性 4 查询命中均 0）· `C6`（渲染可机读 ∧ `llm_call=0` ∧ `recall_query=1`/查询）· `C7`（语料逐字节相同且未被写）
→ **全部绿**；`C8`（等长同频次仍并列）单列登记。

## 4. 本轮两起仪器/流程事故（诚实入档，均为测量与流程侧，非产品缺陷）
1. **预测输入手算错**（首跑 C4 红，归档 `verdict-r423-run1-predictor-error.json`）：
   `tf(存在)` 手算 2（只读 `LongTermMemory` 段）vs 真值 4（文档 = 目标 + 实体 + 约束 + 里程碑 + 长期记忆）。
   处置：预测输入改引用**机检钉死值** + 新增"实测隐含 tf == 钉死值"子判据；**判据结构与阈值未改**。
2. **冻结语料目录被建出空子目录**（`fixture-sessions/sessions/`）：存储构造即 `Directory.CreateDirectory(<path>/sessions)`，
   某次以语料目录本身作根构造就把子目录建在了语料内。三份语料 sha256 **未变**（== R421 登记），`rmdir` 清除；
   harness 加固为只取文件 + 新增 C0。首跑 `IsADirectoryError` 被日志/异常形态暴露，未静默。

## 5. 复跑命令（L4）
```bash
dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r423
python3 eval/capability/r423/run_r423.py
env -u AGENTFRAMEWORK_PY_RUN dotnet test src/agent.tests/agentframework.tests.csproj --filter FullyQualifiedName~SessionHistorySearch --nologo -v q
```

## 6. 诚实边界
- 频次因子对**词元数与出现次数皆相同**的文档对**无区分度**（不可分边界，非缺陷）⇒ 下一步必须换信号族。
- 收益面未量化（真实语料里"等长且次数不同"的文档占比未知；当前为构造对 + 冻结语料）。
- `(1+ln tf)` 为无参数口径，**未做**变体网格/上界 oracle ⇒ 不宣称该靶点已到最优（BM25 `k1/b` 族未探）。
- 「整串命中兜底/加成」两条路径不带频次因子（常量赋值），口径局部不一致，未评估影响。

## 7. 命名空间碰撞登记（本轮运行环境事实）
- 本轮与**另一个并发执行体**同取轮号 **R423**（对侧 = AOT 发布形态复现，产物 `eval/rover/r423/`，仍在写）。
- 两侧路径不重叠；本侧全部产物位于 `eval/capability/r423/`，对侧产物**未动**；台账含 `namespace_collision` 字段。
- 本侧消歧标识：能力 id `r423.recall-tf-saturation`、计划 `docs/plans/v0.44.0-r423-tf-saturation.md`。
- 根因（本侧流程）：`max+1` 前未复跑「pgrep + 锁 + 轮文件 mtime」序列；已写下轮复发防线。
- **轮内已消解**：对侧在本轮内**让号** —— 其产物目录 `eval/rover/r423/` 迁移为 `eval/rover/r424/`，计划文件改名为 `docs/plans/v0.45.0-r424-aot-mainline-replication.md`（迁移时刻 17:10:36，本侧记录于 17:12）。⇒ 最终归属：**R423 = 本侧（跨会话检索打分·词元频次饱和）**，**R424 = 对侧（AOT 发布形态复现）**。
