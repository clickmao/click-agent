# R409 证据 —— 本地 prompt 模板闸门 / BOS 归属裁决

状态: 已实施（R409，2026-09-14）
计划文档: `docs/plans/v0.31.0-r409-local-prompt-template-gate.md`

## 原始文件清单（本目录，可复核）

| 文件 | 内容 |
|---|---|
| `apply_template_probe.py` / `.out.txt` | `/apply-template` 可用性与渲染产物（67 B，无 BOS） |
| `bos_ownership_probe.py` / `.out.txt` | BOS 归属裁决表（5 种输入 × add_special 两档） |
| `template_source_reconcile.py` / `.out.txt` | GGUF 内嵌模板 vs 归档 `r1_chat_template.jinja` 逐字节对账 |
| `ab_template.py` / `ab_template_long.py` / `template-ab.md` | 模板 vs 裸文本 A/B（R409 前置探针） |
| `prompt.txt` | 96 B 字面权串（sha `d1e94bf7…`），作负控与 id 对账锚 |
| `verify-template.json` | `--verify-template` 机器验证输出（Verdict=gated_single_bos） |
| `e2e-literal-path.json` / `e2e-chat-path.json` | 产品通路对照（18 vs 17 tokens_evaluated，生成 id 逐位相同） |

## A. 关键读数（机器产出，未转述）

```
/props: chat_template=2081 字符(2237 B)  bos_token=<｜begin▁of▁sentence｜>  eos_token=<｜end▁of▁sentence｜>  bos_id=151646

96 B 字面权串 (sha d1e94bf720adbab7b376d0014bfeb01a8c03864cae7c4a1110ab9be5750fa947)
  add_special=true  : 18 token, BOS×2, 首4 id [151646, 151644, 3838, 374]
  add_special=false : 17 token, BOS×1, 首4 id [151646, 151644, 3838, 374]

67 B 渲染串 (sha 25e467ee2ae3bb0f68707bf6d51246dc4f9ce0476ecb8154cf3098f781174567)
  add_special=true  : 17 token, BOS×1, 首4 id [151646, 151644, 3838, 374]
  add_special=false : 16 token, BOS×0, 首4 id [         151644, 3838, 374]

38 B 裸文本 add_special=true : 15 token, BOS×1

⇒ tokenize(96B, add_special=false) ≡ tokenize(67B, add_special=true)   [等价判定由 --verify-template 的 IdsEquivalent=true 给出]

模板来源对账: served == archived == gguf_inline  3/3 形状 True（U 67B/17tok, S+U 95B/23tok, U/A/U 112B/26tok; diff 0 B）
多轮渲染: 118 B，含 EOS 文本 1 次（轮分隔符），不以 EOS 结尾 ⇒ 合法，闸门必须放行
```

## B. `--verify-template` 机器验证（exit 0）

```json
{"Mode":"verify_template","BosId":151646,"ChatTemplateLength":2081,
 "RenderedBytes":67,"RenderedSha256":"25e467ee…","RenderedTokens":17,"RenderedBosCount":1,
 "LiteralBytes":96,"LiteralSha256":"d1e94bf7…","LiteralTokens":18,"LiteralBosCount":2,
 "LiteralTokensNoSpecial":17,"IdsEquivalent":true,
 "Verdict":"gated_single_bos","TemplateRenders":1}
```

判据（预注册）：渲染通路 BOS==1 且 负控 BOS>1 且 两侧 token 流等价 ⇒ 通过。三项全部满足。

## C. 测试

- 负控单测：`LlamaCppPromptGateTests` **9/9 通过（66 ms）**——含「96 B 字面串必须判红」「来源=Literal 必须判红」
  「以 EOS 结尾必须判红」「空产物必须判红」「多轮含 EOS 必须判绿」「无元数据不得误拦」「sha 锚点钉死」。
- 全量回归：**1072 通过 / 0 失败 / 0 跳过（31 s）**（R408 退役后基线 1063 + 本轮新增 9）。
- 构建：`agent.host` Release 绿，`agent.llamacpp`/`agent.host` 零新警告。
- AOT：见 §E（政策 `release_tag_only`，非发布轮仅作参考证据）。

## D. 诚实边界

1. **A/B 是 n=1 题 × 1 采样**（模板 vs 裸文本），只作方向性证据，不是能力分数。
2. **「llama-cli 侧也双 BOS」未单独实测**：本 build 的 llama-cli 性能行不含 prompt token 数。已实测的是
   llama.cpp **tokenizer 默认加 BOS**（`/tokenize`，`add_special=true`）与产品通路 `tokens_evaluated=18`；
   该默认由同一 GGUF/同一 tokenizer 实现决定，故推断基线侧同形——标为**推断**，非测量。
3. **生成结果的鲁棒性只测了 24 token/1 题**：不能外推为「双 BOS 无影响」。其**确定性代价**是 +1 prompt token
   与通路间前缀不可复用（K2/K2b），后者与题面无关。
4. **闸门只覆盖本地通路**；远端 provider 的模板化仍无闸门（见计划文档 §6/§7）。
5. R409 三个探针脚本的**内建裁决行问错了对象**（比较的是 `96B/add_special=true`），故打印 False；
   正确的等价对（`96B/false` vs `67B/true`）在表中逐位相同，且由 `--verify-template` 的 `IdsEquivalent=true`
   独立确认。**探针缺陷已记录，结论不受影响。**

## E. AOT（参考证据，非本轮等级判定依据）

按 `docs/verification-registry.json` 的 `aot.publish.zero_il` 规范命令执行
（`dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_release`，**不带** `-p:PublishAot`），
原始日志 `eval/rover/r409/aot-reference.log`，脚本 `eval/rover/r409/aot_reference.sh`。

实测：**`AOT_EXIT=0`、IL 警告 0**、产物 `/tmp/pub_release/agenthost` **14,950,608 B**（2026-09-14 08:35）；
另有 2 条**非 IL** 警告（`NU1510`：`agent.rag.csproj` 显式引用 `System.Text.Json`，既有噪声）。
政策 `aot_check_policy=release_tag_only` ⇒ 非发布轮不作等级依据。

**旧任务 `proc_7b13a5969495` 的 `AOT_EXIT=1` 追认**：其日志 `/tmp/probe-r408/aot-publish.log`（49 行）内
**无任何 error、无 IL 警告**，且发布走完并产出完整 AOT 产物（`/tmp/aot-r408/agenthost` 14,778,256 B）
⇒ 判定为**采集侧假失败**（chained 脚本末条命令状态），非发布失败。
残留不确定性：旧命令原文未逐字复原（脚本未落盘），故本条为「证据支持的判定」而非「根因复原」。
