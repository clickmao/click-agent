# click-rover 驻留 / 内存回收接前向 —— 真机证据（R390）

> 轮次: **R390**（v0.23.0 · 焦点① 剩余件）／日期: 2026-09-13
> 目标（用户口径逐字）: "只常驻活性高的张量（不再使用的张量，可以主动从内存释放（做内存回收）"。
> 判据（本轮自定，先立后证）: ① **驱逐必须真触发**（不是账面数字）；② 驱逐/重载后前向结果 **逐位一致**；③ 预算语义**只声明一次**，判定与打印同源派生。
> 原始输出: `/tmp/r390/evidence.log`（45 行，下述引用逐字来自该文件）。

---

## 0. 本轮之前的状态与靶点

- 驻留账存在（`Runtime/TensorResidency.cs`）但**未接进前向**：前向自己直接 `GgufReader.Tensor(...)` 物化，**从不走驻留管理** ⇒ 驻留账在前向里恒为空。
- 且实现在"预算 ≤ 0"时**直接返回**（视为无上限），而 CLI 判语按 `peak <= budgetBytes` 判 ⇒ **同一数字被两层各自解释**。
- 后果（真机实测，修复前）: `--budget-mb 0` ⇒ `peak=999MB > budget=0` **但 `evicts=0`** —— 账面同时出现"未超限（未驱逐）"与"已超限"两种说法，**驱逐/回收路径从未被走到**。

## 1. 交付件

| 文件 | 作用 |
|---|---|
| `src/click-rover/Infer/ForwardPass.cs` | 前向增 `pins` / `reclaimPerToken` 两参；每 token 末 `ReclaimAll()`；暴露 `ResidentCount`（只数**物化**张量） |
| `src/click-rover/Cli/ForwardCli.cs` | `--budget-mb` / `--budget-kb` / `--budget-bytes` / `--no-pin` / `--reclaim-per-token`；输出 `residency_scope` + `residency_verdict` 两行账面 |
| `src/click-rover/Cli/ResidencySelfTest.cs` | **10 例自证套件**（真 GGUF 夹具、零 shell、零外部进程） |
| `src/click-rover/Runtime/TensorResidency.cs` | 预算语义显式声明：`Ledger.BudgetUnlimited = budget <= 0`；`EnforceBudget` 与判语同源 |
| `src/click-rover/Cli/RoverCli.cs` | `residency <gguf> [--budget-bytes N] [--budget-mb N] [--pin a,b] [--selftest]` 子命令 |

## 2. 自证套件 —— `residency --selftest`（真 7B 夹具，10/10，exit 0）

夹具直接用**真 7B GGUF**（`prover7b-q4km.gguf`，4,223,362,304 B，取 12 张真张量，最小 `blk.0.attn_norm.weight` = 16,384 B）：

```
residency_selftest{file=prover7b-q4km.gguf file_bytes=4223362304 fixture_tensors=12 smallest=blk.0.attn_norm.weight smallest_bytes=16384}
selftest{case=budget_bound_respected ok=True detail=resident=32768 budget=32768 max_incoming=16384 bound=32768}
selftest{case=lru_evicts_fire ok=True detail=evicts=10 reclaimed=163840}
selftest{case=negctrl_evict_is_real_release ok=True detail=freed_span_access=ObjectDisposedException evicts=10}
selftest{case=ledger_identity_loaded_eq_resident_plus_reclaimed ok=True detail=loaded=196608 resident=32768 reclaimed=163840}
selftest{case=lru_victim_is_oldest ok=True detail=order=blk.0.attn_norm.weight->blk.0.ffn_norm.weight->blk.1.attn_norm.weight victim=blk.0.attn_norm.weight freed=True second_alive=True third_alive=True evicts=1 resident=2 bytes=16384}
selftest{case=pinned_never_evicted ok=True detail=pinned=blk.0.attn_norm.weight alive=True evicts=4 resident=2}
selftest{case=stream_window_no_materialize ok=True detail=resident_count=0 resident_bytes=0 window_bytes=16384 tensor_bytes=16384 streamed_delta=16384}
selftest{case=negctrl_all_pinned_reports_over_budget_honestly ok=True detail=evicts=0 resident=65536 budget=1 over=True verdict=budget_exceeded_honest}
selftest{case=reclaim_all_frees_exactly_unpinned ok=True detail=freed=65536 expected_nonpinned=65536 resident_before=81920 resident_after=1 pinned_kept=16384}
selftest{case=budget_semantics_declared_once ok=True detail=zero_budget_unlimited=True evicts_on_unlimited=0 resident_kept=2 positive_budget_unlimited=False}
selftest{ran=10 pass=10 fail=0 tokens=0 engine=residency file=prover7b-q4km.gguf}
exit=0
```

