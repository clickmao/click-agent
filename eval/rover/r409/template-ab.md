# R409 预备探针：本地模型的「模板化 vs 裸文本」同题 A/B

> 目的：回答「r1（R1-Distill-Qwen-1.5B）的输入是否必须严格模板化」——不用推断，用同机 A/B 实测。
> 判据**开跑前预注册**（R402 纪律），全部读数为机读，运行 2026-09-14 08:2x，单机 2 vCPU / 3.574 GiB / avx512。

## 1. 实验设计（自变量唯一）

| 项 | 值 |
|---|---|
| 模型 | `/tmp/models/r1-distill-qwen-1.5b-q4km.gguf` (1,117,320,800 B) |
| 运行时 | `llama-server` b1-4df29be（自 R408 起的唯一本地执行面） |
| 采样 | greedy（`temperature=0, top_k=1, top_p=1.0, min_p=0.0, repeat_penalty=1.0, seed=12345`） |
| KV / attention | `-ctk f32 -ctv f32 -fa off`（R407 对账口径，禁精度档翻档） |
| 线程 | `-t 1` |
| 端点 | `/completion` + `--no-jinja`（**排除 server 侧偷偷套模板**，模板只由 prompt 字节决定） |
| **自变量** | **prompt 字节**（其余全同） |

- 臂 A `prompt_raw.txt`（38 B / 15 token）：`What is 12*12? Answer with the number.`
- 臂 B `prompt.txt`（96 B / 18 token）：`<｜begin▁of▁sentence｜><｜User｜>What is 12*12? Answer with the number.<｜Assistant｜>`

## 2. 读数（两次运行：24 token 短窗 + 400 token 长窗）

| 臂 | pred tokens | stop_type | 是否出现 144 | 输出（head） |
|---|---|---|---|---|
| **A 裸文本** | 24 / 400 | `limit` / **`limit`** | False / **False** | `' To get started, you can use the number line to visualize the problem.\nTo get started, you can use the number…'`（**逐句重复、跑题、永不停止**） |
| **B 出厂模板** | 24 / 296 | `limit` / **`eos`** | False / **True** | `<think>\nTo calculate 12 multiplied by 12, … multiply 12 by 10 = 120, 12 by 2 = 24, adding … equals 144.` |

- 两侧 `tps ≈ 18.53 / 18.66` ⇒ **不是速度差异造成的假象**。
- A 臂 400 token 仍未出现 EOS；按 `max_tokens=8192` 计，成本还会再乘 **20.5×**。

## 3. 结论（可机械复核）

1. **r1 的模板是承重结构，不是格式美化**。同一权重、同一贪心、同一 KV 精度，只换 prompt 字节：
   `跑题死循环 + 不停止 + 无答案` ⇄ `在思考 + 正确 144 + 正常 EOS`。
2. **失败模式有两条，第二条更贵**：① 不答题；② **不出结束符** ⇒ 产品侧 token 成本失控（K2）且无法靠 offline 断言发现。
3. 因此「本地模型 prompt 的模板来源必须钉死」（GGUF 内 jinja），这条从「纪律」升级为**实测依据**。

## 4. 诚实边界

- n=1 题 × 1 采样 × 单模型；只作**方向性**证据，**不是能力分数**（沿用 `r403/nl_verify_cases.json` 的同款声明）。
- 24 token 短窗两臂都未给出 144 ⇒ 该窗口下唯一可判的是「在题上 / 不在题上」。
- 本实验只证明「模板缺失 ⇒ 行为崩」，**不**证明「模板正确 ⇒ 一定答对」；也未测多轮/停止符跨实现一致性。
- 裸文本臂 ≠ 官方推荐用法，本实验不代表该模型的正常使用形态，只标定「模板这一项的边际贡献」。

## 5. 复现

```sh
llama-server -m /tmp/models/r1-distill-qwen-1.5b-q4km.gguf --host 127.0.0.1 --port 8931 \
  -c 512 -t 1 -ctk f32 -ctv f32 -fa off --no-jinja --no-warmup
python3 eval/rover/r409/ab_template.py        # 短窗
python3 eval/rover/r409/ab_template_long.py   # 长窗（落 long-run.json）
```

> 待办（诚实登记）：本轮为 R408 收尾问答期的**预备探针**，尚未进 `docs/verification-registry.json`（该表与计划文档交叉校验，
> 需先有计划文档行）；主报告 §7 的 R408 条目亦未补。
