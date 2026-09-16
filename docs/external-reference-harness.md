# 外部参照对比器具（codex-cli 基准）· 常态开发流程

状态: 生效（R455 起入册）。用户钦定：「可以将对比流程加入开发文档内」。

## 1. 目的
**本文档 = 主线方法的常态载体。** 用户 2026-09-17 钦定更正：**主线 = 用「随机游戏 / 数学难题 / 程序题」的真实开发任务，与外部真值（codex-cli）同环境·同输入对照，对本项目做质量自检**；本节所述器具就是该主线的执行面（见 `iteration-master-plan.md` §0-0 铁律 10）。

用**外部真值**（另一套真实 agent 框架在同一模型上的行为）检验本 agent 的链机制，替代封闭系统自证。
服务判据 = 用户钦定 KPI：**一轮任务总 token ↓≥30%（主要是不必要的 LLM API 请求少了）**；一等上游指标 = **问询次数（澄清轮）**。**KPI 是主线的判据之一，不是主线本身。**

## 2. 硬性铁律（违一条则整批数据作废）
| # | 铁律 | 违反后果 |
|---|---|---|
| E1 | **同环境**：两侧工作目录初始内容逐字节相同（`md5sum` 全员一致后才许开跑） | 数据作废 |
| E2 | **同输入**：两侧逐轮文本出自同一 `suite-turns.json`（同一 `md5`） | 数据作废 |
| E3 | **同模型**：两侧经同一 adapter 打到同一真实模型（`deepseek-flash`） | 数据作废 |
| E4 | **零重试**：`response.completed` 必须带 `input_tokens`/`output_tokens`，否则 codex 侧会重连重发 ⇒ **破坏返回基准**（R454 教训：6 连次） | 数据作废 |
| E5 | **单句输入不算**：输入必须逐模块可测（缓存命中 / 闸门 / 吸收 / 动作），单句「继续下一轮」不构成对照 | 数据作废 |
| E6 | 判分**机械**：产物按字节等值判定，禁模型裁判；只读落盘证据，禁事后补记 | 数据作废 |

## 3. 标准套件（6 轮，单会话两侧各跑一遍）
| 轮 | 输入 | 覆盖模块 |
|---|---|---|
| T1 | 当前目录下一共有几个 .py 文件？ | 只读理解 / 是否伪执行 |
| T2 | 把 .py 文件的个数写入 count.txt（只要数字） | 动作通道 |
| T3 | x/y/z.txt 顺序合并写 merged.txt | 动作通道 / 多文件 |
| T4 | 读 merged.txt 统计字母数写 stats.txt（chars=<n>） | 多步推理 + 动作 |
| T5 | 继续 | 闸门 / 吸收（driver 类输入） |
| T6 | notes.md 第一行写 first.txt | 动作通道 / 文本处理 |
判分期望：`count.txt=4`、`merged.txt=ALPHA\nBETA\nGAMMA\n`、`stats.txt=chars=14`、`first.txt` 含 `R455 fixture note`。

## 4. 度量（两侧同式）
- 逐调用：`prompt_tokens` / `prompt_cache_hit_tokens` / `completion_tokens` / `tools[]` 数量 / 工具调用数
- 逐轮：远端调用数、澄清问句数（`ASK` 标记）、产物通过数
- 汇总：`Σcached/Σin` 命中率、`x/4` 产物通过、**问询次数**、总 token
- 边界：两侧静态面/工具面不同源 ⇒ **不得**据总量断言「谁更省」；只允许「同输入下行为差异」与本侧内趋势。

## 5. 器具与用法
| 件 | 路径 |
|---|---|
| 透传工具适配器（统一入口 + usage 注入 + 请求/应答全量落盘，Authorization 永不落盘） | `eval/rover/r455/adapter_tools.py` |
| 夹具生成（两侧逐字节同） | `/tmp/r455_setup.sh` |
| 套件 runner（codex 单会话 `exec` + `exec resume`；我方单会话 driver 6 轮） | `eval/rover/r455/run_suite.sh` |
| 判分器（机械等值 + 逐调用 token/cache + 模块表） | `eval/rover/r455/judge_suite.py` |
| 预注册（结构性不变量 + 事后项分离） | `eval/rover/r455/prereg-r455.json` |
| 诊断报告（机制根因） | `docs/reports/agent-chain-diagnosis-r455.md` |

命令：
```
bash /tmp/r455_setup.sh                       # 夹具（两侧同）
bash /tmp/cxprobe/start_adapter.sh            # adapter @48615
bash eval/rover/r455/run_suite.sh             # 两侧 6 轮（后台，禁中断）
python3 eval/rover/r455/judge_suite.py --ns r455
```

## 6. 已知限制（诚实边界）
- codex 侧本机 `bwrap` 不可用 ⇒ 用 `--dangerously-bypass-approvals-and-sandbox` 在 scratch 目录跑（审批/沙箱面不对等，报告须标注）。
- 两侧静态面不同源（codex instructions 16,979 字符 + 9 工具 vs 我方 4,300 字符 + 0 工具）⇒ token 总量不可直接比较，只比行为与同侧趋势。
- 闸门/本地 r1 需 llama-server（内存闸 `MemAvailable≥2650MB`）；未起时记 `n/a`，**不得**计入「闸门通过」。
- 我方无动作环（R455 机制诊断）⇒ 动作类轮次预期 0 产物；该差异是**被测对象**，不是器具缺陷。
