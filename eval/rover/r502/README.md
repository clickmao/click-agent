# R502 · 主线执行面：开发任务对照套件（codex-cli 外部真值 × 机械判分）

> 本文由 `docs/external-reference-harness.md` §7 机械派生（单一真源，禁手改）+ 机取预注册哈希。
> 生成时间: 2026-09-17 · R502 · 状态: **铺件 + 预注册(v2, 含游戏族) + 负控全绿；真机首跑待窗（R501 收口后）**

## 7. 开发任务对照套件 R502（主线常态执行面 · 2026-09-17）

主线（用户钦定更正）= 用「随机程序 / 数学难题 / 游戏」真实开发任务 + 外部真值（codex-cli，同一真实模型）同环境·同输入对照做质量自检。本节 = 该主线的可复跑执行面。

| 件 | 路径 |
|---|---|
| 冻结题集（**6 题** = 4 程序族 `life_k`(游戏族)/`topo_min`/`vm_run`/`json_mini` + 2 见证型数学族 `witness_sqrt_mod`/`witness_min_counterexample`，seed 20260917，probe 口径 sha `18e7c8dddb54e220`；oracle 正控 **57/57=1.0**；逐族定向 dump 后机合并，禁抽样碰运气） | `eval/rover/r502/taskset-r502.json` |
| 外部真值解法器（codex-cli 作为 probe `command:` 解法：stdin 题面 → stdout 回复；空回 = no_code，不记 0 分） | `eval/rover/r502/codex_solver_r502.py` |
| 对照 runner（同冻结题集 / 同 adapter / 同机械判分；缺任一侧面 ⇒ rc=3） | `eval/rover/r502/run_contrast_r502.sh` |
| 预注册（**先于首跑**，机取 **9 件**哈希 + 6 条判据，禁手抄；题集元信息与正控基线亦机取） | `eval/rover/r502/prereg_r502.json` |
| 对照判分（**只读落盘**，不重跑；产出 `verdict-r502.json`） | `eval/rover/r502/judge_contrast_r502.py` |
| 负控（仪器两端 / fail-closed / 预注册三态 / solver 自检） | `eval/rover/r502/nc_r502.sh` |

- **codex 持久路径**：`~/.agentframework/tools/codex-env/node_modules/.bin/codex`（`@openai/codex@0.154.0`，与 R455 同版 ⇒ 跨轮同版可复现）；旧 `/tmp/codexenv` 仍在，但 /tmp 不可托付。
- **判据（预注册，先于首跑）**：H1 仪器判别力两端（oracle 1.0 ∧ mutation 0.0）· H2 外部真值可用性（0 题 ⇒ 记 `unreported`，禁当 0 分能力）· H3 同输入机检（两侧 `taskset_sha` 相等且 == 预注册值）· H4 同模型机检（adapter 落盘 model 字段）· H5 读数分列（逐题 mode + 两侧 usage 分列，**禁**据 token 总量断言优劣）· H6 fail-closed（缺侧 rc=3）。
- **首跑前负控实测（2026-09-17，全绿）**：程序面 oracle 1/1 ∧ `mutation:json_loose` 0/1；**游戏族** oracle 1/1 ∧ `mutation:life_wrap` 0 整题全对（0/1，且 3 题实测 16/36 用例 ⇒ 变异被隐藏用例抓到）；缺侧 judge rc=3；预注册三态 rc 0/1/3 + 复原 0；solver `--selftest`/`--dry-run` rc=0；生成器自测 `tasks.py --selftest` **47/47**。

```
bash eval/rover/r502/nc_r502.sh                                  # 首跑前负控（本地，不吃真机窗）
bash eval/rover/r502/run_contrast_r502.sh                        # 两侧对照（需内存窗干净 + 无并发真机测量）
python3 eval/rover/r502/judge_contrast_r502.py --codex <cj> --agent <aj> \
        --prereg eval/rover/r502/prereg_r502.json --adapter-log /tmp/r502_env/adapter
```
- **待办**：① ~~真机首跑~~ **已完成（2026-09-17，rc=0 全绿）**：同窗 6 题对照 —— 两侧整题全对 **6/6 = 1.000**（57/57 用例）；codex 14 调用/113,850 tok/97.18 s，本侧 10 调用/**49,709 tok**/21.12 s（tokens −56.3%、调用 −28.6%、墙钟 −78.3%，同质量）；同模型机检 24/24 行 `deepseek-chat`；② 扩面（更多游戏族/见证族 ⇒ 重跑预注册）；③ 效果面残留：R501 t8 本地改写被 guard 以 `question_mark` 拒收（见 improvements v0.98.2）。

