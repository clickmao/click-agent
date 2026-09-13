# r385 — DeepSeek-Prover-V2-7B (GGUF Q4_K_M) Transformer 前向推理：真机证据

**日期**：2026-09-13  
**机器**：Linux 6.8，2 vCPU，3.6 GiB RAM（约 1.95 GiB `MemAvailable`），10 GiB swap（实际使用 0），无 GPU  
**被测模型**：`/tmp/models/prover7b-q4km.gguf`（4,223,362,304 B = 3.933 GiB，Q4_K_M）  
**C# 侧**：`dotnet 10.0.400`，`src/click-rover`（SDK 风格 csproj，未改 csproj、未加 NuGet）  
**对照侧**：`/tmp/ggufenv/bin/python`（gguf + numpy），独立实现，逐张量流式反量化

---

## 0. 结论摘要

| 项 | 结果 |
|---|---|
| Phase 1（tiny f32，C# vs numpy logits） | **max_abs_diff = 7.27e-06**（阈值 `< 1e-4`）✅ |
| Phase 1 逐层 hidden | 最差 5.72e-05 绝对（相对 1.25e-06），**逐层逐 token 全部对账** ✅ |
| Phase 1 覆盖 | GQA(4/2) 与 MHA(4/4) 两种、tied 与 untied 两种输出头、多 token 因果与 KV cache ✅ |
| Phase 2 单 token（真 7B，1 token） | top-1 = **185**（logit 64.47826），耗时 **19.36 s**，峰值 RSS **359.6 MiB** ✅ |
| Phase 2 4 token（真 7B，KV cache 复用） | top-1 = **13**，top-5 = [13,16,17,15,18] 与 numpy **完全一致** ✅ |
| Phase 2 logits 对账（4 token） | **max_abs_diff = 6.10e-05**（值域 86.3–109.9，相对 5.6e-07）✅ |
| Phase 2 logits 对账（单 token） | max_abs_diff = 2.17e-04（**绝对超 1e-4**；值域 44.7–64.5，相对 3.4e-06；top-1/top-5 仍一致）⚠️ 见 §5 |
| 峰值 RSS 对比 | C# **364.9 MiB**；numpy 参考 **2.0 GiB**（LRU 上限 320 MB 仍物化整张 ffn 张量） |

核心量：`streamed=4023.0MiB / file=4028.0MiB → ratio=0.999`（单 token），
`streamed=15107.4MiB → ratio=3.751`（4 token，权重每 token 重新流式一遍），
证明**没有任何 7B 张量被全量物化成 f32**（若物化则为 4.03 GiB × (4096/1440 等) ≫ 可用内存）。

---

## 1. 交付文件清单与关键函数

全部为**新增文件**，工作树中 `src/click-rover/` 整体未被 git 跟踪（`?? src/click-rover/`）；未执行任何 `git commit`/`push`。

| 文件 | 行数 | 职责 | 关键函数（file:line） |
|---|---|---|---|
| `src/click-rover/Infer/ModelConfig.cs` | 152 | GGUF metadata → 超参，构造期强校验（缺失/不自洽即抛错，无默认值降级） | `From` :46，`AttnScale` :39，`LayerPrefix` :43，`Validate` :99 |
| `src/click-rover/Infer/RopeTable.cs` | 73 | RoPE 预计算 cos/sin，**LLaMA NORM 配对**（i ↔ i+n_rot/2） | `RopeTable` ctor :19，`Apply` :51，`At` :70 |
| `src/click-rover/Infer/KvCache.cs` | 100 | 逐层 KV cache，布局 `[layer][kvHead][pos][dim]`，单/多 token 同路径 | `KvCache` :25，`EnsureCapacity` :44，`Append` :65，`Keys` :83，`Values` :86 |
| `src/click-rover/Infer/ForwardPass.cs` | 303 | 前向主体 + 计时/内存/RSS 读数 | `Forward` :162（Embed :177；RMSNorm+QKV :185-189；RoPE :190-191；KV append :192；GQA 注意力 :195-202；attn_out+残差 :203-204；FFN RMSNorm :209；SwiGLU :210-213；残差 :214；output_norm :234-235；lm_head/tied :238-239），`Gemv` :120，`MaybeLoadBias` :106，`ReadVm` :281，`TopK` :256，`LayerHook` :10 |
| `src/click-rover/Cli/ForwardCli.cs` | 173 | `forward` 子命令：参数解析、RoPE 双实现对拍、统计输出、dump | `Forward` :18，`RopeCrossCheck` :118，`WriteF32` :166 |
| `src/click-rover/Cli/RoverCli.cs` | — | 仅两处改动：dispatch `"forward"`、usage 一行 | — |

复用（只读，未改动）：`Gguf/GgufReader.cs`、`Gguf/GgufMappedFile.cs`、`Quant/Dequant.cs`、`Runtime/CpuKernels.cs`、`Runtime/TensorResidency.cs`。
**未修改 `src/agent/**` 任何文件**（`git status --porcelain -- src/agent` 输出为空；`git diff -- src/click-rover/click-rover.csproj` 亦为空）。

