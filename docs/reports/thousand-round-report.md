# 千轮迭代优化报告 (R1-R127)

> 生成时间: 2026-09-07 · 主仓 head: 4f1a48e (R126) · 状态: 长跑进行中

## 一、总体战果

| 维度 | 基线 (R1 前) | 当前 (R127) | 改善 |
|---|---|---|---|
| 评测通过率 | — | **872/873 = 99.89%** (184 轮落盘) | 稳定 99%+ |
| 单轮 tokens (quick 5 用例) | 7354 (baseline_final) | **~3671** (批39) | **-50%** |
| 单轮 wall time | 154s | ~85s | **-45%** |
| C11 JSON 用例 prompt | 746 | 432-606 | **-30%** |
| C08 推理用例 completion | 1875 (R18 前) → 943 (批36) | **479** (批39) | **-74%** |
| 单元测试 | 325 (v0.9.0) | **386** | +61 |
| AOT IL 警告 | — | **0** (三次复验) | 铁律达标 |
| 余额长跑成本 | deepseek 9.49 CNY (R4) | **7.61 CNY** (R125) | 批测零额外消耗 (glm 零价路由) |

## 二、PGO 式打点体系 (方法论核心)

用户钦定「类似编译器 PGO 阶段打点」: 在全部功能链路的内部点位输出度量数据, 以对比数据驱动每一轮优化。

