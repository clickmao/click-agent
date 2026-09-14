# R401 · 探针 rover 臂「解法级 KPI」对比 —— 步2 归因报告

日期: 2026-09-14 · 计划项: R401（v0.22.0-longterm-backlog.md，最前未完成项）
范围: 只做「解法级对比」的一条线：rover 臂**能否**产出可信读数。本轮不宣称能力高低。

## 0. 一句话结论

rover 臂此前**没有一条可信读数**：不是模型不会做题，而是测量链上三处缺陷（渲染错字节 / 臂不可用被当成 0 分 / 墙钟与 token 预算不协调）
使读数要么为假、要么为零证据。三处已修并各自留下机检证据；校准常数已真机实测。

## 1. 缺陷 1（测量侧·最严重）：送达对账是**自证型断言**，看不见渲染错误

- 现象: 探针渲染出的 prompt 首部是字面文本 `151646`（6 字符），而模型自带模板要求的是**特殊符号**本体。
- 根因: 渲染时把「特殊符号的编号」当作「特殊符号文本」代入模板变量。模板变量按语义接收的是符号文本。
- 为什么既有判据全绿: A4「原样送达」比较的是「我方摘要 == 引擎回显摘要」——两侧算的是**同一串字节**，对「字节本身错」零分辨率。
  即：**传递无损 ≠ 内容正确**。
- 修法: 从模型元数据表把编号解析为符号文本后再代入（`eval/probe/rover_prompt.py::resolve_special`），
  并在证据里落 `bos_token` / `special_tokens_resolved` / `prompt_head`。
- 新判据（跨实现字节对账）: 我方渲染 vs 引擎（独立实现，读同一个自带模板）对同一任务的渲染，**摘要必须逐字节相等**。
  - 证据: `eval/rover/r401/prompt-parity-crossimpl.json` → **2/2 byte-equal**
    （m001 `5866860630bf53ff`、m002 `b1c529f462b5e05d`），verdict=`all-byte-equal`。
  - 复核口径: 引擎侧 `generate --chat` 用同一模型同一模板渲染，回报 `prompt_sha256`（real machine，非模拟）。
- 顺带定性修正: 旧判据「我方版式必须 ≠ 引擎硬编码版式」在本模型上**已失效**——
  本模型的模板本身就是该版式，两者相等是**预期**而非缺陷；该判据已降级为事实记录，不再作 gate。

## 2. 缺陷 2（链路侧）：臂不可用被记成「能力 0 分」

- 现象: 第一次 rover 臂 0.67 s「跑完」，`per_task` = `no_final 0/1`，`raw json` 目录为空。
- 根因: 子进程缺少运行时根路径 ⇒ 引擎宿主 `exit 131`（app-launch-failed），**引擎根本没启动**；
  harness 却按「模型没给出 FINAL」计入失败模式。
  这是把**臂不可用**读成**能力为零**——与「机制未触发却下无效结论」同族。
- 修法（`eval/probe/run_probe.py::solve_rover`）:
  1. 显式注入运行时环境（不依赖调用方 shell 的导出）；
  2. **跑前清同名残留产物**——否则引擎崩溃时 harness 会把上一轮 json 当本轮答案读（静默串轮）；
  3. 启动失败 ⇒ `arm_status=unavailable`，**不计入分母**，单列 `arm_unavailable` 计数 + `validity` 字段，
     不再伪装成一个 0 分用例。
- 证据: 修复后同一臂不再出现 `exit 131`；`meta.arm_status` / `validity` 字段随产物落盘。

## 3. 缺陷 3（预算协同）：墙钟与 token 预算不协调 ⇒ 零证据

- 现象: 校准前那次臂跑满 1000 s 被 harness SIGKILL：`exit -9`、`budget_limited=true`、
  `stop="solve timeout"`、`reply_chars=0`、raw json **根本没落盘**。
  烧掉 1000 s 却**零信息**——最坏的读数形态（比失败更差）。
- 真机校准常数（`/tmp/r401-rate.json`，m001 同一 prompt，48 token 限量跑）:
  - `prompt_tokens=78`、`ms_prefill=131814.8`（≈1.69 s/prompt-token）
  - `ms_per_token=2157.3`（≈0.4635 token/s）
  - `stop=max_tokens`、`eos=151643`、`text_head="<think>\n嗯，我现在要解这个同余方程…"`
- 由此得**可分辨判据**: `384 token 预算 ≈ 132 s prefill + 384×2.157 s ≈ 960 s 生成`，
  与默认 1000 s 墙钟几乎相等 ⇒ **任何并发负载都会把读数变成零证据**。