实现要点落实：
- **零硬编码**：`layers/hidden/ffn/n_head/n_head_kv/head_dim/vocab/ctx/rope_base/rope_dim/rms_eps` 全部 `Req()` 自 metadata；RoPE scaling 读 `*.rope.scaling.type`（本模型不存在 → `none`，且 `attn_scale` 由 `1/sqrt(head_dim)` 计算而非写死）。
- **tied embeddings**：`HasOutputTensor = Find("output.weight") != null`；本模型有 `output.weight`（Q6_K）→ `tied_embeddings=False`；tiny 变体验证了 tied 路径（回退 `token_embd.weight`）。
- **GQA**：`kvh = h / GqaGroup`；本模型 `n_head=32 = n_head_kv=32`（**实测非 GQA**），故 GQA 合法性由 Phase 1 的 `nh4/nhkv2` tiny 模型覆盖。
- **KV cache**：`--ctx 8` 时 `cache_bytes=7864320`（30 层 × 32 头 × 8 位 × 128 维 × 4 B × K+V），4 个 token 内 `kv_len` 依次 1→2→3→4。
- **流式**：每张权重量化字节经 `CpuKernels.GemvQuantized` 边反量化边点积；`--drop-pages` 用 `madvise(MADV_DONTNEED)` 在算完后释放文件页。

---

## 2. Phase 1：tiny 模型自证数学（同一份权重，两侧各算）

### 2.1 tiny GGUF 构造（同一份权重来源）

```
$ /tmp/ggufenv/bin/python /tmp/gen_tiny_gguf.py /tmp/tiny
tiny-gqa-untied.gguf  (331840 B)
tiny-mha-tied.gguf    (348160 B)
```

权重由固定种子 `np.random.RandomState(seed).uniform(-0.5, 0.5)` 生成（F32），
`tiny-gqa-untied`: L=2, hidden=64, ffn=128, n_head=4, n_head_kv=2, head_dim=16, vocab=64, ctx=32, untied；
`tiny-mha-tied`: n_head_kv=4, tied。

### 2.2 C# 侧原始输出

```
$ export PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet"
$ dotnet run --project src/click-rover/click-rover.csproj -c Release --no-build -- \
    forward /tmp/tiny/tiny-gqa-untied.gguf --tokens 1,2,3 --dump /tmp/dump_cs
forward{file=tiny-gqa-untied.gguf file_bytes=331840 tokens=[1,2,3] n_tokens=3 data_offset=2880}
cfg{arch=llama name=tiny-untied-L2-h64-nh4-nhkv2 layers=2 hidden=64 ffn=128 n_head=4 n_head_kv=2 gqa_group=2 head_dim=16 value_dim=16}
cfg{vocab=64 ctx=32 rope_dim=16 rope_base=10000 rope_scaling=none rope_factor=0 rms_eps=1E-05 attn_scale=0.25 tied_embeddings=False}
open{meta_parse_ms=4 header_open_ms=7.6 header_bytes_read=2880 ws_before=30056448 ws_after=33062912}
rope_check{impl_a=RopeTable impl_b=CpuKernels.Rope n_heads=4 head_dim=16 rope_dim=16 pos=7 max_abs_diff=2.9802322E-07 verdict=match}
logits{count=64 min=-4.360713 max=4.420093 mean=0.0056183552 stdev=2.0122969614141515 sum=0.35957473516464233}
topk{rank=1 id=46 logit=4.420093}
topk{rank=2 id=24 logit=3.6906633}
topk{rank=3 id=4 logit=3.5593152}
topk{rank=4 id=32 logit=3.2958674}
topk{rank=5 id=41 logit=3.007175}
logits_head{[0]=-3.1073766 [1]=1.406104 [2]=1.7209799 [3]=1.8573395 [4]=3.5593152 [5]=-1.1685549 [6]=2.7929564 [7]=1.2823524}
last_hidden{idx0..3=[-3.1073766,1.406104,1.7209799,1.8573395]}
timing{embed_ms=1.2 attn_ms=21.0 ffn_ms=1.5 out_norm_ms=0.0 lm_head_ms=0.1 total_ms=26.3 per_token_ms=8.8 layers=2 tokens=3}
layer_timing{min_ms=0.5 max_ms=21.9 mean_ms=11.2 is_per_layer=True}
mem{peak_working_set=36052992 peak_vmrss=36069376 vmhwm=36323328 vmhwm_mib=34.6 kv_cache_bytes=2048 gc_heap=274360 drop_pages=False}
residency{loaded=1.2KiB reclaimed=0.0KiB streamed=928.0KiB}
residency{loads=5 evicts=0 reclaims=0 hits=8 misses=5 hit_rate=61.54 %}
residency{peak_resident=1.2KiB budget=96.0MiB}
stream{tensor_window_bytes_scanned=950272 file_bytes=331840 ratio=2.864 touched_windows=51}
dump{dir=/tmp/dump_cs logits=logits.bin per_layer_hidden=hidden_t{ti}_blk{l}.bin tokens=3 dims=dims.txt}
done{command=forward tokens=3 vocab=64 layers=2}
```