tiny 夹具复跑同为 `selftest{ran=10 pass=10 fail=0 ... file=tiny-gqa-untied.gguf}`、`exit=0`。

**每条断言绑组件真实行为（不是账面数字）**：

| 用例 | 真断言 |
|---|---|
| `budget_bound_respected` | 驱逐后驻留 ≤ 预算（`resident=32768 budget=32768`，上界含单张量） |
| `lru_evicts_fire` | 超预算**真发生驱逐**（`evicts=10`）且释放字节精确（`reclaimed=163840`） |
| `negctrl_evict_is_real_release`（**负控**） | 驱逐后访问受害者缓冲 **必须抛 `ObjectDisposedException`** ⇒ "只加计数不释放"的实现在此必红 |
| `ledger_identity_…` | `loaded == resident + reclaimed`（196,608 = 32,768 + 163,840） |
| `lru_victim_is_oldest` | 受害者 = `LastUseTick` 最小者，且**在驱逐发生的那一刻**判定次序；受害张量 `freed=True`、后两张 `alive=True` |
| `pinned_never_evicted` | pin 的张量在 4 次驱逐中 `alive=True` |
| `stream_window_no_materialize` | 量化权重走流窗口：`resident_count=0 resident_bytes=0` 而 `streamed_delta=16384` ⇒ **量化权重不物化、不计入驻留** |
| `negctrl_all_pinned_…`（**负控**） | 全 pin + 预算 1 B ⇒ 必须 `evicts=0` 并**如实报** `budget_exceeded_honest`（不许伪报符合预算） |
| `reclaim_all_frees_exactly_unpinned` | `ReclaimAll()` 释放额 = 非常驻驻留之和（65,536 = 65,536），pin 的 16,384 被保留 |
| `budget_semantics_declared_once` | 预算 0 ⇒ `zero_budget_unlimited=True` 且 `evicts_on_unlimited=0`（无上限不是"必然超限"）；预算 > 0 ⇒ `positive_budget_unlimited=False` |

## 3. 接前向真机对账（判据：受限 vs 默认 **逐位一致**）

### tiny（`tiny-gqa-untied.gguf`，3 token，f32）

```
# 默认（pin 全部 norm，预算 96 MiB）
residency_scope{budget_bytes=100663296 budget_unlimited=False pin_mode=default_norms reclaim_each_step=False}
residency_verdict{peak_resident=1280 budget=100663296 peak_within_budget=True evicts=0 reclaims=0 loads=5 hits=8 misses=5 hit_rate=0.6154 resident_end=5 verdict=within_budget}
# 预算 0（语义 = 无上限；修复前此处会同时打印"未驱逐"与"超限"）
residency_scope{budget_bytes=0 budget_unlimited=True pin_mode=default_norms reclaim_each_step=False}
residency_verdict{peak_resident=1280 budget=0 peak_within_budget=True evicts=0 reclaims=0 loads=5 hits=8 misses=5 hit_rate=0.6154 resident_end=5 verdict=budget_unlimited}
# 受限（--no-pin --budget-bytes 256 --reclaim-per-token）⇒ 驱逐真触发
residency_scope{budget_bytes=256 budget_unlimited=False pin_mode=none reclaim_each_step=True}
residency_verdict{peak_resident=512 budget=256 peak_within_budget=False evicts=9 reclaims=12 loads=13 hits=0 misses=13 hit_rate=0.0000 resident_end=1 verdict=budget_exceeded_honest}
```

逐位对账（**8/8 文件 `cmp` 全同**）:

```
identical dims.txt caa618221669facb
identical hidden_t0_blk0.bin 38f2247ea7593af2
identical hidden_t0_blk1.bin 40b7929156f62970
identical hidden_t1_blk0.bin 1dcbea0bd0e472f6
identical hidden_t1_blk1.bin e8f8400229bc9767
identical hidden_t2_blk0.bin 7633f56542e72281
identical hidden_t2_blk1.bin 4e1e429295fbde1e
identical logits.bin c5bbb3f546a640be
```

### 真 7B（DeepSeek-Prover-V2-7B GGUF-Q4_K_M，4.22 GB，2 token）

