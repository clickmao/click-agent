# R474 — KPI 分母升级: 桩估算 → 供应商 usage 真值 (真端点双臂)

预注册 `eval/rover/r474/prereg_r474.json` / 计划 `docs/plans/v0.90.0-r474-kpi-denominator-provider-truth.md` / 结算 `eval/rover/r474/settle_r474.py`
器具: 本地中继 `eval/rover/r474/relay_real.py`(请求体落盘 + 供应商 usage 落盘 + 预算闸) ; 双臂: Arole(门关) / R(门开), 唯一变量 = 门控标志, 同一 AOT 二进制 / 同一 p12 网格 12 轮 / 同一 role 夹具。

## 1. 读数 (供应商真值, 中继捕获)

| 臂 | 轮 | 中继调用 | prompt | hit | miss | completion | **total** | 命中占比 | 成本上界 | 成本下界 |
|---|---|---|---|---|---|---|---|---|---|---|
| Arole 门关 | 12/12 | 20 | 70890 | 61952 | 8938 | 5204 | **76094** | 87.4% | 0.024865 | 0.009810 |
| R 门开 | 12/12 | 9 | 29477 | 22912 | 6565 | 3292 | **32769** | 77.7% | 0.011580 | 0.006012 |

- **KPI: total 降幅 56.94% / 远端调用次数降幅 55.0% / prompt 降幅 58.42%** (判据 >=30% ⇒ PASS)
- 恒等式 prompt == hit + miss: 20/20 (Arole) 与 9/9 (R) 全成立 ⇒ usage 未被中继改写
- 预算闸: 双臂合计上界 0.036445 CNY <= 0.15 cap ; blocked=0 ; 中止试点 2 次调用另计 0.002039

## 2. 分母对照: 桩估算 vs 供应商真值 (本轮核心)

| 量 | 桩口径(字符/2) | 供应商真值 | 比值 |
|---|---|---|---|
| Arole prompt | 53565 | 70890 | 1.323 x |
| R prompt | 21026 | 29477 | 1.402 x |

⇒ 桩口径系统性**低估 24%-29%**(计费面), 且「下降」这一量在两种分母下同向同量级:
桩口径 R467: 32097 -> 14529 = **-54.74%** ; 供应商真值 R474: 76094 -> 32769 = **-56.94%** (差 2.2pp)。
结论: R465-R467 的降幅结论**不是分母假象**; 但后续一切绝对 token 读数必须以供应商 usage 为准。

## 3. 缓存通道首批真值 (R470-R472 定律的实发面确认)

- 逐主调用 hit_rate 0.894-0.952 (第 3 轮起), 会话首调 Arole 0.9369 / R 0.2232
- Pearson(lcp_est_tokens, 供应商 hit) = **0.8175 (Arole) / 0.7593 (R)** ⇒ 由实发 messages 推出的公共前缀长度与供应商命中量同向强相关 (首次在真实链路验证)
- `effective_hit_rate` 首次可算: 11/16 (Arole) 与 5/6 (R) != -1 ; 其中 **3 例 > 1.0** (1.0589 / 1.0066 / 1.0822) ⇒ 该指标分母取 `cacheable_tokens`(=上一条 prompt) 的口径缺陷: 命中量可超上一条全量 ⇒ 应改为 hit/min(prompt, cacheable) 或 hit/prompt。红线 97% 的判定面随之需重述。

## 4. 预注册判据结果 (verdict-r474.json)

| 判据 | 结果 | 读数 |
|---|---|---|
| C1 链真跑通 | PASS | 双臂各 12/12 轮, 驱动 errors=[] , blocked=0 |
| C2 内外一致 (relay==host llm_call) | **FAIL(字面)** | Arole 20 vs 16 ; R 9 vs 6 |
| C3 供应商真值可取 | PASS | 双臂 usage 行齐, identity 全成立 |
| C4 缓存命中样本 | PASS | hit 61952 / 22912, 会话首调 hit 2688 / 640 |
| C5 KPI 总 token 降 | PASS | -56.94% (>=30%) |
| C6 effective_hit_rate 可算 | PASS | 11/16, 5/6 |
| C7 预算闸 | PASS | 0.036445 <= 0.15, blocked=0 |
| C8 质量不降 | **部分不达标** | 见第 5 节 |
| C9 闸器负控 | PASS | cap=0 -> 402 且零外发 ; 正控 -> 透传 |
| C10 中止试点计入 | PASS | 0.002039 CNY |