`rope_check` 是**实现内部的双实现对拍**：新增的 `RopeTable.Apply` 与仓库既有 `CpuKernels.Rope` 在 pos=7、4 头 × 16 维上 max_abs_diff = 2.98e-07。

### 2.3 numpy 独立参考对账（读 C# dump 的逐层 hidden）

```
$ /tmp/ggufenv/bin/python /tmp/ref_forward.py /tmp/tiny/tiny-gqa-untied.gguf \
      --tokens 1,2,3 --dump /tmp/dump_cs --json /tmp/ref_tiny.json
ref_cfg{arch=llama name=tiny-untied-L2-h64-nh4-nhkv2 layers=2 hidden=64 ffn=128 n_head=4 n_head_kv=2 head_dim=16 vocab=64 rope_base=10000.0 rope_dim=16 rope_scaling=none eps=9.999999747378752e-06 }
  [ref] token_index=0 token=1 pos=0 layer_max_abs_diff=['2.1e-05', '5.72e-05'] cum_deq_s=0.0
  [ref] token_index=1 token=2 pos=1 layer_max_abs_diff=['1.72e-05', '4.96e-05'] cum_deq_s=0.0
  [ref] token_index=2 token=3 pos=2 layer_max_abs_diff=['2e-05', '5.34e-05'] cum_deq_s=0.0
ref_logits{count=64 min=-4.36071348 max=4.42009306 mean=0.00561833382 sum=0.359573364 stdev=2.01229692}
ref_topk{rank=1 id=46 logit=4.42009306}
ref_topk{rank=2 id=24 logit=3.69066119}
ref_topk{rank=3 id=4 logit=3.55931544}
ref_topk{rank=4 id=32 logit=3.2958684}
ref_topk{rank=5 id=41 logit=3.00717425}
ref_head{[0]=-3.10737729 [1]=1.40610313 [2]=1.72098136 [3]=1.85734439 [4]=3.55931544 [5]=-1.16855919 [6]=2.79295444 [7]=1.28235435}
ref_timing{total_s=0.01 dequant_s=0.00 dequant_calls=18 peak_cache_mb=336}
compare_logits{n=64 max_abs_diff=7.27176666e-06 mean_abs_diff=1.94925815e-06 argmax_id=27 cs=-1.84605896 ref=-1.84605169 top1_match=True}
compare_hidden{token_index=0 layers=2 max_abs_diff=5.7220459e-05 first_layer_gt_1e-4=-1}
compare_hidden{token_index=1 layers=2 max_abs_diff=4.95910645e-05 first_layer_gt_1e-4=-1}
compare_hidden{token_index=2 layers=2 max_abs_diff=5.34057617e-05 first_layer_gt_1e-4=-1}
compare_hidden_worst{token_index=0 layer=1 max_abs_diff=5.7220459e-05}
ref_done
```

**判据**：`compare_logits.max_abs_diff = 7.27e-06 < 1e-4` ✅（两侧 top-5 id 完全相同：46/24/4/32/41）。
逐层 hidden 最差 5.72e-05 绝对；该层 `max|hidden| = 45.67`，即**相对 1.25e-06** —— 纯 f32 累加次序差异（C# 用 `TensorPrimitives.Dot` SIMD 树形归约，numpy 用 BLAS），不是实现错位。

### 2.4 第二个 tiny：MHA + tied embeddings（4 token）

```
$ dotnet run ... -- forward /tmp/tiny/tiny-mha-tied.gguf --tokens 5,0,63,7 --dump /tmp/dump_cs2
cfg{arch=llama name=tiny-tied-L2-h64-nh4-nhkv4 layers=2 hidden=64 ffn=128 n_head=4 n_head_kv=4 gqa_group=1 head_dim=16 value_dim=16}
cfg{vocab=64 ctx=32 rope_dim=16 rope_base=10000 rope_scaling=none rope_factor=0 rms_eps=1E-05 attn_scale=0.25 tied_embeddings=True}
rope_check{impl_a=RopeTable impl_b=CpuKernels.Rope n_heads=4 head_dim=16 rope_dim=16 pos=7 max_abs_diff=2.9802322E-07 verdict=match}
logits{count=64 min=-5.0320024 max=4.6808257 mean=-0.19655208 stdev=2.0313600192426775 sum=-12.579333767294884}
topk{rank=1 id=23 logit=4.6808257}
topk{rank=2 id=34 logit=3.9929779}
topk{rank=3 id=0 logit=3.2153718}
topk{rank=4 id=46 logit=2.5913558}
topk{rank=5 id=36 logit=2.4740345}
mem{peak_working_set=36343808 peak_vmrss=36360192 vmhwm=36614144 vmhwm_mib=34.9 kv_cache_bytes=4096 gc_heap=310728 drop_pages=False}

$ /tmp/ggufenv/bin/python /tmp/ref_forward.py /tmp/tiny/tiny-mha-tied.gguf --tokens 5,0,63,7 --dump /tmp/dump_cs2
ref_topk{rank=1 id=23 logit=4.68082428}
ref_topk{rank=2 id=34 logit=3.99297857}
ref_topk{rank=3 id=0 logit=3.21537232}
ref_topk{rank=4 id=46 logit=2.59135604}
ref_topk{rank=5 id=36 logit=2.47403693}
compare_logits{n=64 max_abs_diff=7.62939453e-06 mean_abs_diff=1.96159817e-06 argmax_id=17 cs=-2.98780012 ref=-2.98779249 top1_match=True}
compare_hidden{token_index=0 layers=2 max_abs_diff=2.67028809e-05 first_layer_gt_1e-4=-1}
compare_hidden{token_index=1 layers=2 max_abs_diff=4.57763672e-05 first_layer_gt_1e-4=-1}
compare_hidden{token_index=2 layers=2 max_abs_diff=4.95910645e-05 first_layer_gt_1e-4=-1}
compare_hidden{token_index=3 layers=2 max_abs_diff=5.91278076e-05 first_layer_gt_1e-4=-1}
compare_hidden_worst{token_index=3 layer=1 max_abs_diff=5.91278076e-05}
ref_done
```

