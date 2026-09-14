# R417 证据清单（探针反饱和 / 质量分数前置）

> 目录名说明：本轮最初按 `r416` 命名，随后发现 **R416 已被 D2 收口轮占用**（`2b831ac`/`f36f897`）⇒ 本轮定名 **R417**，目录与产物已改名。
> 日志文件保留创建时的原名 `/tmp/r416-run1.log`、`/tmp/r416-disc.log`、`/tmp/r416-json.log`。

## 臂

| 脚本 | 作用 | 日志 |
|---|---|---|
| `run1_same_seed.sh` | 仪器自检（tasks/grade/run_probe/kpi_probe）+ **同题复跑** seed=20260913（agent，AOT `/tmp/pub_r414/agenthost`） | `/tmp/r416-run1.log`、`/tmp/r416-probe.log` |
| `run2_discrimination.sh` | 判别力自证：oracle 正控（`topo_min`+`vm_run`）+ 2 个缺陷注入负控 + 真机 agent 新族 | `/tmp/r416-disc.log` |
| `run3_json.sh` | `json_mini`：oracle 正控 / `json_loose` 负控 / 真机 agent | `/tmp/r416-json.log` |

## 读数（外部真值 = `data/probe/probe-r417-*.json`）

| 面板 | 读数 | 判定 |
|---|---|---|
| 同题复跑 seed 20260913 | 1.0（35/35），与 2026-09-13 基线逐族一致 | 饱和确认 |
| oracle `topo_min`+`vm_run` | 49/49；整题全对 4/4 | 正控 PASS |
| oracle `json_mini` | 36/36；整题全对 2/2 | 正控 PASS |
| `mutation:topo_dfs` | 24/52；整题全对 0/4 | 负控 PASS |
| `mutation:vm_noerr` | 29/48；整题全对 0/4（timeout 2 / runtime_error） | 负控 PASS |
| `mutation:json_loose` | 54/72=0.75；整题全对 0/4 | 负控 PASS |
| agent `topo_min`+`vm_run`（n=6） | 74/74；整题全对 6/6 | **仍饱和** |
| agent `json_mini`（n=3） | 见下「json_mini 真机」 | — |

### json_mini 真机（首个非饱和质量分数）

| 口径 | 用例级 | 整题全对 | 来源 |
|---|---|---|---|
| 记录口径（缺陷仪器） | 27/54 = 0.5000 | 0/3 | `data/probe/probe-r417-json-agent.json` |
| **修正口径**（同批归档回复离线复判） | **47/54 = 0.8704** | **1/3** | `data/probe/probe-r417-json-regrade.json`；`--solver file:/tmp/r417-replay` |

逐题（修正口径）：p001 12/18（7 处**输出漏引号**）· p002 **18/18 满分** · p003 17/18（唯一失分 = `tight_gen` 强制的**裸 TAB 紧用例**，期望 `ERR`）。

### 仪器两处真缺陷（本轮真机暴露 ⇒ 已修）

1. `extract_code()` 逐候选"首个可编译前缀"⇒ 长回复下把 10 KB 程序判成 **46 字符注释残片**（p001 记录 0/18，真值 12/18）。修：分两轮（先整体可编译者）+ 前缀下限 64 字符。
2. `grade_program()` 先判 `exit != 0` ⇒ **stdout 正确但 `sys.exit(1)`** 被顶成 `runtime_error`（p002 记录 10/18，真值 18/18）。修：stdout 优先（`exit_nonzero_ok` 计数；期望空输出时崩溃仍算失败）。

⇒ `eval/probe/grade.py --selftest` **25 → 29**（4 条新负控固化）。

## 复验命令

```bash
cd /home/agentuser/AgentFramework
bash eval/rover/r417/run1_same_seed.sh
bash eval/rover/r417/run2_discrimination.sh
bash eval/rover/r417/run3_json.sh
python3 scripts/dev_return_digest.py && sed -n '/## 3. 探针分数/,/## 4./p' docs/reports/dev-return-digest.md
```