事后判据(单列, 不覆盖 C2 原判):
- **P1**: relay 调用 == `llm_call` + `llm_call_recover` ⇒ 20==16+4, 9==6+3 **成立** ⇒ 每条远端调用都有遥测点;但 recover 行**缺 prompt/缓存字段** ⇒ 产品自记账漏 15,458 prompt tokens = Arole prompt 总量 **21.8%** (R 臂漏 10,162 = 34.5%)。
- **P2**: 扣除 recover 同类比较: Arole 59,721 (16 调用) vs R 22,607 (6 调用) = **-62.1%** ⇒ 降幅不靠重试差异解释。

## 5. 诚实边界: 本轮 KPI 达标, 但**质量判据不达标**

真端点把桩时代看不见的**回复正文**暴露出来, R 臂 12 轮里 9 轮不是实质回答:

| 轮 | 用户 | Arole(门关) | R(门开) |
|---|---|---|---|
| t1 | 把构建命令写成一行。 | 371 字实质回答(前提问询) | ⚠「模型未产出正文…请重试」 |
| t2-t5 | 谢谢/好的/嗯嗯/明白 | 短确认(11-30 字) | 模板「收到, 继续按当前方向推进」(4 轮) |
| t6 | 再讲一遍。 | 103 字(反问要点) | **模板**(判 `mechanical:repeat→local`) |
| t7 | 讲细一点。 | 644 字实质回答 | ⚠ 未产出正文 + 失败横幅 |
| t8 | 换个说法。 | 528 字实质回答 | ⚠ 未产出正文 + 失败横幅 |
| t9 | 从头再说。 | 571 字实质回答 | **模板**(判 `mechanical:repeat→local`) |
| t10-t12 | 归因质询三连 | 105/165/226 字实质回答 | 96/136/243 字实质回答(与 Arole 同级) |

- 失败通道真值: Arole `llm_call_recover` 4 条 **recovered=true**(重试出正文) ; R 3 条 **recovered=false**(retry_len=0) ⇒ 3/12 轮用户可见失败横幅(t1/t7/t8)。
- 门事件(R): 12 事件 = Pass 6 / Skip 6 (`gate:skip` 4 + `mechanical:repeat` 2)。
- **可用性缺陷(非设计预期)**: t6「再讲一遍。」与 t9「从头再说。」被判 repeat→local 回模板; 用户要的是**内容复述**, 模板=零信息回答 ⇒ 重复类指令必须「回放上一条回复正文」(零 token) 而不是模板。
- 归因边界: 空正文是**供应商侧**失败模式(两臂都出现首次空正文), 本轮 3 例重试全失败 vs Arole 4 例全成功, 样本 n=3/4 **不足以**断言与门控相关; 器具缺采样参数与 finish_reason 落盘 ⇒ 根因未定位(下轮补)。

## 6. 本轮产物

- `eval/rover/r474/relay_real.py` — 真转发中继(双证据: 请求体 + 供应商 usage; 预算闸 fail-closed 402; key 仅经环境变量, 不入日志/不入 config)
- `eval/rover/r474/selfcheck_guard.py` — 闸器自检(负控 cap=0 -> 402 零外发 / 正控 -> 透传)
- `eval/rover/r474/run_arm_real.sh` + `run_both.sh` — 双臂真端点执行器(端点只改 chat_completions, **balance 读端点保持真实** => 401 但零成本, 见 tel 的 balance_sync ok=false provider_http_401)
- `eval/rover/r474/settle_r474.py` — 结算器(供应商真值 + 类别/恢复态分解 + 前缀-命中相关 + 预算)
- 证据: `arm-Arole.json` `arm-R.json` `verdict-r474.json` `calls-*.jsonl` `usage-*.jsonl` `turns-*.jsonl` `tel-*/host.jsonl`
- 退役: `/tmp/cxprobe/*` 端口 48510 的 12h 空闲 stub 未动(非本侧作业, 不杀进程)

## 7. 下轮候选 (按优先级)

1. **repeat-skip 回放**: 命中 repeat 规则时回放上一条回复正文(零 token), 替掉模板 ⇒ 直接修 t6/t9 质量问题且省 token (改链代码 ⇒ 需 AOT 重发布 + IL 警告 0)
2. **recover 通道加固**: 空正文重试失败时降采样/换非推理模型兜底; 并给 `llm_call_recover` 行补 prompt/cache 字段(补 21.8% 自记账漏账)
3. **effective_hit_rate 口径修正**: hit/min(prompt, cacheable), 红线判据随之重述并回归
4. **中继器具补字段**: 采样参数(max_tokens/temperature) + finish_reason + 响应体尾部落盘, 用于定位空正文根因
5. **kpi.jsonl 接入真值源**: 以供应商 usage 作为分母列, 与产品 `llm_call` 双列并行(禁混算)