`max_abs_diff = 7.63e-06 < 1e-4` ✅，top-5 完全一致，**tied embeddings 路径被真实执行**（`tied_embeddings=True`）。

> 若 RoPE/GQA/SwiGLU/注意力掩码/转置任一实现错，两侧 logits 会是 O(1)～O(10) 量级偏离（随机权重下无任何"巧合对齐"的可能）；7e-06 只可能来自浮点归约次序。

---

## 3. Phase 2：真实 7B 单 token 前向

### 3.1 命令与原始输出

```
$ export PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet"
$ cd /home/agentuser/AgentFramework
$ time dotnet run --project src/click-rover/click-rover.csproj -c Release --no-build -- \
    forward /tmp/models/prover7b-q4km.gguf --tokens 100000 --ctx 4 \
    --drop-pages --budget-mb 96 --dump /tmp/dump_7b_1
forward{file=prover7b-q4km.gguf file_bytes=4223362304 tokens=[100000] n_tokens=1 data_offset=3990784}
cfg{arch=llama name=Deepseek-Prover-V2-7B layers=30 hidden=4096 ffn=11008 n_head=32 n_head_kv=32 gqa_group=1 head_dim=128 value_dim=128}
cfg{vocab=102400 ctx=32768 rope_dim=128 rope_base=10000 rope_scaling=none rope_factor=0 rms_eps=1E-06 attn_scale=0.088388346 tied_embeddings=False}
open{meta_parse_ms=33 header_open_ms=35.9 header_bytes_read=3990784 ws_before=30199808 ws_after=51425280}
rope_check{impl_a=RopeTable impl_b=CpuKernels.Rope n_heads=32 head_dim=128 rope_dim=128 pos=7 max_abs_diff=7.1525574E-07 verdict=match}
logits{count=102400 min=44.72445 max=64.47826 mean=52.261738 stdev=2.016153540079068 sum=5351601.956748962}
topk{rank=1 id=185 logit=64.47826}
topk{rank=2 id=58 logit=64.338005}
topk{rank=3 id=6659 logit=63.716404}
topk{rank=4 id=12 logit=63.1097}
topk{rank=5 id=1901 logit=62.79767}
logits_head{[0]=58.943367 [1]=58.83851 [2]=62.46416 [3]=58.86468 [4]=59.434605 [5]=54.92581 [6]=58.089848 [7]=60.94924}
last_hidden{idx0..3=[58.943367,58.83851,62.46416,58.86468]}
timing{embed_ms=2.5 attn_ms=5971.0 ffn_ms=11702.1 out_norm_ms=1.4 lm_head_ms=1623.1 total_ms=19355.1 per_token_ms=19355.1 layers=30 tokens=1}
layer_timing{min_ms=426.5 max_ms=950.3 mean_ms=589.1 is_per_layer=True}
mem{peak_working_set=35536896 peak_vmrss=36679680 vmhwm=377090048 vmhwm_mib=359.6 kv_cache_bytes=3932160 gc_heap=14296808 drop_pages=True}
residency{loaded=976.0KiB reclaimed=0.0KiB streamed=4023.0MiB}
residency{loads=61 evicts=0 reclaims=0 hits=0 misses=61 hit_rate=0.00 %}
residency{peak_resident=976.0KiB budget=96.0MiB}
stream{tensor_window_bytes_scanned=4218372096 file_bytes=4223362304 ratio=0.999 touched_windows=273}
dump{dir=/tmp/dump_7b_1 logits=logits.bin per_layer_hidden=hidden_t{ti}_blk{l}.bin tokens=1 dims=dims.txt}
done{command=forward tokens=1 vocab=102400 layers=30}

real    0m20.760s
user    0m12.624s
sys     0m1.661s
```

