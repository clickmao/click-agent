# R598 DAG（起手前写, 先出 DAG 再执行）

意图: 主线真机对照轮 = **判据 v3 第六窗集行使**（同被测件 + 同冻结题集, 只换窗集 w178..w180）× 外部真值 codex;
并轮推进 R597 §7 候选 ②③④⑤。候选①（产品侧处置）**待用户放行** ⇒ 零产品源码改动。

## 节点 / 依赖边

| 节点 | 内容 | 依赖 | 证据面 |
|---|---|---|---|
| N0 | 前置: keys/DOTNET/bin/codex/cfg 存在性 + 余量重派生（候选⑤ swing=r597 实测 83MB） | — | bins-r598.json, gate-margin-r598.json |
| N1 | 派生器具（命名空间/窗集替换, 判据逻辑一字不改） | N0 | derive_r598.py 断言全过 |
| N2 | 预注册先写后跑闸（prereg-r598.json, 12 证据面） | N1 | runner 第 0 步机检 |
| N3 | 真机臂轮: 3 窗 × (codex C1×1 + 产品默认档 R598D×3) = 12 跑次 | N2 | logs/runs.jsonl, snapshots/ |
| N4 | 汇总: kpi_r598（C0..C6）+ pool_taskface_r598（C7 主判据 set6）+ 铁律 11 前置器 | N3 | verdict-r598.json, taskface-pool-r598.json, precond-r598.json |
| N5 | 只读并轮: ②真值侧 wythoff 缺口归因 ③C7 负控选择面改制 ④V_int 第五窗集 ⑤余量条款 | N4 | percase/truthgap-r598.json, c7nc-r598.json, vint-r598.json |
| N6 | 落盘: §7 块 + kpi.jsonl + 本地 commit（推送暂停令在效） | N5 | git show --stat |

## 可并行面

- **无并行子 agent**: 同仓在飞写者 = 本侧（N3 真机臂轮）。N3 在飞期间其它节点**限只读且禁任何重算**
  （内存/CPU 污染读数; 起手闸 REQ=2650+MARGIN, 在飞期任何重算都可能把窗口读数推离带内）。
- N0/N1/N2 串行且必须在 N3 之前完成（预注册先写后跑闸）。

## 起手闸事件（如实登记）

本 tick 首次采样 CEIL≈2765MB ⇒ CAP = CEIL − 2650 − 60 = 55 < floor 60 ⇒ 条款 fail-closed（窗口不可开）。
处置 = 起手前清场（`sync` + `drop_caches`，page cache 回收，无数据/状态改动）⇒ CEIL≈3017MB ⇒ 窗口开启。
读数影响面 = MemAvailable（起手闸读数），**不触及被测量读数**；已在 prereg 声明。

## 收尾重启判据（按 DAG 判该重启哪条边, 不重跑全轮）

- N4 的 C7「有牙」判定 rc=2 ⇒ 重启 **N5③**（器具修法，预注册后重算; 禁令: 不得手改判据凑绿）。
- N4 的 C0 出现真值自败窗 ⇒ 该窗按 C0 标 `unreliable` 并从配对剔除（禁筛窗）; 只重算 **N4**。
- 铁律 11 rc≠0 ⇒ 只重算 **N4 的成本标注**（全部读数降级为「参考（未可验收）」），**不重跑 N3**。
- N3 出现 bin sha 漂移 / 缺跑次 ⇒ 重启 **N3**（臂身份不成立, 整轮读数作废）。
