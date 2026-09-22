# R632 · 器件面收口（判据族对齐 / 策略声明 / 驱动器声明刷新）＋ 文献小步

**级别：L2**（机检器行为断言 + 注入缺陷负控）；**轮形 = 器件/判决面收口轮**（零真机臂 / 零远端调用 /
零产品源码改动 / 零新增夹具 / 零新增开关）。数据面 = **R631 冻结快照**（零重测）。证据可复现命令见文末。

## 1. 关闭的三处 R631 自捕缺陷

| # | 缺陷 | 判别形态 | 修前 → 修后 |
|---|---|---|---|
| D2 | 裁判件**判据键族 ≠ 预注册**（缺 5 / 多 15） | 键集合逐键相等 ∧ 主判据键由**机读字段**绑定 ∧ `verdict_source` 显式 | 旧件 STEP1 判红 → 修后 D1 全绿（`keys_equal=true`） |
| D3 | 轮驱动器**头部声明滞后**（6/6 项与实盘不符） | 声明块与实盘段**同文件**逐项比对；缺声明 ≠ 一致 | `checked=6 drifted=6` → `drifted=0 absent=0`；实盘段 sha256 逐字节不变 |
| D4 | —（本轮**新捕**）D4 取数层假红 | 同一判据两条取数路径（现盘 sha vs `git cat-file blob` bytes） | `rc=2`（假红）→ `rc=3`；四件与 HEAD blob 逐字节相等 |

## 2. 本轮新捕（全部入档，见 `eval/rover/r632/evidence/instrument-defects-r632.json`）

1. **D4 取数层假红**：`git show HEAD:<path>` + `.strip()` 丢尾字节 ⇒ 四件 sha 必不等 ⇒ 判红（**测量层**缺陷，非被测）。
2. **缺声明判绿**：声明检查器 v1 对无声明块驱动器判 `PASS`（把「缺声明」读成「一致」）⇒ 假绿；
   修法 = 三态 verdict（`PASS` / `DECL_DRIFT` / **`DECL_ABSENT`**）+ 退出码只读 verdict；四态正负控 **8/8**。
3. **同名判据两套谓词**：R631 kpi 行把 `J1_fallback_exercised` 读作 `NOT_EXERCISED`，按 prereg-r631 **同一键名**谓词
   重审冻结件得 **pass**（`fallback_runs=6`）⇒ 旧读数**证伪**；**不改写历史行**，纠偏只落本轮。
4. **台账自带假断言**：R632 台账初稿称「`prefix_tokens` 未落盘 / 无消费者」——为假
   （生产者 `src/agent.modelqueue/LocalSessionCacheLedger.cs:86,100,111,112`、消费者 `eval/rover/r411/verify.py:43`、
   阈值件 `eval/rover/r410/prefix-reuse.json:3`）⇒ 同轮勘误；教训：**一次 grep 无命中 ≠ 不存在**。

## 3. 负控（有牙证明）

| 器具 | 形态 | 读数 |
|---|---|---|
| `negctl_r632.py`（披露式三步） | STEP1 修前必红 / STEP2 修后必绿 / STEP3 变体必转红 | rc=0；STEP1 red · STEP2 green · **变体 10/10 转红** |
| `decl_driver_check_r632.py --selftest` | 合成一致头 PASS / 字段注入 5 种 DECL_DRIFT / 空头 DECL_ABSENT | rc=0 · teeth=true · 8/8 判中 |

## 4. 重审读数（R631 冻结面；**本轮不产生能力面结论**）

- `J0 ✅ · J1 ✅(fallback_runs=6) · J4a ❌ · J4b ✅ · J3 ❌ · J6 informational · W ❌(valid=1) · P11 ✅(前置器 rc=1)`
- 判决 **rc=3**「判据不可判（有效窗<2）」⇒ RF0005 §3：**停链先造窗**（禁下调阈值）。
- 判决来源显式：`verdict_source.key = J4a_capability_replication;J3_cost`（次级红 = rc1 档；rc 抬到 3 的是 **W**）。
- `D2` 对 R631 既有窗 **`POLICY_ACTIVE=false`**（B2 拒绝追溯套用）⇒ 该窗单列标注取 **R4 人工口径**，不得读作机检行使。
- 铁律 11：前置器 rc=1 ⇒ R631 质量/成本列**仍标「参考（未可验收）」**，本轮不改写。