**读数**：
- top-1 = **185**，logit 64.47826；top-5 = 185 / 58 / 6659 / 12 / 1901。token 185 解码为 `'Ċ'`（GPT-2 byte-level 词表里的换行符）——对纯 BOS 输入预测换行，符合该类模型行为。
- 耗时 **19.36 s**（wall 20.76 s）：attn 5.97 s + ffn 11.70 s + lm_head 1.62 s；30 层平均 589 ms/层。
- **峰值 RSS = VmHWM 359.6 MiB**（376,090,368 B）。`peak_working_set` 只有 35.5 MB，因为它是在每个 token 结束后采样，而 `--drop-pages` 已把文件页 `MADV_DONTNEED` 掉了；VmHWM 才是真实的进程峰值。
- `streamed = 4023.0 MiB`，`ratio = 0.999` → 单 token 把整个权重文件读了一遍；`residency.loaded = 976 KiB`（61 张 norm 张量：30×2 + 1）→ **除 norm 外没有任何权重常驻内存**。

### 3.2 numpy 独立流式参考对账（同一 token）

```
$ /tmp/ggufenv/bin/python /tmp/ref_forward.py /tmp/models/prover7b-q4km.gguf \
      --tokens 100000 --dump /tmp/dump_7b_1 --budget-mb 320 --json /tmp/ref_7b_1.json
ref_cfg{arch=llama name=Deepseek-Prover-V2-7B layers=30 hidden=4096 ffn=11008 n_head=32 n_head_kv=32 head_dim=128 vocab=102400 rope_base=10000.0 rope_dim=128 rope_scaling=none eps=9.999999974752427e-07 }
  [ref] token_index=0 token=100000 pos=0 layer_max_abs_diff=['3.81e-06', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.000732', '0.000488'] cum_deq_s=41.9
ref_logits{count=102400 min=44.724617 max=64.4784546 mean=52.2619133 sum=5351620 stdev=2.01615548}
ref_topk{rank=1 id=185 logit=64.4784546}
ref_topk{rank=2 id=58 logit=64.3381958}
ref_topk{rank=3 id=6659 logit=63.7165794}
ref_topk{rank=4 id=12 logit=63.10989}
ref_topk{rank=5 id=1901 logit=62.7978516}
ref_head{[0]=58.9435654 [1]=58.8386917 [2]=62.4643326 [3]=58.8648834 [4]=59.4347839 [5]=54.9259796 [6]=58.090023 [7]=60.9494324}
ref_timing{total_s=64.19 dequant_s=44.61 dequant_calls=224 peak_cache_mb=336}
compare_logits{n=102400 max_abs_diff=0.000217437744 mean_abs_diff=0.000171929001 argmax_id=3362 cs=59.279747 ref=59.2799644 top1_match=True}
compare_hidden{token_index=0 layers=30 max_abs_diff=0.00146484375 first_layer_gt_1e-4=1}
compare_hidden_worst{token_index=0 layer=1 max_abs_diff=0.00146484375}
ref_done
```

- **top-1 = 185，两侧一致**；top-5 id 全同（185/58/6659/12/1901）。
- logits `max_abs_diff = 2.17437744e-04`，值域 44.72–64.48 → **相对 3.4e-06**。
- 逐层 hidden：layer0 = 3.81e-06；layer1–28 = 1.4648e-03 **恒定不变**；layer29 = 4.88e-04。该 token 的 `max|hidden| = 4477.87`（BOS embedding 离群维）→ 相对 **3.3e-07**。误差不随层数增长，说明不存在系统性偏离。

---

## 4. Phase 2：真实 7B 多 token 前向（KV cache / 因果掩码）

### 4.1 命令与原始输出

