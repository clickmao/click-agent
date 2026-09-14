# 能力自检探针 KPI 台账

生成时间: 2026-09-14 21:18:06 · 遥测: `data/telemetry/host.jsonl` · run 数: 9

**口径**: 通过率 = 隐藏用例通过数 / 隐藏用例总数(**整题全对才算过**的等价读数见 四); token 取 run 墙钟窗口 `[ts-elapsed_s, ts]` 内的 `llm_call` 打点合计; 窗口内无调用 ⇒ `n/a`(**不是 0**)

## 一、总览

| # | run | solver | 题集sha | 题数 | 用例 | 整题全对 | 通过率 | 耗时(s) | s/题 | tokens(p/c) | tok/题 |
|--|--|--|--|--|--|--|--|--|--|--|--|
| 0 | probe-m6-agent.json | agent | b8e796a6d803 | 6 | 36 | 6/6 | 1.0000 | 215.01 | 35.84 | n/a | n/a |
| 1 | probe-agent-seed0-r433m6.json | agent | b8e796a6d803 | 6 | 36 | 5/6 | 0.6944 | 91.97 | 15.33 | 24623/19069 | 7282.0 |
| 2 | probe-agent-seed20260913-r433as.json | agent | f7b1a5320cdf | 3 | 43 | 3/3 | 1.0000 | 97.26 | 32.42 | 15235/18925 | 11386.7 |
| 3 | probe-mutation:topo_dfs-seed20260913-r433ctl-topo.json | mutation:topo_dfs | fd4b97912550 | 3 | 39 | 0/3 | 0.4359 | 0.94 | 0.31 | n/a | n/a |
| 4 | probe-mutation:vm_noerr-seed20260913-r433ctl-vm.json | mutation:vm_noerr | 7c7b19d622fd | 3 | 32 | 0/3 | 0.6250 | 0.84 | 0.28 | n/a | n/a |
| 5 | probe-mutation:json_loose-seed20260913-r433ctl-json.json | mutation:json_loose | 5fbcab13df1f | 3 | 54 | 0/3 | 0.7037 | 1.49 | 0.50 | n/a | n/a |
| 6 | probe-agent-seed0-r433m6r2.json | agent | b8e796a6d803 | 6 | 36 | 5/6 | 0.6944 | 151.71 | 25.29 | 24643/33572 | 9702.5 |
| 7 | probe-agent-seed0-r433m6fix.json | agent | b8e796a6d803 | 6 | 36 | 6/6 | 1.0000 | 123.77 | 20.63 | 23152/17437 | 6764.8 |
| 8 | probe-agent-seed0-r433m6fix2.json | agent | b8e796a6d803 | 6 | 36 | 6/6 | 1.0000 | 191.57 | 31.93 | 23295/31992 | 9214.5 |

## 二、对比 A → B

A = `probe-m6-agent.json` (agent, 题集 b8e796a6d803) · B = `probe-agent-seed0-r433m6fix2.json` (agent, 题集 b8e796a6d803)

> 题集是否同一批: **是** (同批题集 ⇒ Δ 可比)

| 指标 | A | B | Δ |
|--|--|--|--|
| 整题全对率 | 1.0000 | 1.0000 | +0.0000 |
| 整题全对题数 | 6 | 6 | +0 |
| 通过率(用例级) | 1.0000 | 1.0000 | +0.0000 |
| 通过用例数 | 36 | 36 | +0 |
| 用例总数 | 36 | 36 | +0 |
| 题数 | 6 | 6 | +0 |
| 耗时(s) | 215.0100 | 191.5700 | -23.44 |
| s/题 | 35.8350 | 31.9283 | -3.91 |
| 回复字符均值 | 2491.3333 | 2085.0000 | -406.33 |
| tok/题 | n/a | 9214.5000 | n/a |
| tok/通过用例 | n/a | 1535.7500 | n/a |

## 三、按族分层 (B 或最后一个 run 之前的最新 run)

run = `probe-agent-seed0-r433m6fix2.json` · 题集 `b8e796a6d803`

| 族 | 题数 | 通过率 | 用例 | 模式 |
|--|--|--|--|--|
| pair_closest_abs_sum | 3 | 1.0000 | 33/33 | ok=3 |
| witness_min_counterexample | 1 | 1.0000 | 1/1 | ok=1 |
| witness_sqrt_mod | 2 | 1.0000 | 2/2 | ok=2 |

## 四、失败模式分布 + 未知键审计

| run | 模式 | 计数 |
|--|--|--|
| probe-m6-agent.json | ok | 36 |
| probe-agent-seed0-r433m6.json | ok | 25 |
| probe-agent-seed0-r433m6.json | syntax_error | 1 |
| probe-agent-seed20260913-r433as.json | ok | 43 |
| probe-mutation:topo_dfs-seed20260913-r433ctl-topo.json | ok | 17 |
| probe-mutation:topo_dfs-seed20260913-r433ctl-topo.json | wrong_output | 22 |
| probe-mutation:vm_noerr-seed20260913-r433ctl-vm.json | ok | 20 |
| probe-mutation:vm_noerr-seed20260913-r433ctl-vm.json | runtime_error | 12 |
| probe-mutation:json_loose-seed20260913-r433ctl-json.json | ok | 38 |
| probe-mutation:json_loose-seed20260913-r433ctl-json.json | wrong_output | 16 |
| probe-agent-seed0-r433m6r2.json | ok | 25 |
| probe-agent-seed0-r433m6r2.json | syntax_error | 1 |
| probe-agent-seed0-r433m6fix.json | ok | 36 |
| probe-agent-seed0-r433m6fix2.json | ok | 36 |

未知模式键(不得丢弃, 单列备查): 无

## 五、诚实边界

- token 读数缺失(窗口内无 llm_call 打点)的 run: probe-m6-agent.json, probe-mutation:topo_dfs-seed20260913-r433ctl-topo.json, probe-mutation:vm_noerr-seed20260913-r433ctl-vm.json, probe-mutation:json_loose-seed20260913-r433ctl-json.json
- 通过率=用例级读数; **整题全对** 的题数见 run 摘要 `per_task[].mode==ok` 计数
- 判定口径 = 交付物真实形态(围栏 / 回复区裸代码 / 落盘产物)取最长可编译候选; 口径错会造成**反向空心指标**(满分记 0 分), 已有永久负控
- 题集饱和(通过率 1.0)时该读数对能力提升不敏感 ⇒ 需看对抗族与作弊解负控