### 7.1 首跑读数（真机, 2026-09-17, rc=0）

| 侧 | 整题全对 | 用例 | 调用 | tokens | 墙钟 |
|---|---|---|---|---|---|
| 外部真值 codex-cli（同模型） | 6/6 = 1.000 | 57/57 | 14 | 113,850 | 97.18 s |
| 本侧 AOT agenthost | 6/6 = 1.000 | 57/57 | 10 | **49,709** | **21.12 s** |

判据: H1 仪器判别力 ✓ · H2 外部真值可用 ✓ · H3 同输入机检 ✓（两侧 taskset_sha `18e7c8dddb54e220`）· H4 同模型机检 ✓（落盘 `request.upstream_request.model`；v2 修字段路径）· H5 分列（禁总量断言）✓。
**诚实边界**: 两侧静态面不同源（codex 自带 agentic 循环/沙箱/命令执行）⇒ **禁据 token 总量断言优劣**；n=6 单跑单窗；prereg 标签 `deepseek-flash` 为本仓侧标签、供应商侧名 `deepseek-chat`。

## 文件清单（本目录）

| 文件 | 作用 |
|---|---|
| `taskset-r502.json` | 冻结题集（6 题；probe 口径 sha `18e7c8dddb54e220`；oracle 正控 rate=None） |
| `codex_solver_r502.py` | 外部真值解法器（probe `command:` 适配；`--selftest` / `--dry-run`） |
| `codex_fixture_r502.jsonl` | solver 自检夹具（无网络校验抽取/usage/错误分支） |
| `run_contrast_r502.sh` | 两侧对照 runner（预注册闸 + 夹具同源断言 + adapter 健康检查 + 收口） |
| `judge_contrast_r502.py` | 对照判分（只读落盘；H2..H6） |
| `make_prereg_r502.py` | 预注册生成/校验（9 件哈希 + 6 条判据；`--check` 三态） |
| `nc_r502.sh` | 负控（NC1 程序面 / NC1b 游戏族 / NC2 缺侧 / NC3 预注册三态 / NC4-5 solver） |
| `taskset-r502nc.json`、`taskset-r502nc-game.json` | 负控题集（程序面 / 游戏族） |
| `make_evidence_r502.sh` | 证据归档（`.log/.jsonl` → `.txt`，R500 铁律） |
| `prereg_r502.json` | 预注册落盘件（首跑前；含 `checks_prefirstrun`） |

## 首跑前负控读数（机取）

- NC1 程序面: oracle whole_ok=1/1 ∧ `mutation:json_loose` whole_ok=0 ⇒ True
- NC1b 游戏族: oracle whole_ok=1/1 ∧ `mutation:life_wrap` whole_ok=0 ⇒ True
- NC2 缺侧 judge rc=3（期望 3）· NC4/NC5 solver rc=0/0（期望 0）
- NC3 预注册三态 rc={'uniform': 0, 'drift': 1, 'missing': 3, 'restored': 0}

## 诚实边界

- 首跑**未进行**：以上全部为「器具自检」读数（oracle/mutation 本地），**不是**外部对照读数 ⇒ 不得对外宣称任何「本 agent vs codex」结论。
- codex 侧沙箱面不对等（本机 `bwrap` 不可用 ⇒ `--dangerously-bypass-approvals-and-sandbox`），标注为已知限制。
- 两侧静态面不同源 ⇒ **禁**据 token 总量断言优劣（H5）。
- 游戏族已补（`life_k`，Conway 生命游戏第 k 代）；主线「随机游戏」面已可覆盖，但**真机读数仍缺**。