```
$ time dotnet run --project src/click-rover/click-rover.csproj -c Release --no-build -- \
    forward /tmp/models/prover7b-q4km.gguf --tokens 100000,90379,4160,16 --ctx 8 \
    --drop-pages --budget-mb 96 --steps --dump /tmp/dump_7b_4
forward{file=prover7b-q4km.gguf file_bytes=4223362304 tokens=[100000,90379,4160,16] n_tokens=4 data_offset=3990784}
cfg{arch=llama name=Deepseek-Prover-V2-7B layers=30 hidden=4096 ffn=11008 n_head=32 n_head_kv=32 gqa_group=1 head_dim=128 value_dim=128}
cfg{vocab=102400 ctx=32768 rope_dim=128 rope_base=10000 rope_scaling=none rope_factor=0 rms_eps=1E-06 attn_scale=0.088388346 tied_embeddings=False}
open{meta_parse_ms=51 header_open_ms=54.7 header_bytes_read=3990784 ws_before=30105600 ws_after=51265536}
rope_check{impl_a=RopeTable impl_b=CpuKernels.Rope n_heads=32 head_dim=128 rope_dim=128 pos=7 max_abs_diff=7.1525574E-07 verdict=match}
step{token_index=0 token=100000 pos=0 kv_len=1 cache_bytes=7864320 layer_ms_sum=16443.9}
step{token_index=1 token=90379 pos=1 kv_len=2 cache_bytes=7864320 layer_ms_sum=42973.0}
step{token_index=2 token=4160 pos=2 kv_len=3 cache_bytes=7864320 layer_ms_sum=67777.6}
step{token_index=3 token=16 pos=3 kv_len=4 cache_bytes=7864320 layer_ms_sum=86876.8}
logits{count=102400 min=86.30756 max=109.9002 mean=94.489944 stdev=2.3105131792088134 sum=9675769.928016663}
topk{rank=1 id=13 logit=109.9002}
topk{rank=2 id=16 logit=109.5841}
topk{rank=3 id=17 logit=109.33308}
topk{rank=4 id=15 logit=109.16453}
topk{rank=5 id=18 logit=108.44236}
logits_head{[0]=104.56003 [1]=105.568634 [2]=103.510574 [3]=105.47527 [4]=103.3102 [5]=102.23653 [6]=105.44947 [7]=107.41246}
last_hidden{idx0..3=[104.56003,105.568634,103.510574,105.47527]}
timing{embed_ms=7.7 attn_ms=29213.8 ffn_ms=57662.9 out_norm_ms=3.3 lm_head_ms=1519.4 total_ms=88752.7 per_token_ms=22188.2 layers=30 tokens=4}
layer_timing{min_ms=1872.3 max_ms=4399.7 mean_ms=2895.9 is_per_layer=True}
mem{peak_working_set=38703104 peak_vmrss=38801408 vmhwm=382574592 vmhwm_mib=364.9 kv_cache_bytes=7864320 gc_heap=22824152 drop_pages=True}
residency{loaded=976.0KiB reclaimed=0.0KiB streamed=15107.4MiB}
residency{loads=61 evicts=0 reclaims=0 hits=180 misses=61 hit_rate=74.69 %}
residency{peak_resident=976.0KiB budget=96.0MiB}
stream{tensor_window_bytes_scanned=15841296384 file_bytes=4223362304 ratio=3.751 touched_windows=906}
dump{dir=/tmp/dump_7b_4 logits=logits.bin per_layer_hidden=hidden_t{ti}_blk{l}.bin tokens=4 dims=dims.txt}
done{command=forward tokens=4 vocab=102400 layers=30}

real    1m30.838s
user    0m46.293s
sys     0m7.341s
```

- top-1 = **13**（`'.'`），top-5 = 13/16/17/15/18 → `'.','1','2','0','3'`（有趣但无关紧要：数字分布）。
- KV cache 行为正确：`kv_len` 1→2→3→4，`cache_bytes` 恒为 7,864,320 B（8 位 × 30 层 × 32 头 × 128 维 × 4 B × K+V）。
- 耗时 88.75 s（wall 90.84 s），22.2 s/token；第 4 个 token 的注意力只遍历 4 个位置，但权重必须重新流式一遍（15.1 GiB 总读 = 3.75 × 文件），仍是内存受限而非计算受限。
- **峰值 RSS = VmHWM 364.9 MiB**。

### 4.2 numpy 独立流式参考（4 token，全程 3m46s，`/usr/bin/time -v` 原始输出）

