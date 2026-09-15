# R462 报告 · 召回-现实一致性闸 + 语言无关召回探针

## 一、三问直答

| 问题 | 判据 | 读数 | 结论 |
|---|---|---|---|
| 召回块里引用的、当前工作区并不存在的文件事实，能否被**机制**标成假？ | P1 实发面出现 `[核验✗ …]` 且引用 `report.md` | **11 个实发消息带 ✗**，`recall_stale_refs` 含 `report.md` | ✅ 成立 |
| 换语言复用是否零噪声（R447 语言无关令）？ | P2 收进非白名单后缀文本 `logic.unit`、拒二进制 `blob.bin` | `[工作区文件 logic.unit]` **进面**；`[工作区文件 blob.bin]` **不出现** | ✅ 成立 |
| 打假是否不额外花 token？ | P3 召回片段内不得出现 `[核验✓`（只打假） | 0 处 ✓ 标签；一致时零字节注入 | ✅ 成立 |
| 本轮是否回归？ | P4 7 轮 ok + 四产物 + 契约声明不上回复面 | 7/7 ok；`count.txt=4`/`merged.txt` 三行/`stats.txt=chars=14`/`first.txt` 首行；回复面 0 处契约声明 | ✅ 无回归 |

**E2E 总判：PASS（4/4）**；负控（同判据跑 R461 实发面）P1/P2 = **false** ⇒ 判据有判别力。

## 二、改了什么（链机制，非关键词/提示词补丁）

| # | 位置 | 机制 | 依据 |
|---|---|---|---|
| 1 | `src/agent.core/core/RecallRealityGate.cs`（新） | 逐子句抽取**路径样 token**（结构判定，零后缀白名单）→ 用**文件系统**裁决 → 追加 `[核验✓ 现存 N B]` / `[核验✗ 当前不存在该文件]` / `[核验✗ 越界路径…]`；fail-safe（无 root/异常 ⇒ 原文）；幂等；越界不探测；`failOnly` 模式一致时零字节 | R460/R461 实发：模型宣称 `stats.txt chars=15` 而磁盘 0 B ⇒ 产物 3/4 |
| 2 | `src/agent.modelqueue/ActionLoop.cs` + `src/agent/action/WorkspaceActionPort.cs` | 闸接入**工具回灌面**（回灌前 fail-only 核验）；`IActionPort` 增 `WorkspaceRoot` 端口（默认 null ⇒ 无工作区实现 fail-safe） | v3 实测：陈旧引用只出现在工具结果通道 |
| 3 | `src/agent/contextassembler/ContextAssembler.cs` | 召回片段同样 fail-only 核验（逐轮进 prompt ⇒ 一致时零字节） | 守住命中率/token 预算 |
| 4 | `src/agent.context/WorkspaceTextProbe.cs`（新）+ `ContextAssembler` | **删除**硬编码后缀白名单（源码逐字列语言后缀）→ 结构+内容探针（空/NUL/二进制 ⇒ 弃）；后缀集只在显式配置 `AGENTFRAMEWORK_TEXT_SUFFIX_ALLOWLIST` 时生效 | R447 用户令逐字：管道内一律标「通用代码逻辑」 |
| 5 | `config/base/language-tags.txt`（新） | 语言标签集**外置为数据**（机检/判定器只读数据，不改代码） | 同上；机检 `RecallRealityGate_Source_HasNoLanguageSuffixLiteral` |

## 三、判据修订留档（预注册被证伪 ⇒ 宣称收窄，不改写为通过）

| 版本 | 结果 | 真实原因 | 处置 |
|---|---|---|---|
| v1 | P1/P2/P3/P4 = false | 召回窗口（mtime 降序前 3）被运行期写的 `data/` 占满；P3 口径把记忆块全标注误算违规 | 记**器具缺陷**，非产品缺陷 |
| v2 | P1/P2/P4 = false | P4 `contract_on_front` 系**误判**（命中 system prompt 里对模型的契约说明）；P2 被 `list_dir` 工具结果污染 | 口径修订：P4 只查**回复面**；P2 只查**召回通道** |
| v3 | P1 = false（P2/P3/P4 ✅） | 陈旧引用只在**工具回灌面**，闸未覆盖该通道 | 修**链机制**（接入回灌面）而不是改判据 |
| **v4** | **4/4 PASS** | — | 判据 P1 从未被放宽 |

## 四、验证

- 单测：`RecallRealityGateTests` + `ActionLoopTests`（含新面 3d）= **32/32 通过**（构建 0 Error）。
- AOT：`/tmp/pub_r462/agenthost`（15,322,688 B）`env -i` 自启 `--version` **rc=0**。
- E2E：同夹具/同 7 轮/同适配器，唯一差异 = 二进制；实发全文 17 份（`ADAPTER_DUMP_FULL=1`）。
- 夹具同源：13 项与 R461 逐字节同源 + delta 3 项（`notes.md` 追加 1 行、`logic.unit`、`blob.bin`）+ 删运行期 `data/`。

## 五、诚实边界

- `failOnly` 模式**只打假不打真** ⇒ 一致时无法从注入面直接机检「已核验」，正向证据由单测（`Verify_ExistingArtifact_TaggedWithRealByteCount`）承担。
- 路径样 token 判定限 **ASCII**：`报告.md` 这类非 ASCII 文件名不进闸（避免把「提升3.2倍」误判为路径）⇒ CJK 产物的召回一致性暂未覆盖。
- 闸只做**存在性/体量**裁决，不判内容语义（内容真假仍属 r1 判别面的靶点）。
- W-臂（权重档位）读数见下节；`3B/2B` 档在 2 vCPU 上单臂耗时显著长于 1.5B。

## 六、W 臂：权重/量化档位能力探针（用户问「现役 r1 参数权重够不够」）

语料 = **产品实发**门判 prompt 逐位（28 条：14 条真实驱动消息「继续下一轮」= 负类 / 14 条 Ack「谢谢，收到。」= 正类），oracle = 网格 `expected[]`（机械，与 r1 无关），调用面与产品一致（`/completion`、`samplers=[temperature]`、temp=0、`cache_prompt=false`）。

| 臂 | 权重 | 准确率 | 假跳率(负类被判 S) | 漏跳率(正类被判 P) | 解析失败 |
|---|---|---|---|---|---|
| 1.5b-q4（现役基线） | 1.04 GiB Q4_K_M | **0.321** | **0.929 (13/14)** | 0.357 (5/14) | 1 |
| 1.5b-q8 | 1.89 GiB Q8_0 | 见 `w-1.5b-q8.json` | | | |
| paw2b-q4（用户指定） | 1.56 GiB Q4_K_M | 见 `w-paw2b-q4.json` | | | |
| 3b-q4 | 2.10 GiB Q4_K_M | 见 `w-3b-q4.json` | | | |
| 3b-q5 | 2.44 GiB Q5_K_M | 见 `w-3b-q5.json` | | | |

> 基线关键事实：现役 1.5B-Q4 在**真实驱动消息**上 13/14 判「该跳」，而机械守卫口径要求**必须通过** ⇒ 现状靠守卫兜住（R452：`skip_rejected_nonack`），即该权重在判别面**不可承重**。

## 关联：权重档位探针（R462-W）

> 现役 1.5B 判别面不承重（假跳 14/14）、3B-Q4/Q5 达标（0/14，2 tok/次）⇒ 详细表/负控/边界见 `docs/reports/r462-weight-probe.md`。
