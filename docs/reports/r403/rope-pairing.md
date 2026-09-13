# R403 · RoPE 配对约定按 arch 选择（prover7b 长期带病运行的根因）

日期: 2026-09-14 · 状态: **已修复并验证**（本机 commit 待推送；推送暂停令在效）

## 1. 现象与发现路径

追查"qwen2.5-math-1.5B-Instruct 端到端能跑但输出乱码"时，做了三项排除法：

| 步骤 | 结论 |
|---|---|
| 分词对账（HF `tokenizers 0.23.2` 独立 oracle） | **洗清**：6 个测试串逐 id 相同（含 `12345`、前导空格 ` 2`） |
| 配置读取对账（HF `config.json` vs GGUF metadata） | **洗清**：`rope_theta=10000.0` 两边一致（此前误以为 1e6） |
| 量化类型对账（逐张量类型直方图） | **洗清**：两文件均 Q4_K/Q6_K/F32，全在引擎支持集 |
| 对照臂：prover7b（arch=llama）同提示 | 输出 ` 6, ` ⇒ 引擎通用机制正常 ⇒ 缺陷在 qwen2 相关路径 |
| 张量结构对照 | qwen2 用到**三条 7B 从未覆盖的路径**：tied 词表 / attn q-k-v 偏置 / GQA |
| **RoPE 约定审计** | **发现真实缺陷**（见下） |

## 2. 根因：RoPE 配对约定写死为一种

权威源：llama.cpp `llama_model_rope_type()`（`src/llama-model.cpp:2584`，取自 llama-cpp-python 0.3.35 sdist 内 vendored llama.cpp；提取结果存档 `eval/rover/oracle/rope-types.json`）

```c
// use what we call a normal RoPE, operating on pairs of consecutive head values
case LLM_ARCH_LLAMA: ... return LLAMA_ROPE_TYPE_NORM;     // 既有 prover7b 走这条
// the pairs of head values are offset by n_rot/2
case LLM_ARCH_QWEN2: ... return LLAMA_ROPE_TYPE_NEOX;     // qwen2.5-math 走这条
```

ggml 内核逐行对账（`ggml-cuda/rope.cu`）：

| 约定 | 配对下标 | 角度 | 引擎原状态 |
|---|---|---|---|
| `rope_norm`（LLAMA→NORM） | `x[2j], x[2j+1]`（相邻） | `pos·base^(-2j/n_rot)` | ❌ **未实现** |
| `rope_neox`（QWEN2→NEOX） | `x[j], x[j+n_rot/2]`（半偏移） | 同上 | ✅ 唯一实现 |

⇒ **`arch=llama` 的模型（DeepSeek-Prover-V2-7B，本项目主模型）一直在用错配对**：位置信息错乱但不抛错，
输出退化为重复/乱码。**R400 那句 `gen_text= 2 2 2 2` 不是模型行为，是本缺陷的症状。**

同类缺陷的自我放大：`rope_check` 交叉验证（`RopeTable` ↔ `CpuKernels.Rope`）长期"通过"，
因为两个实现**共享同一个约定误解** ⇒ 自洽 ≠ 正确。已作为通用工程教训写入
`skills/independent-verification-before-claim`（v1.1.0，新增"约定负控"判据）。

## 3. 修复

| 文件 | 改动 |
|---|---|
| `src/agent.rover/infer/RopePairing.cs` | 新增：`RopePairing{ NormConsecutive, NeoxHalf }` + 由 `llama-arch.cpp` 机械提取的 41 个 NORM arch 名单 + `FromArch()`（未收录 ⇒ NEOX，与 llama.cpp default 分支一致） |
| `src/agent.rover/infer/RopeTable.cs` | 构造参数加 `pairing`；`Apply` 按约定选择配对下标（两处 `RopeTable` 调用点同步） |
| `src/agent.rover/infer/ModelConfig.cs` | 新增 `required RopePairing`，由 `general.architecture` 判定 |
| `src/agent.rover/runtime/CpuKernels.cs` | `Rope(...)` 加 `pairing` 形参（直接实现同步支持两种约定） |
| `src/agent.rover/cli/ForwardCli.cs` | `rope_check` 输出带 `arch/pairing`，并新增**负控行** `rope_pairing_negctl` |
| `src/agent.tests/RoverRopeTests.cs` | 新增 7 测试：两种约定的金标向量 / 跨实现一致 / **负控（两约定必须不同）** / 频率表与约定无关 / **实现↔存档逐项机检** |