```
ref_cfg{arch=llama name=Deepseek-Prover-V2-7B layers=30 hidden=4096 ffn=11008 n_head=32 n_head_kv=32 head_dim=128 vocab=102400 rope_base=10000.0 rope_dim=128 rope_scaling=none eps=9.999999974752427e-07 }
  [ref] token_index=0 token=100000 pos=0 layer_max_abs_diff=['3.81e-06', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.00146', '0.000732', '0.000488'] cum_deq_s=59.9
  [ref] token_index=1 token=90379 pos=1 layer_max_abs_diff=['3.81e-06', '1.43e-06', '1.43e-06', '1.91e-06', '2.86e-06', '3.81e-06', '2.86e-06', '3.81e-06', '5.72e-06', '5.25e-06', '6.2e-06', '6.68e-06', '7.63e-06', '1.14e-05', '8.11e-06', '9.54e-06', '1.05e-05', '1.05e-05', '1.53e-05', '1.53e-05', '2.29e-05', '3.81e-05', '4.58e-05', '4.58e-05', '3.05e-05', '1.72e-05', '3.05e-05', '3.05e-05', '4.67e-05', '0.000156'] cum_deq_s=104.4
  [ref] token_index=2 token=4160 pos=2 layer_max_abs_diff=['3.81e-06', '9.54e-07', '9.54e-07', '1.07e-06', '1.19e-06', '1.61e-06', '1.67e-06', '1.82e-06', '3.81e-06', '2.38e-06', '2.62e-06', '2.86e-06', '1.14e-05', '7.63e-06', '4.77e-06', '1.14e-05', '1.14e-05', '1.14e-05', '1.53e-05', '9.06e-06', '9.78e-06', '1.14e-05', '1.26e-05', '1.29e-05', '3.05e-05', '3.05e-05', '1.56e-05', '3.05e-05', '3.05e-05', '0.000153'] cum_deq_s=154.7
  [ref] token_index=3 token=16 pos=3 layer_max_abs_diff=['3.81e-06', '1.91e-06', '2.86e-06', '1.19e-06', '1.91e-06', '1.43e-06', '1.91e-06', '3.81e-06', '3.81e-06', '5.72e-06', '3.81e-06', '3.81e-06', '1.34e-05', '9.54e-06', '3.81e-06', '7.63e-06', '7.63e-06', '5.72e-06', '5.72e-06', '7.63e-06', '7.63e-06', '7.63e-06', '2.29e-05', '3.05e-05', '3.05e-05', '3.05e-05', '1.53e-05', '1.53e-05', '1.14e-05', '0.000114'] cum_deq_s=195.2
ref_logits{count=102400 min=86.3075562 max=109.900192 mean=94.4899445 sum=9675770 stdev=2.31051302}
ref_topk{rank=1 id=13 logit=109.900192}
ref_topk{rank=2 id=16 logit=109.584053}
ref_topk{rank=3 id=17 logit=109.333076}
ref_topk{rank=4 id=15 logit=109.164528}
ref_topk{rank=5 id=18 logit=108.442352}
ref_head{[0]=104.56002 [1]=105.568619 [2]=103.510551 [3]=105.475281 [4]=103.310188 [5]=102.236526 [6]=105.449448 [7]=107.41246}
ref_timing{total_s=219.92 dequant_s=198.18 dequant_calls=857 peak_cache_mb=336}
compare_logits{n=102400 max_abs_diff=6.10351562e-05 mean_abs_diff=1.06915086e-05 argmax_id=32104 cs=99.5164337 ref=99.5163727 top1_match=True}
compare_hidden{token_index=0 layers=30 max_abs_diff=0.00146484375 first_layer_gt_1e-4=1}
compare_hidden{token_index=1 layers=30 max_abs_diff=0.000156402588 first_layer_gt_1e-4=29}
compare_hidden{token_index=2 layers=30 max_abs_diff=0.000152587891 first_layer_gt_1e-4=29}
compare_hidden{token_index=3 layers=30 max_abs_diff=0.000114440918 first_layer_gt_1e-4=29}
compare_hidden_worst{token_index=0 layer=1 max_abs_diff=0.00146484375}
ref_done
        Command being timed: "/tmp/ggufenv/bin/python /tmp/ref_forward.py /tmp/models/prover7b-q4km.gguf --tokens 100000,90379,4160,16 --dump /tmp/dump_7b_4 --budget-mb 320 --json /tmp/ref_7b_4.json"
        Elapsed (wall clock) time (h:mm:ss or m:ss): 3:45.68
        Maximum resident set size (kbytes): 2076236
        Major (requiring I/O) page faults: 75698
        Minor (reclaiming a frame) page faults: 25272439
        Swaps: 0
        File system inputs: 28607576
        Exit status: 0
```

**对账结论**：
- **两侧 top-1 = 13，top-5 = [13, 16, 17, 15, 18] 完全一致** ✅
- logits `max_abs_diff = 6.10e-05`，`mean = 1.07e-05`，`top1_match=True`；值域 86.3–109.9 → 相对 **5.6e-07**
- 逐层逐 token hidden 全部对账（4 token × 30 层 = 120 个张量），误差随深度**平滑累积、非跳变**（token1: 3.8e-06 → 1.6e-04），这是 f32 归约次序差异的典型特征
- 相对误差换算（脚本 `/tmp/rel.py`）：

```
-- 相对误差 (token_index=1, 4tok run): max|diff| / max|C# hidden| --
   layer= 0 max|hidden|=    14.462 abs_diff=3.81e-06 rel=2.63e-07
   layer= 1 max|hidden|=    8.0037 abs_diff=1.43e-06 rel=1.79e-07
   layer=10 max|hidden|=    25.348 abs_diff=6.2e-06 rel=2.45e-07
   layer=20 max|hidden|=    84.798 abs_diff=2.29e-05 rel=2.7e-07
   layer=29 max|hidden|=   111.52 abs_diff=0.000156 rel=1.4e-06
   worst rel over 30 layers = 1.4e-06

-- 4tok 判定裕度: top1=109.9 top2=109.584 gap=0.316101 logits 对账 max_abs_diff=6.1e-05 → gap/err = 5.18e+03x
-- single 判定裕度: top1=64.4783 top2=64.338 gap=0.140251 logits 对账 max_abs_diff=2.17e-04 → gap/err = 645x
```

- **top-1 判定稳健**：两次运行里 top-1 与 top-2 的 logit 间距分别是数值误差的 **5180 倍**和 **645 倍**，argmax 不处于"误差可翻转"的临界状态。

### 4.3 内存可行性对照（同一台 2 vCPU / 3.6 GiB 机器）

| 实现 | 峰值 RSS | 说明 |
|---|---|---|
| C# click-rover（逐张量流式 + `MADV_DONTNEED`） | **364.9 MiB** | 常驻仅 976 KiB norm；权重边反量化边用 |
| C# click-rover（单 token） | **359.6 MiB** | 同上 |
| numpy 参考（LRU 320 MB，仍物化整张 ffn 张量） | **2,076,236 KB ≈ 1.98 GiB** | 逼近 2.2 GiB 可用上限，`Swaps: 0` 侥幸通过 |

