# R471 报告 · 分通道聚合：真实流**实发 0/43**，R470 的 43 是派生值（诚实面收口）

## 结论（一句话）
聚合器改为**只读产品实发字段**并 fail-closed；在真实流量上它现在报 **实发 0 行 / 缺字段 43 行**，而把 R470 的 `shared_prefix: 43` 明确降级为**对照列**（禁混算）——R470 的「100% 落入 shared_prefix」是**派生结论**，此前无人区分，本轮把这条界线机检钉住。

## 证据（命令 → 读数）
`env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR python3 eval/rover/r471/check_channels_r471.py` ⇒ **C1~C6 全绿 6/6，rc=0**；形式门禁 **C7 全绿**（`dotnet test` 27/27，读数自 `eval/rover/r471/formgate-r471.log` 机检取值）⇒ **合计 7/7 PASS**：

| 判据 | 内容 | 读数值 |
|---|---|---|
| C1 | 源未改 + BOM 不吞行 | sha256 `2a9e3449…9a13`，43 条 |
| C2 | 实发面诚实 | `emitted.rows=0`，`absent_field=43`，**`emitted.shared_prefix=0`（≠43）** |
| C3 | 两列分离 + 守恒 | `derived.shared_prefix=43`，派生命中 **59,518**（=R470 值），`0+43==43 ✓` |
| C4 | 正控（器具非空心） | 同形夹具 5 行精确读回：`{shared_prefix:2, same_session:2, unknown:1}`，命中求和 **2,048**、已上报 1 / 未上报 1，`unreported=0`，rate 逐行同式 |
| C5 | 负控 6 例 | (a)双计判红 ✓ (b)未上报不入和且 `hit_na=1` ✓ (c)`unknown` ✓ (d)缺字段不冒充 ✓ (e)归因反写有判别力 ✓ (f)接线洞判红 ✓ |
| C6 | 零回归 | 新脚本 legacy 键与 `HEAD` 版**逐键相同**，新增键仅 `channels`/`channel_verdict`，`verdict` 一致 |
| C7 | 形式门禁 | `dotnet test` **27/27**（failed 0, skipped 0, exit 0, 执行数>0），含 `PromptCacheRedlineTests` 对脚本的逐串锁 `REDLINE = 0.97` 仍绿 ⇒ 只增不改未破锁 |

聚合器输出（真实流）：

```
[分通道·实发] 有通道字段 0/43 行 (缺字段 43, 非法值 0)
  · same_session 0    · shared_prefix 0    · unknown 0
[分通道·shared_prefix] 调用 0 | 命中求和 0 tok (已上报 0 / 未上报 0) | 占比 -1
[分通道·对照] 派生重算 (R470 口径, 禁与实发相加): shared_prefix 43 行, 命中求和 59518 tok
[分通道·守恒] 0+43==43 ✓; 判红 0 条 ⇒ PASS
```

## 变更（只增不改）
`scripts/kpi_cache_hit.py`（sha256 `0025d67c…3f18`，307 行）：
- 新增 `CHANNELS`(:63) / `chan_of`(:66，产品 `PromptCacheKpi.Channel` 逐字移植) / `aggregate_channels`(:71-166)；
- 新增打印段(:236-254) 与 JSON 键 `channels`/`channel_verdict`(:268-269)；`VERDICT` 行追加通道判据(:302)；
- 退出码语义扩展：`1` 亦含「分通道判据判红」；`effective_hit_rate`/`cacheable_tokens`/97% 红线**一字未动**。

## 基线对比
| 项 | R470 | R471 |
|---|---|---|
| 聚合器能否读通道字段 | 否（字段落盘无人聚合） | **是**（实发优先，缺字段 fail-closed） |
| 真实流通道读数 | 无（只有证据脚本派生 43） | 实发 **0/43** + 派生对照 43（**分离标注**） |
| 器具执行数 | — | 正控 `emitted.rows=5` > 0（非空跑） |
| 负控 | R470 4/4 | R471 **6/6**（新增双计/接线洞/未上报三例） |
| legacy 行为 | — | 与 HEAD **逐键零回归** |
| AOT | `agenthost` 15,343,232 B / IL 0 | 未触发（本轮无 C# 改动） |

## 诚实边界
- **实发面在真实流上零样本**：43 条 `llm_call` 全部早于 R470 接线 ⇒ 实发正确性由同形夹具（C4）+ 负控（C5）背书，**不由真实流量背书**。真实流只能证明「聚合器不再把派生量冒充实发量」。
- 未做真机远端调用 ⇒ 仍无同会话第 2 轮真实样本，97% 红线的真机可达性仍只有离线界（R469）。
- 本轮不改链、不改红线 ⇒ **不产生 KPI 数值变化**，只产生可复核性。

## 下轮候选
① **C 档 3,320 tok 新算的组成分解**（共享 ≈2.1k 不随 prompt 增长 + 私有部分），把 R469/R470 的「升前缀」变成可执行改动并挂真实前后对比；
② 红线迁移为「分档上限 + 达成轮占比 + 分通道」的**联合判据**（R469 结论落地）；
③ **实发字段的真实样本**：在下一次真实调用上验证 `cache_channel` 真的落进遥测（当前 0 样本是本轮最大未覆盖面）。