## 4. 证据（同一命令、同一参数、同一机器）

```
forward <gguf> --tokens 16,11,17 --topk 8 --head-vals 0
```

| 模型 | 改前 | 改后 | 判定 |
|---|---|---|---|
| prover7b（llama，pairing=NORM） | `mean=96.45615 stdev=2.376802840591207 min=88.50625 max=114.56561 top1=11` | `mean=95.889435 **stdev=2.48841954302631** min=85.72626 max=114.44776 top1=11` | ✅ 生效 |
| qwen2.5-math-1.5B（qwen2，pairing=NEOX） | `min=-7.598128 max=11.951501 mean=-2.0197861 stdev=1.1325822820864757 sum=-306878.2203581892 top1=8` | **全部数字逐位相同** | ✅ 范围隔离 |

- 负控：`rope_pairing_negctl{active=NORM other=NEOX max_abs_diff=3.7959385 verdict=distinct}`
- 金标向量（独立算出后硬编码，`pos=3, head_dim=8, base=10000, x=[1..8]`）：
  - NEOX `[-1.695593, 0.137552, 2.788682, 3.975982, -4.808842, 6.323059, 7.086837, 8.011964]`
  - NORM `[-1.272233, -1.838865, 1.683929, 4.707907, 4.817777, 6.147278, 6.975969, 8.020964]`（`max|Δ|=9.614`）
- 测试：`RoverRopeTests` **7/7**；`agent.rover` / 测试工程 **Build 0 错误**
- 生成 A/B（同提示 `1, 2, 3, 4, 5,`，greedy）：改前 ` 6, ` / 0.0364 tok/s；改后 ` 6, ` / 0.0387 tok/s
  ⇒ 本提示输出不变（说明修复未破坏既有正确行为），速度无回归

## 5. 诚实边界

1. **prover7b 的全部历史输出（含 R400 生成链读数）在新配对下不可信，需重测**；本次仅完成"平凡续写"重测，
   解法级重测（足量 token 预算 + 数学题）未做。
2. **qwen2 乱码仍未定性**：分词与 RoPE 均已洗清 ⇒ 剩余嫌疑人为 **tied 词表**（7B 有 `output.weight`，
   qwen2.5-math-1.5B 无）、**attn q/k/v 偏置**（7B 无）、**GQA 12:2**（7B 为 32:32）。判别实验已排队：
   跑 `DeepSeek-R1-Distill-Qwen-1.5B`（qwen2 架构但 **untied**）。
3. NORM/NEOX 表来自 vendored llama.cpp（0.3.35 sdist）。**上游若变更该表，需重新提取**；
   存档与实现的机检可防实现侧漂移，但防不了"存档本身过期"——故存档内记录来源与提取方式。

## 6. 附带产出

- `scripts/gguf_probe_remote.py`：**远程 GGUF 兼容性预探**（HTTP range 只取头部 ~24 MB，
  解析 metadata + 张量清单 ⇒ 判定 arch / 是否含引擎未实现的特性 / 量化类型是否可实现）。
  实测候选：`DeepSeek-R1-Distill-Qwen-1.5B` RUNNABLE；`Llama-3.2-1B` RUNNABLE；
  `Qwen2.5-0.5B` / `SmolLM2-360M` **含 Q5_0 ⇒ BLOCKED**；`Qwen3-0.6B` **含 56 个 qk_norm ⇒ BLOCKED**。
- 待办候选：给引擎补 **Q5_0** 反量化内核（32 元素块 / 22 字节），否则 0.5B 档模型无法使用。

## 7. 下轮候选

1. R1-Distill 探针（决定性：定位 tied 词表路径是否就是 qwen2 乱码根因）。
2. prover7b 解法级重测（新配对 + 足量 token 预算）。
3. Q5_0 内核 + 0.5B 档实测（若用户要"更小"）。
4. R402 批 prefill A/B、R403 chat template 全量。