即：**C# 路径的流式设计是本机真正可行的方案**；numpy 参考若不加 LRU 会 OOM。

---

## 5. 诚实边界 / 未完成项

1. **单 token logits 的绝对差 2.17e-04 超过了 1e-4 这个数字**。需要说明：1e-4 是任务为 Phase 1（f32 全精度同权重对拍）设定的判据，Phase 1 实际 7.27e-06 通过。Phase 2 的 2.17e-04 出现在 logits 值域 44.7–64.5 上，即**相对 3.4e-06**；同一对拍在 4-token 运行里是 6.10e-05（< 1e-4）。4.03 GiB 权重里每个 block 的 f32 累加次序不同（C# SIMD 归约 vs numpy BLAS）足以产生这个量级。若要求 Phase 2 也 < 1e-4 绝对，需要逐元素对齐归约次序或上 float64——本轮未做。
2. **本模型实测不是 GQA**（`n_head_kv = n_head = 32`）。GQA 代码路径（`kvh = h / GqaGroup`）由 Phase 1 的 `nh4/nhkv2` tiny 模型验证，而非由 7B 真机验证。
3. **本模型无 RoPE scaling**（metadata 无 `rope.scaling.type`，→ `none`；`rope_base = 10000.0` 读自 metadata）。因此 `RopeTable` 里的 yarn/longrope 分支**未被真机执行**，只在构造期读到 `none` 时跳过。若后续换用带 scaling 的模型，该分支需要另外构造 tiny 用例验证。
4. **未实现采样/生成循环**（temperature、top-p、EOS 停止、多轮 decode）。本任务是"前向推理 + 数值验证"，`forward` 只做一次批量前向并返回最后位置的 logits；多 token 的 KV cache 已按"逐 token 走同一路径"实现，但没有按 token 增量喂入的公开 API。
5. **未做性能优化**：22.2 s/token（4 token）/ 19.4 s（单 token）主要花在每 token 重新反量化整个权重文件（15.1 GiB 总读）。可用手段（跨 token 保留热点层、多线程 GEMV、页缓存策略）未做——`--drop-pages` 是当前内存安全优先的选择。
6. **`peak_working_set` / `peak_vmrss` 两个采样字段偏低**（35–39 MB），因为它们只在每个 token 结束时采样一次，而 `--drop-pages` 已释放文件页。**真实峰值以 `vmhwm_mib` 为准**。
7. numpy 参考的 `dequant_s = 198 s` 占了其 220 s 总耗时的 90%，是 gguf-py `dequantize` 的吞吐（约 411 MB/s）限制；C# 侧同等工作在 ~19 s 内完成（含计算），这也是 C# 侧不用额外优化的原因之一。

---

## 6. 复现命令（全部可重跑）

```bash
export PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet"
cd /home/agentuser/AgentFramework
dotnet build src/click-rover/click-rover.csproj -c Release -v q --nologo     # 0 warning / 0 error

# Phase 1
/tmp/ggufenv/bin/python /tmp/gen_tiny_gguf.py /tmp/tiny
dotnet run --project src/click-rover/click-rover.csproj -c Release --no-build -- \
  forward /tmp/tiny/tiny-gqa-untied.gguf --tokens 1,2,3 --dump /tmp/dump_cs
/tmp/ggufenv/bin/python /tmp/ref_forward.py /tmp/tiny/tiny-gqa-untied.gguf \
  --tokens 1,2,3 --dump /tmp/dump_cs --json /tmp/ref_tiny.json
# (tiny-mha-tied.gguf 同理, 覆盖 tied embeddings + MHA)

# Phase 2
dotnet run --project src/click-rover/click-rover.csproj -c Release --no-build -- \
  forward /tmp/models/prover7b-q4km.gguf --tokens 100000 --ctx 4 --drop-pages \
  --budget-mb 96 --dump /tmp/dump_7b_1
dotnet run --project src/click-rover/click-rover.csproj -c Release --no-build -- \
  forward /tmp/models/prover7b-q4km.gguf --tokens 100000,90379,4160,16 --ctx 8 \
  --drop-pages --budget-mb 96 --steps --dump /tmp/dump_7b_4
/tmp/ggufenv/bin/python /tmp/ref_forward.py /tmp/models/prover7b-q4km.gguf \
  --tokens 100000,90379,4160,16 --dump /tmp/dump_7b_4 --budget-mb 320 --json /tmp/ref_7b_4.json
/tmp/ggufenv/bin/python /tmp/rel.py
```

辅助脚本：`/tmp/gen_tiny_gguf.py`（tiny GGUF 构造）、`/tmp/ref_forward.py`（numpy 独立参考）、`/tmp/analyze.py`、`/tmp/rel.py`、`/tmp/find_tokens.py`。

**约束遵守**：未 `git commit` / `push`；未改动 `src/agent/**`；未改 `click-rover.csproj`；未加 NuGet 包；未使用反射；未用 `Console.WriteLine`（输出统一走 `RoverCli` 的 `TextWriter o`）。本文所有数字均来自上述真实运行，粘贴自原始输出。
