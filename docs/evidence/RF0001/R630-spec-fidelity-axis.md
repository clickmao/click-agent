# R630 · 恒前缀尾部追加块（规格保真自检）—— 单变量轴第四档 `spec`

轮次：R630（2026-09-22）· 协议：`docs/plans/RF0005-completion-protocol.md` §1/§2/§3
证据级别：**L3**（真机运行：AOT 发布件 + 真远端调用 + 逐跑次判分）· 非 L4（未做跨机复现）

## 1. 单变量轴

| 项 | 值 |
|---|---|
| 轴（既有 env，**新取值**） | `AGENTFRAMEWORK_R1_ACTION_PROMPT` |
| T 档 | `spec` ⇒ 生效前缀 = 缺省块正文 + `<spec_fidelity>` 尾块 = **16182 字符** |
| C 档 | unset ⇒ 产品缺省 = R617 现盘块 = **15796 字符**（逐字节等于冻结 pin） |
| 臂身份 | 两臂**同一枚 AOT 二进制**（`pub_r630/agenthost` sha256 `cefd045e8d1d4258…`，运行前后一致性检查落盘 `bin-sha-check.json`） |

## 2. 前缀不变量（器具机检，rc=0）

`python3 eval/rover/r630/gen_prefix_r630.py` ⇒ `eval/rover/r630/prefix-r630.json`

| 档 | chars | 说明 |
|---|---|---|
| default（缺省） | 15796 | R617 现盘 pin（sha `25c97bef…`） |
| r615（锚） | 15794 | 历史档可复现 |
| legacy（锚） | 15675 | R610–R614 冻结 pin |
| **spec（本轮治疗档）** | **16182** | 缺省块正文 + 386 字符尾块（sha `b687c6dd…`） |

八条 checks 全绿：`body_append_only`（去尾闭合标签后新块正文以旧块正文**逐位为前缀**）· `four_tiers_distinct` ·
`spec_longer_than_default` · `default_bytes_unchanged` · `closing_tag_preserved` · `min_chars_gate` ·
`inserted_block_wellformed` · `inserted_block_substantive`。

## 3. AOT 面（发布形态铁律）

`bash eval/rover/r630/aot_r630.sh` ⇒ `PUBLISH_RC=0 IL_WARNINGS=0 ERRORS=0`，ELF `19,870,960 B`，
sha16 `cefd045e8d1d4258`；**双档装载冒烟**（仓库外 cwd + `env -i`）：
`MODE=off SMOKE_RC=0 drift_rc6_hits=0` / `MODE=spec SMOKE_RC=0 drift_rc6_hits=0`
⇒ 轴门禁（`R1Pipeline` 的 `EffectiveChars/EffectiveSha256Pinned` 双档判定）对治疗档**不误判漂移**。

## 4. 真机臂（w211/w212；reps=3；每跑次独立会话 + 洁净工作区）

冻结题集 `eval/rover/r618/taskset-r618.json`（sha `e0c667c2…`，逐字节复用）· 题面 `prompt_sha256 516f3208…`（chars 2182）·
模型通道 = 中继适配器 `eval/rover/r455/adapter_tools.py @ :49794`（relay 到真实上游；逐调用 usage 落盘）。

| 臂 | w211 通过数 | w212 通过数 | 中位 | 极差 | 计划未跑完 |
|---|---|---|---|---|---|
| T（spec） | 58 / 56 / 58 | 58 / 50 / 58 | 58 / 58 | [50, 58] | 3/6（`expect_stdout_exhausted`） |
| C（缺省） | 58 / 58 / 58 | 58 / 54 / 58 | 58 / 58 | [54, 58] | 1/6 |

失败形态：`stdout_mismatch`（期望 `WIN 15 15` / 格子图，实测**空**）——与 R629 `wythoff` 族归因的
「产物未按题面规格自验即交付」同族；**尾块未消除该形态**。

## 5. 成本（口径 = **中继逐调用 usage**；`transcript.cache_*` 是末次值，不作比率）

`python3 eval/rover/r630/adapter_usage_r630.py` ⇒ `cost-r630.json`（25 条 dump，臂归属按**实发 system 长度**分类，
`unknown=0`；恒等式 `prompt_tokens == cache_hit + cache_miss` 全 25 条成立）

| 臂 | 调用 | 新算 prompt(miss) | completion | 命中率 v_all |
|---|---|---|---|---|
| T（spec） | 11 | 11,251 | 46,482 | 0.8915 |
| C（缺省） | 14 | 11,061 | 58,490 | 0.9147 |

## 6. 判决（`judge-r630.json`，rc=0）

`J0=J1=J2=J3=J4=true`；但**轴裁定 = 定案关闭**：`swing=8 ≥ effect=0`
⇒ 按 §3「摆动 ≥ 效应 ⇒ 该轴非承重变量、定案关闭（禁调阈值）」。**本轮不宣称任何收益**。

## 7. 诚实边界 / 器具自捕缺陷（三条，全部留档不翻案）

1. **v1 跑次全 VOID（rc=6/`llm_transport`）**：首跑驱动脚本未做 cfg 端口替换、也未起中继适配器
   ⇒ 12/12 跑次 0 秒退出（"Connection refused 127.0.0.1:48600"）。跑次目录**改名保留**
   （`runs/r630-v1-void-notransport`，禁删）。
2. **v1 判据器假绿**：同一批 VOID 日志上判据器给出 `rc=0 / J0=true`（它只看前缀读数，不看是否真达模型）
   ⇒ 留档 `v1-judge-falsegreen-r630.json`。
3. **v2 判据器误判 VOID**：修成「`rc != 0` ⇒ VOID」后又把 `rc=5`（计划未跑完，**已真实调用**）当 VOID
   ⇒ 5/12 跑次被剔除 ⇒ 停链 rc=3；留档 `v2-judge-r630.json`。**修法 = 判据改为「未达模型」**
   （`calls<1 ∨ stage=llm_transport`），并对**同一批日志**零重测复算 ⇒ v3。
   影子自检扩到 **7 态**（含 S6 全 VOID 必判 rc=2、S7 计划未跑完**不得**判 VOID）。

## 8. 未测 / 遗留

- 未跑 codex 同窗外部真值臂（本窗 0 条）⇒ 质量面只作**臂间并列**，不作对外宣称；`F_merge.quality.cases_median_truth`
  为**跨窗并列**引用（标「参考」）。
- 铁律 11 前置器 `exec_precondition.py --round r630` = **rc=3（DISCOVER_FAIL）** ⇒ 按铁律 11，
  本轮**不宣称**任何 token/调用降幅为可验收读数（成本列只作**并列观测**）。
- `R1Transcript.prefix_pinned` 布尔仍按**缺省档**钉值比较 ⇒ spec 档恒 `false`（标签面缺陷，**本轮只登记不改**，
  防混淆单变量）。
- 「按题族分列」判据候选（文献小步 §R630 台账）未实施。
