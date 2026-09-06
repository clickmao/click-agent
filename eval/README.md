# eval/ — AgentFramework 真机评测基建

打点驱动优化循环的测试 harness 与历史跑测数据。

## 结构

```
eval/
├── cases.json        # 10 用例 (意图/子任务/技能/记忆/指令/负路径)
├── run_round.py      # 跑批 harness — 每用例独立进程, 采集回复+telemetry
├── analyze.py        # round 对比 — token/时长/通过率/回归检测 + ledger
├── results/          # 各轮跑测结果摘要 + ledger 台账 (提交入库)
└── README.md
```

## 打点层 (PGO 式阶段点位)

`src/agent.config/AgentTelemetry.cs` — 进程级 JSONL 落盘 `data/telemetry/<name>.jsonl`。

| 点位 | 位置 | 关键 kv |
|---|---|---|
| boot | host 启动 | probe |
| skill_load | SkillRegistry | root/count/ids |
| skill_parse | SkillPackageLoader | dir/error (坏包诊断) |
| skill_scan | SkillDispatcher | input_len/registry_count |
| skill | SkillDispatcher | matched/level/precision |
| skill_exec | SkillDispatcher | skill/out/error |
| intent | IndustrialAgentV2 | primary/subtask_count/input_chars |
| assembly | ContextAssembler | sources 各源召回/token/rel/assembly_ms/from_cache |
| llm_call | ModelQueueRouter | model/provider/prompt_tokens/completion_tokens/success |
| loop_turn | IndustrialAgentV2 | total_ms/success/reply_chars |
| subagent | IsolatedTaskRunner | isolated/relevance_score/reason |

## 用法

```bash
# 跑一轮 (10 用例, ~2.5min)
python3 eval/run_round.py round4 "变更说明"

# 对比基线 → ledger 台账 (REVERT/KEEP verdict)
python3 eval/analyze.py round4 baseline_final
```

**回退规则**: 出现用例回归 (pass→fail) 或 token 劣化 >15% → REVERT 候选。

## 虚拟 skills (skills/)

- `wordcount` (executive): scripts/main.py 确定性字数统计 — 验证脚本执行链路
- `unit-convert` (executive): 摄氏→华氏 — 正则参数抽取
- `code-review-checklist` / `git-commit-helper` (normative): 口径承载
- `identity.yaml` (legacy): 身份说明 force_template

## 打点驱动修复台账 (首轮)

| # | 缺陷 | 修复 |
|---|---|---|
| 1 | bge 语义疑似 (level=1) force_use 吞掉正常提问 | normative 仅词面命中 (level≥2) 才 force |
| 2 | auto 模式选无 key 模型 (gpt-4o-mini, env 缺失) | ModelSelectionPolicy/ChannelScheduler key 可用性过滤 |
| 3 | /balance 带参未被拦截 (走 LLM) | 拦截条件支持 `/balance <model>` |
| 4 | BalanceScheme 读 `endpoint` 键, yaml 是 `request_address` | 键名同步 |
| 5 | deepseek 余额 shape (balance_infos[0].total_balance, CNY) | 按真实 API 解析+币种标注 |
| 6 | 裁决排他+语义疑似淹没词面强命中 | Level 优先于 Exclusive |
| 7 | executive skill 无 scriptRunner DI, 输出被丢弃 | DI 注入 + 成功输出直接承载 |
| 8 | FromCache 默认 true (缓存统计失真) | 默认 false |
| 9 | goal 锚定不抽实体 → 隔离判定永不触发 | SetGoal 时 ExtractEntities |
| 10 | IsolatedTaskRunner DI 缺注册 → 隔离子代理休眠 | 补注册 (ILogger 泛型 factory) |

基线: baseline_final 10/10 PASS, 7354 tokens, 154s → round3 10/10, 7444 tokens, 95s (wall -38%)。