```
# 默认（pin 全部 norm）—— 热集常驻
residency_verdict{peak_resident=999424 budget=100663296 peak_within_budget=True evicts=0 reclaims=0 loads=61 hits=60 misses=61 hit_rate=0.4959 resident_end=61 verdict=within_budget}
# 受限（--no-pin --budget-bytes 16384 --reclaim-per-token）—— 驱逐真触发
residency_verdict{peak_resident=32768 budget=16384 peak_within_budget=False evicts=118 reclaims=120 loads=121 hits=0 misses=121 hit_rate=0.0000 resident_end=1 verdict=budget_exceeded_honest}
```

逐位对账（`cmp` 全同）:

```
identical dims.txt 24d2bc8519b66d39
identical logits.bin e34dabd647b50ba0        # 且 top-1 与默认一致
```

**读法（三条真断言）**：
1. **`peak = 预算 + 单张量字节`**：tiny `512 = 256 + 256`、7B `32768 = 16384 + 16384` ⇒ 驻留**真的被压在预算附近**，这是"驱逐确实发生"的充分算术证据（不驱逐则 7B 会像旧行为一样停在 999,424 B）。
2. **逐位一致**：最激进的档（每 token 全清 + 每次只允许 1 张常驻）与默认档在 tiny **8/8 文件**、7B **logits/dims** 上 `cmp` 相同 ⇒ 驱逐/重载**不改变数值结果**（重物化走同一条确定性反量化路径）。
3. **热集常驻有账**：真 7B 默认档 `loads=61 hits=60`（第 2 token 起 60/61 命中）、常驻 **999,424 B ≈ 0.023%** 模型体积 ⇒ "只常驻活性高的张量"落地为**只常驻 norm**，其余量化权重走流窗口（`resident_count=0`）。

## 4. 本轮修掉的两处真缺陷（都是"两层口径不一致"，非表面 bug）

1. **`budget <= 0` 被两层各自解释**（驱逐路径因此从未走到）。
   修法：**语义只声明一次** —— `Ledger.BudgetUnlimited = budget <= 0`，`EnforceBudget` 与打印判语**同源派生**；同时补 `--budget-bytes`（真子张量级预算不再只能用 0/负表达）。修复后 `--budget-mb 0` 输出 `budget_unlimited=True ... verdict=budget_unlimited`，两层不再打架。
2. **自证断言本身写错**：LRU 次序原在 12 次取用**之后**判定，而次序第二张早已被后续驱逐 ⇒ 断言误红。
   修法：改为**在驱逐发生的那一刻**判定。**可复用教训**：*内存/生命周期类断言的观测点必须在事件时刻，事后观测会被后续同类事件掩盖。*

## 5. 诚实边界（不夸大）

1. 本机 **2 vCPU / ~2.2 GiB 可用内存** ⇒ 预算强度只覆盖"小到能触发驱逐"的量级，**未做长序列下的峰值 RSS 压测**。
2. 驱逐策略是 **LRU-on-tick**；`IsHot` 访问计数**未作为前向的驱逐豁免**使用（前向只在 `--no-pin` 与 默认 pin 两档切换，未实装"访问计数晋升为常驻"）。
3. `--reclaim-per-token` 每 token 重物化 norm（`hits` 归 0），是**故意**的对照档，非默认行为；默认档不回收，故 `reclaims=0`。
4. **`resident_end=1` 且 `verdict=budget_exceeded_honest` 是设计内的诚实报错**：预算 16,384 B 装不下"下一张进来时还要留一张"的峰值 ⇒ 如实报超限，不静默降级、不伪报。
5. 未做多线程/流水线下的驻留并发安全论证（前向当前单线程）。
6. 与 agent 主链的**挂载仍未接线**（C7/C8）——本轮只完成"前向 ↔ 驻留"，未完成"agent ↔ click-rover"。

## 6. 复现命令

```bash
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
dotnet build src/click-rover/click-rover.csproj -c Release          # 0 Warning / 0 Error
R=src/click-rover/bin/Release/net10.0/click-rover.dll
dotnet $R residency --selftest /tmp/models/prover7b-q4km.gguf      # 判据: ran=10 pass=10 fail=0 且 exit 0
dotnet $R forward /tmp/tiny/tiny-gqa-untied.gguf --tokens 1,2,3 --ctx 64 --dump /tmp/resid/def
dotnet $R forward /tmp/tiny/tiny-gqa-untied.gguf --tokens 1,2,3 --ctx 64 \
  --no-pin --budget-bytes 256 --reclaim-per-token --dump /tmp/resid/ev
for f in $(cd /tmp/resid/def && ls); do cmp /tmp/resid/def/$f /tmp/resid/ev/$f; done   # 8/8 全同
```