## 5. 声明面全表复核

`python3 eval/capability/decl_sweep.py --check` ⇒ `SER_ASSERT=OK` · `checked=30 drifted=0`（只读，一字节未动）。
`run_r631.sh` 不在 `eval/capability/instruments.json` 常设表内（逐轮驱动器），其声明由 D3 件单独钉住。

## 6. 文献小步（arXiv 面顺延，第二来源 2 篇）

- **出口可用性分离**：`search_arxiv.py` 三式 **HTTP 429**（内置退避重试亦 429）、raw curl 逐目标 **000 timeout ×2 + 429 ×2**、
  同窗对照 `arxiv.org/abs/...` 200 ⇒ 判 **「顺延（出口 429）」**，**不计**入连续 0 采信（未达 3 ⇒ **不降频**）。
- **第二来源**（官方工程文档，只作机制来源）：OpenAI《Prompt caching》与 vLLM《Automatic Prefix Caching》各 1 条逐字引文；
  两条均判「**已实施（同形机制本仓既有）**」/「观察」⇒ **无新候选**；`required_prefix_tokens=4224` 属本仓自标定，**禁与厂商 1,024 互换**。
- 台账**追加**：`docs/research/lit-review-ledger.md` 577 → 608 行（numstat **31/0**，无删除）。

## 7. 证据 sha256（本档落盘时现盘字节）

| sha256 | 文件 |
|---|---|
| `1c941e00e5775d57…` | `eval/rover/r632/prereg-r632.json` |
| `d0cca7a84c12192a…` | `eval/rover/r632/verdict-r632.json` |
| `cacd933fa194ddae…` | `eval/rover/r632/judge_align_r632.py` |
| `d913380ce65409e4…` | `eval/rover/r632/policy_gate_r632.py` |
| `bb62c27381c0ab18…` | `eval/rover/r632/decl_driver_check_r632.py` |
| `9b7c094a918f0a40…` | `eval/rover/r632/negctl_r632.py` |
| `4050a6176c64c44e…` | `eval/rover/r632/refresh_driver_decl_r632.py` |
| `0c68d3df31a73158…` | `eval/rover/r632/report-r632.md` |
| `27fa42e9865ba63e…` | `eval/rover/r632/evidence/instrument-defects-r632.json` |
| `d39abff9c430e9b6…` | `eval/rover/r632/evidence/decl-before-r631.json` |
| `b07f80d3e7d96f1e…` | `eval/rover/r632/evidence/decl-after-r631.json` |
| `2b5c1764f83a3546…` | `eval/rover/r632/evidence/decl-refresh-r631.json` |
| `b2ee86117664995b…` | `eval/rover/r632/evidence/decl-selftest-r632.json` |
| `4547e0fdffd3d319…` | `eval/rover/r632/evidence/negctl-r632.json` |
| `92b06789066d8031…` | `eval/rover/r631/run_r631.sh` |
| `3f34c1190f51c572…` | `docs/research/lit-review-ledger.md` |

## 8. 复现命令

```bash
cd /home/agentuser/AgentFramework
python3 eval/rover/r632/decl_driver_check_r632.py --selftest                                   # rc=0 · teeth=true · 8/8
python3 eval/rover/r632/decl_driver_check_r632.py --sh eval/rover/r631/run_r631.sh --round r631  # drifted=0 absent=0
python3 eval/rover/r632/negctl_r632.py                                                          # rc=0 · 变体 10/10 转红
python3 eval/rover/r632/policy_gate_r632.py                                                     # 策略三态（含 B2 背时序拒绝）
python3 eval/rover/r632/judge_align_r632.py --D ~/.agentframework/harness/runs/r631 \
        --json eval/rover/r632/verdict-r632.json                                                # rc=3（有效窗<2）
python3 eval/capability/decl_sweep.py --check                                                   # checked=30 drifted=0
python3 eval/capability/status_gen.py --check                                                   # 收口判据 PASS
```
