# 能力自检探针 KPI 台账

生成时间: 2026-09-13 23:28:55 · 遥测: `data/telemetry/host.jsonl` · run 数: 6

**口径**: 通过率 = 隐藏用例通过数 / 隐藏用例总数(**整题全对才算过**的等价读数见 四); token 取 run 墙钟窗口 `[ts-elapsed_s, ts]` 内的 `llm_call` 打点合计; 窗口内无调用 ⇒ `n/a`(**不是 0**)

## 一、总览

| # | run | solver | 题集sha | 题数 | 用例 | 整题全对 | 通过率 | 耗时(s) | s/题 | tokens(p/c) | tok/题 |
|--|--|--|--|--|--|--|--|--|--|--|--|
| 0 | probe-agent-seed20260913.json | agent | e72c0e37e249 | 6 | 35 | 6/6 | 1.0000 | 56.09 | 9.35 | 21530/4845 | 4395.8 |
| 1 | probe-mutation:hardcode-seed20260913.json | mutation:hardcode | d2236104629c | 3 | 32 | 0/3 | 0.0625 | 0.72 | 0.24 | n/a | n/a |
| 2 | probe-oracle-seed20260913.json | oracle | e72c0e37e249 | 6 | 35 | 6/6 | 1.0000 | 0.72 | 0.12 | n/a | n/a |
| 3 | probe-m6-oracle.json | oracle | b8e796a6d803 | 6 | 36 | 6/6 | 1.0000 | 0.71 | 0.12 | n/a | n/a |
| 4 | probe-m6-agent.json | agent | b8e796a6d803 | 6 | 36 | 6/6 | 1.0000 | 215.01 | 35.84 | 28334/38956 | 11215.0 |
| 5 | probe-m6-hardcode.json | mutation:hardcode | 364de23ea7ae | 3 | 33 | 0/3 | 0.1818 | 0.71 | 0.24 | n/a | n/a |

## 二、对比 A → B

A = `probe-oracle-seed20260913.json` (oracle, 题集 e72c0e37e249) · B = `probe-agent-seed20260913.json` (agent, 题集 e72c0e37e249)

> 题集是否同一批: **是** (同批题集 ⇒ Δ 可比)

| 指标 | A | B | Δ |
|--|--|--|--|
| 整题全对率 | 1.0000 | 1.0000 | +0.0000 |
| 整题全对题数 | 6 | 6 | +0 |
| 通过率(用例级) | 1.0000 | 1.0000 | +0.0000 |
| 通过用例数 | 35 | 35 | +0 |
| 用例总数 | 35 | 35 | +0 |
| 题数 | 6 | 6 | +0 |
| 耗时(s) | 0.7200 | 56.0900 | +55.37 |
| s/题 | 0.1200 | 9.3483 | +9.23 |
| 回复字符均值 | 131.8333 | 1537.3333 | +1405.50 |
| tok/题 | n/a | 4395.8333 | n/a |
| tok/通过用例 | n/a | 753.5714 | n/a |

## 三、按族分层 (B 或最后一个 run 之前的最新 run)

run = `probe-agent-seed20260913.json` · 题集 `e72c0e37e249`

| 族 | 题数 | 通过率 | 用例 | 模式 |
|--|--|--|--|--|
| bracket_fix | 1 | 1.0000 | 10/10 | ok=1 |
| det_mod | 1 | 1.0000 | 1/1 | ok=1 |
| expectation_urn | 1 | 1.0000 | 1/1 | ok=1 |
| matrix_spiral | 1 | 1.0000 | 11/11 | ok=1 |
| max_subarray | 1 | 1.0000 | 11/11 | ok=1 |
| quadratic_residue_count | 1 | 1.0000 | 1/1 | ok=1 |

## 四、失败模式分布 + 未知键审计

| run | 模式 | 计数 |
|--|--|--|
| probe-agent-seed20260913.json | ok | 35 |
| probe-mutation:hardcode-seed20260913.json | ok | 2 |
| probe-mutation:hardcode-seed20260913.json | wrong_output | 30 |
| probe-oracle-seed20260913.json | ok | 35 |
| probe-m6-oracle.json | ok | 36 |
| probe-m6-agent.json | ok | 36 |
| probe-m6-hardcode.json | ok | 6 |
| probe-m6-hardcode.json | wrong_output | 27 |

未知模式键(不得丢弃, 单列备查): 无

## 五、诚实边界

- token 读数缺失(窗口内无 llm_call 打点)的 run: probe-mutation:hardcode-seed20260913.json, probe-oracle-seed20260913.json, probe-m6-oracle.json, probe-m6-hardcode.json
- 通过率=用例级读数; **整题全对** 的题数见 run 摘要 `per_task[].mode==ok` 计数
- 判定口径 = 交付物真实形态(围栏 / 回复区裸代码 / 落盘产物)取最长可编译候选; 口径错会造成**反向空心指标**(满分记 0 分), 已有永久负控
- 题集饱和(通过率 1.0)时该读数对能力提升不敏感 ⇒ 需看对抗族与作弊解负控

