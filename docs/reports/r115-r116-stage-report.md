# R115-R116 阶段报告 (2026-09-07)

## R115: 3 真实 key 余额链 E2E (用户钦定)

### E2E 实测 (全部真实 API)
| 端点 | 测试 | 结果 |
|---|---|---|
| glm-5.3-flash | 直连对话 + JSON 格式跟随 | ✓ 纯 JSON `{"name":"fastapi","lang":"python"}` |
| ds-4 deepseek | 真余额查询 | ✓ 9.02→9.01 CNY (真实扣费) |
| kimi-k3 | 负样本 | ✓ 诚实报错 (无费用不可链接) |
| glm 余额 | 无 scheme | ✓ 诚实报 provider_not_supported |

### 打点驱动修复 5 真缺陷 (balance_sync 打点立功)
1. **#43** InitializeAsync 无调用点 → LazyBalanceSync fire-once (bounded-wait 3s)
2. **#44/44b** QueryAsync 传 provider 名 Find 落空 → provider→代表模型解析 + key 可用性优先
3. **#45** 汇率方向反 (CNY→USD 应除 7.2) — 9.02 CNY 虚报 $64.94 → $1.25
4. **#46** 切模候选未滤无 key 模型 (曾切 claude 无 key 必败)

### 阈值切模实战
MIN_BALANCE_USD=100 → deepseek $1.25 不足 → 自动切 glm-5.3-flash → 对话实际用 glm ✓

## R116: P3 embedding 真链 + 全功能 E2E (完成)

### mass_128 全量 16/16 PASS (13428tok / 423s)
- C14 隔离实战: isolated=true score=2 (实体零重叠) 独立 session ✓
- C15 pivot: 重锚成功未被误隔离 ✓
- 全部用例 bge_provider=bge-local (P3 真向量全量生效)
- AOT 复验: Generating native code + 0 IL 警 + bge-local dim=512 ms=113 (AOT 下) ✓

### P3 bge 真链打通 (打点实证)
- 修复前: `bge_embed provider=hash-fallback dim=256` (词袋兜底 — AGENTFRAMEWORK_BGE_MODEL 未设)
- 修复后: `bge_embed provider=bge-local dim=512 ms=282` (真 bge 向量)
- compression semantic=1.0/0.977 (bge 真向量 cos 漂移校验生效)

### 全功能 E2E 实测 (pilot)
| 功能 | 输入 | 结果 |
|---|---|---|
| 意图识别 | "1+1" | ✓ intent=general |
| 无关话题隔离 | 轮1 锚 Redis → 轮2 天气 | ✓ isolated=true score=2 实体零重叠, 独立 session |
| goal pivot | 轮2 "算了...写首诗" | ✓ 重锚新任务未被隔离误吞 |
| 子任务细分 | "调研→报告→推荐" | ✓ subtasks≥2 |
| skills | wordcount/unit-convert | ✓ (虚拟 skills 命中) |
| JSON 校验 | C11 json_fields | ✓ json_format_rate 维度 |

### 缺陷 47 (意图分类)
"帮我写一首关于秋天的短诗" → code_generation ("帮我写" 词表) — 创作类拦截规则0 (规则表首位) 修复 + IntentCreativeTests×5。

### harness 扩展
- run_case_repl: 多轮 REPL 用例执行器 (隔离/pivot 需同 session 多轮)
- summarize 维度 +4: isolated/isolated_score/bge_provider/bge_ms
- cases.json 16 用例 (+C14_isolated_multi/C15_pivot_multi)
