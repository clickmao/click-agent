# R420 证据：`/recall` 接线（跨会话检索生产消费点）

**轮次**: R420 · **分支**: A（有任务） · **计划项**: backlog `L2 待办①` = `L7-G1`（高优先级）
**一句话**: `SessionHistorySearch` 自 R370 交付后**生产消费点为 0**（"API 落地 ≠ 已接线"），本轮把它接到本地指令出口 `/recall`，并在真机上取得「接线生效 / 未接线必不同」的两臂读数。

## 1. 判据（预注册）

| # | 判据 | 类型 |
|---|---|---|
| C1 | `TryRoute("/recall q").Handled==true ∧ Command=="recall" ∧ Argument=="q"` | L2 行为断言 |
| C2 | `KnownCommands` 全集行为探测：每条 TryRoute 必 Handled（漏臂即红） | L2 一致性审计 |
| C3 | 空命中 → 渲染含「无命中」且**不抛异常**（失败可见，不静默空白） | L2 |
| C4 | 真机：治疗臂同窗口 `recall_query` ≥1 ∧ `llm_call` == 0 | L3 通道级 |
| C5 | 真机：接线前产物同形输入 `recall_query`==0 ∧ `llm_call` ≥1 且 stdout **无**渲染 | L4 负控 |

C4 ∧ C5 合取成立才算「接线生效且本地指令零 LLM」——只有 C4 时，文本进度行（CLI 对 `-q` 恒定打印「意图分析/管线执行」）会让人误以为走了 LLM 主链。

## 2. 复现命令

```bash
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
cd /home/agentuser/AgentFramework
# C1–C3
dotnet test src/agent.tests/agentframework.tests.csproj \
  --filter "FullyQualifiedName~SessionHistorySearchTests|FullyQualifiedName~CommandRouteConsistencyTests" --nologo -v q
# C4（干净遥测窗口）
rm -f data/telemetry/host.jsonl
./src/agent.host/bin/Release/net10.0/linux-x64/publish/agenthost -q "/recall 拓扑序 字典序 5"
cat data/telemetry/host.jsonl      # 期望: recall_query ≥1, 无 llm_call
# C5（接线前产物负控）
rm -f data/telemetry/host.jsonl
/tmp/pub_r414/agenthost -q "/recall 存在"   # 期望: 送 LLM, 无渲染
cat data/telemetry/host.jsonl      # 期望: recall_query==0, llm_call==1
```

## 3. 读数

- 构建 `0 errors`；单测 **28/28 PASS**（含新增 3 条渲染断言 + `/recall` 路由三元断言 + 一致性审计行）。
- AOT 发布 ok（`publish/agenthost` 15,159,856 B）。
- **治疗臂**（R420 AOT）：3 条查询 ⇒ `recall_query` **3**，`llm_call` **0**；回复为渲染串（命中 id + `score=` + 摘要片段）。
- **负控臂**（接线前 AOT `/tmp/pub_r414/agenthost`，12:19）：同形输入 ⇒ `recall_query` **0**，`llm_call` **1**，stdout 无「跨会话检索」，回复为 `失败: 环境变量 AGENTFRAMEWORK_KEYS_DEEPSEEK 未设置`。
- 同一二进制的 `query_len/hits` 对照：`存在` 2/2 · `不存在` 3/2 · `拓扑序 字典序` 7/2 · `zzq` 3/**0**。

## 4. 诚实边界（含本轮暴露的新缺陷）

1. 负控是**产物级**（接线前 AOT 二进制），不是源码回滚重编译；两者语义等价性由「同形输入产生相反读数」支撑。
2. 真机查询共 7 条、单批单机，**不构成分布**；`hits` 数值只作行为证据，不作召回率。
3. **新缺陷（本轮真机暴露，未修，登记为下轮候选）**：检索打分对**否定**无感——`不存在`(3 字) 与 `存在`(2 字) 命中**同一批**文档、分数同为 1.5660，`外星词根zzq不存在` 亦得 2 命中。用户问「X 不存在吗」会拿到「关于 X 的文档」，读起来像**肯定**。机理 = 词面（子串/词袋）重叠 + 无否定/无 IDF 门。这与 skill 中「标记『出现』≠『误用』」同族：**词面重叠 ≠ 语义相关**。
4. `HIT 0` 的两条正向查询（`会话记忆` / `向量召回 嵌入`）说明当前语料被探针题面占据，非「召回全灭」。

> 归档说明: `host-pre-run.jsonl`（本轮之前的累积遥测，1672109 B, sha256[:16]=b2a7f25cde673da9）已按仓库洁净度要求删除，不参与本次提交；本轮三窗口存档 = `host-run1.jsonl`(治疗) / `host-run2.jsonl`(对照对) / `host-negctl.jsonl`(接线前负控)。
