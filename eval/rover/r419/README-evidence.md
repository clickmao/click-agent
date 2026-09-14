# R419 证据索引 —— 探针多轮化（轮数 / 首次通过率 / 修复率从恒等变可分化）

**预注册目标**: 让「轮数 / 首次通过率 / 修复率」在当前链上产生**真分化**（此前单轮 ⇒ 恒 1、无区分度）。
**结论（诚实）**: 仪器侧**达成**（成对正负控 + 7 态自证 + 三个缺陷闸）；真机侧**测到过真分化但未稳定复现**
（4 次 onfail 真机跑: 3 次饱和 1.0、1 次 0.8333→1.0）。判据检查器在饱和时**判 2 而非放行**，故本轮不应被读成通过。

## 复现（一条命令 = 一批，含控制臂 + 检查器）
```bash
cd /home/agentuser/AgentFramework
R419_N=6 R419_SEED=419 R419_NS=<唯一后缀> bash eval/rover/r419/run1_multiturn.sh
python3 eval/rover/r419/check_multiturn.py --selftest     # 检查器自证 7/7
python3 eval/probe/run_probe.py --selftest                # 26/26
python3 eval/probe/grade.py --selftest                    # 31/31
python3 eval/probe/process_metrics.py --selftest          # 22/22
```
`R419_NS` 必须唯一：同后缀重跑会**静默覆盖**已有读数（本轮实测事故），驱动脚本已加 `REFUSE_NS_COLLISION` 闸。

## 真机臂读数（agent = AOT agenthost + 本地 r1 判别链；`json_mini`；turns=2；correction=onfail）
| # | 批次后缀 | n / seed | 轮数(实/期) | 首轮整题全对 | 两轮整题全对 | 修复率 | 回归 | 判定 | 产物 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `b09141437` | 3 / 419 | 3/3 | 1.0 (3/3) | 1.0 | n/a | 0 | EXIT 2 饱和 | `logs/check-b09141437.out` |
| 2 | `b2091515` | 6 / 420 | 6/6 | 1.0 (6/6) | 1.0 | n/a | 0 | EXIT 2 饱和 | `logs/check-b2091515.out` |
| 3 | `b3092030` | 6 / 419 | **7/7** | **0.8333 (5/6)** | **1.0** | **1.0** | 0 | **EXIT 0 分化** ★ | 首跑产物被 #4 覆盖（仅会话记录，见下「归档事故」） |
| 4 | `b3092030`(重跑) | 6 / 419 | 6/6 | 1.0 | 1.0 | n/a | 0 | EXIT 2 饱和 | `logs/check-b3092030.out` |
| 5 | `b4095015` | 6 / 419 | 6/6 | 1.0 | 1.0 | n/a | 0 | EXIT 2 饱和 | `logs/check-b4095015.out` |

## 控制臂（确定性，仪器判别力）与对照观测
- `ctlpos` = `mutation:delayfix`（第 1 轮浅解 / 第 2 轮真解）⇒ **fix_rate = 1.0**，三次批全部成立（n=3/6/6）。
- `ctlneg` = `mutation:nofix`（两轮同浅解）⇒ **fix_rate = 0.0**、用例级 0.5140（不许把「没修」读成「修了」）。
- 控制臂轮数 **实到 == 期望**（3/3、6/6、12/12），逐条回读磁盘计轮，不信转录内 `turn N`（进程内轮次）。
- **对照臂 `correction=always`（假前提）**: 首轮 0.6667 → 两轮 0.0，fix 0/3，**回归 2 题** ⇒ 对已达标题谎称「隐藏用例没过」会把已对题改坏。
  产物归档于 `evidence-always-correction/`（README + `-t2.json` + 6 份回复 + RUN.json）。
  教训: **修正轮的前提必须为真**，否则量到的不是「修复率」而是「抗误导性」。默认已改 `onfail`。

## 本轮修掉的三个仪器缺陷（每个都成对配了闸）
1. **判定器遇坏字节整臂崩**（`grade.py` `run_code` 用 `text=True` 严格解码）⇒ 一条 0xe9 截断字节就 `UnicodeDecodeError` 杀掉整臂（实测 `STEP_EXIT_agent=1`）。
   修 = 字节捕获 + `errors="replace"` + 记 `bad_encoding` 计数；负控 = 打印坏字节的程序判不过而**不崩**（grade selftest 29→31）。
2. **同 NS 重跑覆盖既有读数** ⇒ 驱动加 `REFUSE_NS_COLLISION` 闸；每次测量唯一后缀（本条即「归档事故」的产物）。
3. **首轮失败在日志里不可见 + `reply_chars` 恒 0**（归档 11.9 KB 而摘要写 0）⇒ 首轮行原样打印、`reply_chars/head` 集中回填（run_probe selftest 25→26）。

## 归档事故（如实登记）
`b3092030` 首跑（★ EXIT 0，first=0.8333 / fix=1.0 / 轮数 7/7）之后用**同一 NS** 重跑该臂，覆盖了 `data/probe/probe-agent-seed419-r419dagent-b3092030-t2.json`
与 6 份归档回复 ⇒ 该次读数**只剩会话记录，磁盘不可复验**。此后加 `REFUSE_NS_COLLISION` 闸禁止同 NS 重跑；本文件表里 #3 行标「仅会话记录」。
**不把被覆盖的读数当主证据**：主证据 = #2/#4/#5（饱和）+ 控制臂 + 7 态自证；#3 只作「该配置可分化」的存在性观测。

## 成本/过程读数（`process_metrics.py --multiturn`，外部真值 = 归档回复 + 判定器产物）
| 臂(tag) | 题数 | 整题全对 | 用例级 | tokens/题 | 墙钟均(ms) |
|---|---|---|---|---|---|
| agent/r419bagent-b09141437 | 3 | 3/3 | 1.0 | 11911.3 | 144960 |
| agent/r419cagent-b2091515 | 6 | 6/6 | 1.0 | 9217.7 | 93357 |
| agent/r419dagent-b3092030 | 6 | 6/6 | 1.0 | 10490.5 | 98429 |

## 诚实边界
① 真机侧**未稳定复现**分化（3/4 饱和）⇒ 本条**不构成**「r1 判别链路增益已确证」；② n=6、单族（`json_mini`）非分布；
③ 链不落 `completionTokens` ⇒ 成本只有 prompt 侧 + 墙钟；④ `json_mini` 对该链已近天花板（R417 的 1/3 读数系旧提取器所致，提取器修好后分数上移）。