- 修法: 给引擎传一个**小于** harness 墙钟的 `--max-seconds`（`PROBE_ROVER_MAX_SECONDS`，默认 `solve_timeout-60`），
  引擎按墙钟**优雅停止并落盘部分产物**（`stop=seconds`）⇒ 至少留下证据，而不是被 SIGKILL。

## 4. 读数（本轮）

| 序号 | 条件 | 结果 | 定性 |
|---|---|---|---|
| ① | 修复渲染前（0.67 s） | `no_final 0/1` · exit 131 | **无效读数**（臂不可用，已改判） |
| ② | 渲染已修 + 未校准预算（1000 s） | `budget_limited` · exit -9 · reply_chars=0 | **非能力读数**（预算不协调） |
| ③ | 渲染已修 + 预算协同（`--max-seconds 900`） | `no_final` · exit 0 · `stop=seconds` · 290 步 · `reply_chars=398` · 结构未闭合 | **有效读数，但语义是「未答完」不是「答错」** |

**臂间对比（同题集 sha `09d7d4327ede04b7`，R401 目标口径）**

| 臂 | 通率 | 耗时 | 预算/停止 |
|---|---|---|---|
| 判定器正控（oracle） | **2/2** | 0.0 s | — |
| 远端 API 臂（agent） | **2/2** | 13.4 s | 无 token 限量 |
| 本机引擎臂（rover·模板对等） | **0/1** | 901.6 s | `max_tokens=384`；`stop=seconds`（墙钟先到） |

产物: `eval/rover/r401/solution-level-kpi.json`（`measurement_valid=true`，**8/8** 有效性断言全过）
台账: `data/probe/rover_engine_kpi.jsonl`（同键幂等，重复跑不污染趋势）

**③ 的 0 分归因（新增 A7，机检）**: `reply_completeness = {stop: seconds, steps: 290, reply_chars: 398,
structural_open_tail: true, tail: "x=2：", verdict: "incomplete-not-wrong"}`。
模型在本机引擎上产出了**连贯的中文推理**（分解模数 15 → 分别解 mod 3 / mod 5 → 正在枚举 x），
但 384 token 预算 + 900 s 墙钟先用尽，**从未进入正文作答阶段**——所以这一格是「没答完」，不是「答不出来」。
（对比 R406/R407 时期的乱码输出，本轮文本连贯 = 前向修复在真实生成链上生效的旁证。）
A7 的作用: 只要臂没拿到分，就必须带「未完成 / 臂不可用」的显式归因，**禁止 0 分无解释**地进入对比表。

## 5. 诚实边界

- 只跑 1 题（m001 `quadratic_residue_count`）；m002 只有渲染对账，无解法读数。
- 本机 2 vCPU、无 GPU；同一时段有**并发兄弟进程**（R407 AOT 线）争 CPU ⇒ 所有 `elapsed_s` **只作指示性**，
  不作性能结论；token 速率常数在无争用时重测为准。
- 「render 与引擎逐字节相等」只证明**输入一致**，不证明模板本身选得对（模板来自模型自带元数据，取舍见 R406）。
- 本轮读数的 0 是**预算不足**而非能力判定：本机引擎的 token 预算尚未调到模型自然停止点，因此**不得**用它宣称
  「本机引擎做不出该题」；能宣称的只有「在 384 token / 900 s 下未产出 FINAL」。
- 同一时段有并发兄弟进程争 CPU（本轮实测 `ms_per_token=2684.8`，比无争用校准值 2157.3 慢 24%），
  速率类数字只作指示性。
- `budget_limited` 字段语义本轮修正（`stop=seconds` 也计入预算受限）：修正**下轮跑臂才体现在产物里**，
  本轮该字段值来自修复前的那次跑（`stop=seconds` 却报 `false`），已在台账里如实保留、不追改。
- 本轮不比较「远端 API vs 本机引擎」的**质量**差异：本机臂尚未拿到一条完整解。

## 6. 下轮候选

1. ③ 确实停在思考段 ⇒ 下轮按 **wall ≈ prefill + N×2.157 s × 争用系数** 提高预算后重跑 m001
   （参考: N=1024 ⇒ 132 + 1024×2.157×1.2 ≈ 2780 s ⇒ `--max-seconds 2800`、`--solve-timeout 3000`）。
   备选: 让引擎把**思考段与正文预算分开计**，否则纯靠加墙钟换 token 会线性吃时间。
2. 补齐 m002 解法读数后，才做 rover vs 远端 API 的**逐题对账**（同题集 sha 才可比）。
3. 把本节三条缺陷抽象为**语言无关**通用教训 → 已落 `skills/self-verification-blindspots/SKILL.md`。