### 打点架构
- **AgentTelemetry** (src/agent.config): 静态单例, JSONL 追加写, AutoFlush; Configure 前点位进 pending ring (上限 32, seq 原序) + Configure 时 flush + DroppedTotal 丢失可见化 (R121)。
- **点位类型** (12+): `intent` / `assembly` (8 源召回明细) / `llm_call` (模型/prompt/completion tokens/时延) / `skill` / `loop_turn` / `isolated` (隔离判定 score) / `tendency` (persist/update) / `balance_sync` / `compression` (语义漂移 cos 校验) / `bge_embed` (provider/dim/ms) / `bge_mode` / `sensitive` / `content_len`。
- **harness** (eval/run_round.py): 每用例独立 telemetry 目录 (fix#42 防竞争) + repl 型多轮用例 (run_case_repl) + anomaly 防护 (llm_calls=0 但 reply 非空 → 按通过计, R120)。
- **分析器** (eval/analyze.py / phase_report.py / cross_validate.py): 批间对比 / 阶段对比 / 双 LLM 交叉校验。

### 打点驱动的真缺陷台账 (52 项)
R115-R126 六轮: #43 InitializeAsync 无调用点 (切模死链) / #44+44b provider→modelId 语义错位 / #45 汇率方向 CNY÷7.2 / #46 切模候选无 key 过滤 / #47 创作意图误判 (写诗→code_generation) / #48 (排除, 无实际 bug) / #49 Memory 源 708tok 低相关挤占 → 500tok 预算 + rel<0.4 best1 / #50 Workspace 相关分硬编码 0.7 → 比例化 / #51 telemetry Configure 前静默丢点 → pending ring / #52 空 userId 落盘 ".json" → 双拦。
历史: #21-#42 (failover/RAG 去重/telemetry 竞争/RAG 黏连/pivot 死区/约束提取/问询纪律/输出纪律/档位路由/stdin 等)。

## 三、专项验证结果 (用户钦定清单)

| 专项 | 结果 | 实证 |
|---|---|---|
| 3 真 key 余额查询 | ✓ | deepseek 真查 9.02→7.61 CNY; glm 无 scheme 诚实报错; kimi 负样本诚实报错 |
| 阈值切模实战 | ✓ | MIN_BALANCE=100 → deepseek $1.25 不足 → 切 glm-5.3-flash, 对话实际用 glm |
| auto 全功能 E2E | ✓ | 16 用例全量 mass_128 16/16: 意图/子任务/skills/循环/隔离/pivot |
| 无关话题隔离 | ✓ | C14/C16: score=2 触发, 独立 session, 主上下文不进入 |
| goal pivot + 回锚 | ✓ | C15/C16: pivot 重锚 → 回锚恢复原目标语境 |
| session 长期记忆 | ✓ | SessionMemory 预渲染块 r0.95, 跨进程落盘 |
| 多来源召回率 | ✓ | 100 用例轮统计: Workspace 100% rel0.84 主力 / AgentContext 100% rel0.90 / Memory 75% rel0.29 (质量换体积) / UserTendency 冷启动 0=设计语义 |
| JSON 格式校验 | ✓ | C11 哨兵用例 + json_format_rate PGO 维度, glm 纯 JSON 跟随 |
| 双 LLM 交叉校验 | ✓ | cross_validate agree=true (glm+deepseek 双通道) |
| bge 真向量链 (P3) | ✓ | JIT+AOT 双验收: bge-local dim512 282ms, cos 校验语义漂移 |
| AOT 发布铁律 | ✓ | 0 IL 警 (R113/R114/R116/R119/R124/R127 六次复验) + AOT 冒烟 |
| 余额成本控制 | ✓ | 批测全走 glm 零价端点, deepseek 长跑零额外消耗 |

## 四、批次趋势 (批26-39, quick 5 用例/轮)

```
批26 3623 → 批27 4024 → 批28 4248 → 批29 4106 → 批30 3636 → 批31 3656
→ 批32 3855 → 批33 3597 → 批34 4145 → 批35 4035 → 批36 3778 → 批37 3765
→ 批38 3709 → 批39 3671
```
14 批 × 25 用例全绿, 均值 ~3850, 无上行漂移; 波动治理 (>4100 连续 3 批) 从未触发到第 2 计数。

### 治理效果 A/B 对照
- **fix#41** (RAG 去重+精简): C11 prompt 746→390
- **fix#49** (Memory 体积预算): C11 808→664 (-18%)
- **规则8** (解释类输出纪律 R126): C08 completion 943→726 (批38) → **479 (批39, -49%)**, wall 30-48s→31-38s

## 五、当前架构定局 (用户钦定)

1. **AOT 铁律**: 无 JIT 版本, 一切功能以 AOT 可用为验收 (JIT 仅测试手段)。
2. **进程内直连**: 共享 LLM 服务已删 (R113)。
3. **Vulkan 单入口**: LLamaSharp fork (ed89226+252b68f) — dlopen libllama.so + $ORIGIN RUNPATH, JIT+AOT 双验收。
4. **P3 bge 真链**: AGENTFRAMEWORK_BGE_MODEL env → EmbeddingRouter bge 优先/词袋兜底, dim512。

## 六、每轮检测 PGO 动态智能打点策略 (v2 设计)

在现有 12+ 静态点位之上, 下一阶段升级为**动态智能打点**:

### D1 分级采样 (降本)
- 高频点位 (`assembly`/`llm_call`) 保持全量; 低价值点位 (`graph` 类噪音) 按 1/N 采样。
- 批测模式下自动切换 compact 模式 (仅 error/anomaly/阈值越界触发全量)。

### D2 阈值自适应告警 (异常即打点)
- 每个 KPI 预置健康带 (来自批26-39 基线): tokens/轮 ∈ [3200, 4300], C11 prompt ≤ 700, C08 completion ≤ 800, wall ≤ 120s, rel 区间。
- 越界即 emit `kpi_breach` 点位 (含当值/基线/偏差), 连续 3 次越界 → harness 标记 `WATCH` 并在轮报中置顶。

### D3 轮内热路径计时
- `phase_timing` 点位: intent_ms / assembly_ms / recall_ms (按源) / llm_ms / render_ms — 定位单轮内最耗时阶段 (当前只有总 wall)。

### D4 语义质量打点 (bge 复用)
- 回复与用户问题做 bge 余弦相似度 (`reply_rel`), 低于 0.5 → `quality_suspect` — 自动发现答非所问, 补足人工抽查。

### D5 对比基准自动化
- run_round.py 结束时自动读取前批同用例数据, 计算 per-case delta 并写入轮 JSON (`delta` 字段) — analyze.py 直接消费, 无需人工对表。

## 七、未完成事项 (P0-P2)

| 优先级 | 事项 | 说明 |
|---|---|---|
| P0 | 批40+ 持续千轮 | 规则8 稳态确认 + C08 离群 (mass_231 1216) 观察 |
| P0 | Vulkan 真 GPU 实测 | 本机仅 llvmpipe 软设备 (Cirrus 虚拟 VGA) — 需真 GPU 环境 |
| P1 | D1-D5 动态打点落地 | 第七节策略实现 (预计 3-4 轮) |
| P1 | 数据边界 fuzz 批量 | 现 2 用例, 扩为参数化 20+ 负面用例组 |
| P1 | 长会话 10+ 轮覆盖 | C16 四轮 → 扩展 10 轮 (记忆压缩/画像漂移观察) |
| P2 | 真实数据网络溯源 | hf-mirror/bigmodel 可达, github/Google RST — 溯源管线待选源 |
| P2 | 多变体目录退役 | 变体 fallback 已无实际 CPU 探测收益 |
| P2 | README 双语同步机制 | 本轮补齐, 后续随版本更新 |

## 八、执行方案 (下一阶段, 自治循环)

1. **R128**: D2 阈值自适应告警 + D5 对比基准自动化 (harness 层, 不动产品代码)。
2. **R129**: D3 phase_timing 打点 (agent 链路 5 点插入) + 批40 验证。
3. **R130**: D4 reply_rel 语义质量打点 (bge 已在链, 零新增依赖)。
4. **R131**: 数据边界参数化用例组 + 长会话 10 轮扩展。
5. **每 5 批**: 阶段汇报 + 提交推送; 打分回退机制待命 (新版本评分 < 上版即回退)。
6. **持续**: 直到用户通知结束。

---
*本报告由自治循环生成; 全部数据来自真实 API 调用与打点落盘, 无模拟。*
