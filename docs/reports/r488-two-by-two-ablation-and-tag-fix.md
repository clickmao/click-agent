# R488（2026-09-16）真机 2×2 析因消融 + 候选④ TAG 修复 — **主 KPI 首次达线（token −33.28%）**，质量面判负

## 0. 为什么这样设计（因果链）

- R487 的结论是「主 KPI 判负」+ 归因「R485 每调用 prompt 5,540 vs Arole 4,071（+36%）⇒ 剩余调用上下文变长」，
  但它**同时翻动 `turn_gate` 与 `repeat_skip` 两开关** ⇒ 归因只是相关，不是因果（R487 自述「未做因果分离」）。
- 本轮把两开关拆成 **2×2 析因**，四臂**同一刻、同一二进制、同一夹具、同一 key、同一内存闸**，只翻开关：
  `B`(gate off, rs off) / `G`(gate on, rs off) / `S`(gate off, rs on) / `R`(gate on, rs on)。
- 二进制 = AOT 产物 `/tmp/pub_r485/agenthost`，**sha256 `03c77d56e8c485af…` / 15,363,728 B / IL 警告 0** = R485 AOT pin（`eval/rover/r485/aot_r485.txt`），
  `git status --porcelain -- src/` 空、`src/` 最后提交 `f1201bc`(R485) ⇒ **本轮零 C# 改动 ⇒ 读数只能归因于开关翻转，不能归因于二进制**。

## 1. 真跑

```
bash eval/rover/r488/run_both_r488.sh     # rc=0, [both-r488] ALLDONE 12:35:19
```
四臂各 12 轮（本地中继 → 真供应商，`relay_real_r475.py` v2，MAX_CALLS=40 / 上限 0.15 CNY，`blocked=0`×4）。

## 2. 读数（供应商 usage 真值列；候选④ 修复后**臂自身**列非空）

`eval/rover/r488/verdict-r488.json`（机取，禁手抄）：

| 臂 | turn_gate | repeat_skip | 调用 | prompt | completion | total tok | tok/调用 | 空正文 | 去重答复 |
|---|---|---|---|---|---|---|---|---|---|
| B | off | off | 15 | 65,882 | 5,062 | **70,944** | 4,729.6 | 3 | 12/12 |
| G | on | off | 12 | 52,742 | 5,388 | **58,130** | 4,844.2 | 4 | 9/12 |
| S | off | on | 14 | 62,699 | 3,697 | **66,396** | 4,742.6 | 2 | 12/12 |
| R | on | on | 11 | 44,216 | 3,117 | **47,333** | 4,303.0 | 5 | 7/12 |

同刻差分（vs B）：G 调用 −20.0% / token **−18.06%**；S 调用 −6.67% / token **−6.41%**；R 调用 −26.67% / token **−33.28%**。

## 3. 预注册判据（`eval/rover/r488/prereg_r488.json` → 机检）

| 判据 | 结果 | 机检读数 |
|---|---|---|
| H1 主 KPI B→R ≥30% | **PASS** | 70,944 → 47,333 = **−33.28%** |
| H2 `turn_gate` 单独使 prompt/调用变长 | **FAIL（方向被证伪）** | 4,392.1 → 4,395.2（**+3.1**）⇒ R487 的「剩余调用上下文变长」归因在本夹具**不成立** |
| H3 `repeat_skip` 单独为负效应 | PASS | 调用 15→14，token −6.41% |
| H4 可加性 | **FAIL** | 残差 −6,249 = **−8.81% of B** ⇒ 两开关**超加性**，禁由单开关相加外推 |
| H5 质量面（去重答复 ≥10/12） | **FAIL（R）** / **FAIL（G）** | R 7/12、G 9/12；B/S 12/12 |
| H6 候选④ TAG 修复 | PASS ×4 | 四臂 usage 行数 **15/12/14/11** == 中继真值列 |
| H0 跨轮锚 | **FAIL** | B 70,944 vs R487 `Arole485` 63,825 = 漂移 **11.15%**（>10%）⇒ **本轮只做同刻差分，不与 R487 相减** |

## 4. 质量细读（R 臂，逐字）

- t2–t5（「谢谢，收到。」/「好的，明白。」/「嗯嗯，知道了。」/「明白，多谢。」）⇒ 逐字同一句 **21 字模板**：
  「收到，继续按当前方向推进，本轮不重新规划。」（4 轮，**未声明是本地 skip**）；
- t6 逐字 = t1、t9 逐字 = t8（**复述回放** 2 轮）⇒ 实质轮 **6/12**；机械去重口径 7/12。
- ⇒ 这是候选③「skip 类答复不得冒充实质答（复用须显式声明）」的**真实基线**：−33.28% 的降幅**主要由这条模板通道买来**。

## 5. 归因（算术可验）

- token 达线靠 `turn_gate`（G 单独 −18.06%），`repeat_skip` 质量安全但只 −6.41%；两者叠加 −33.28% **同时把质量压到 7/12**
  ⇒ **「token 降 ≥30%」与「回复质量不降」本轮不能同时宣称**（R413 验收②达成、验收③质量面未达成）。
- H2 被证伪后，R487 的 +36% prompt/调用**不再是开关效应**；与 H0 漂移合并看，R487 的 `R485`=81,770 与本轮 `Rr`=47,333
  （**同臂参**）相差 **−42.1%** ⇒ 主臂读数**不稳定**，单次读数不足以定论。

## 6. 候选⑥：对侧 R486 器具**首次真跑**（修命名 bug）

- 发现并修器具缺陷：`check_r486.py` 的 `TAGS` 写作 `pre-empt/post-empt`，而运行器 `run_diff_r486.sh:28` 用
  `TAG=$ARM-$(echo "$MODE" | cut -c1-5)` ⇒ 实际文件名是 `*-empty` ⇒ 修前只读到 2/4 臂、恒 `rc=3 缺输入`（**该器具此前从未跑到判据**）。
- 真跑：`bash eval/rover/r486/run_diff_r486.sh` ⇒ **rc=0**；`python3 eval/rover/r486/check_r486.py` ⇒ **rc=1（判据 FAIL）**：
  `H1 FAIL`（pre_empty=1 vs post_empty=1，delta=0）/ `H3 FAIL`（pre 期望 2）/ `H4 FAIL`（pre 遥测 `retry_skipped` 0/0，post 1/0）/ `H2 PASS` / `NC1 PASS`。
- 判读：**「空正文(带 tool_calls)⇒浪费重试」的 pre/post 差分在本夹具未复现**；夹具 `AGENTFRAMEWORK_ACTION_LOOP=off` ⇒ 重试路径可能结构上不可达。
  **不据此宣称修复生效或失效**（预注册前提被证伪 ⇒ 宣称收窄）。
- 真机空正文基数（真值列，与对侧读数合并）：全调用 B 3/15 · G 4/12 · S 2/14 · R 5/11；
  剔除前 2 次结构性调用 ⇒ B 1/13 · G 2/10 · S 0/12 · **R 3/9（33%）**（空正文集中在 R 臂）。

## 7. 环境/器具事件（不掩盖）

- 起手闸 **fail-closed 两次拒跑**（`MemAvailable` 2,614 MB / 2,640 MB < 2,650 MB，闸为单一源 `eval/rover/r483/preflight_gate.py`，`grep -c 2650` 手抄字面量 0）。
- 处置：判定 `pyright-langserver`(pid 1593597) 为**闲置孤儿**（6 s 内 CPU tick 0、fd 中 socket 0、RSS 345 MB）⇒ 释放 + `drop_caches` ⇒ **2,987 MB PASS**；
  **全程未杀任何在跑作业/未动他方文件**，仅释放自身环境的孤儿资源。

## 8. 器具与门禁读数（本轮真跑）

- **测试**：`env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR $HOME/.dotnet/dotnet test src/agent.tests/agentframework.tests.csproj -c Release`
  ⇒ **Passed 1510 / Failed 0 / Skipped 0**（RC=0）。修前同命令 = 1508/1510，**两个失败恰是登记表形式门禁**
  （`Registry_Exists_And_HasNoViolations`、`Registry_EvidenceBindings_CoverProductFace`）——根因即本轮新增 3 行缺 `evidence_generated_with`（R2f）；
  补字段（`artifact_sha12`/`instrument_sha12` 由 `append_registry_r488.py` **机算**，缺文件即 rc=3 拒写）后复跑 `--filter VerificationFormTests` = **7/7 PASS**。
- **台账**：`docs/verification-registry.json` rows 160 → **163**，`updated_round=R488`，尾换行在位，读回自检 `readback_ok=true`（3 行整行替换，非追加重复）。
- **二进制形态**：`sha256(/tmp/pub_r485/agenthost)` = `03c77d56e8c485af…` = R485 AOT pin（15,363,728 B，IL 警告 0，publish rc=0）；`git status --porcelain -- src/` 空 ⇒ 四臂读数绑定同一 AOT 产物。
- **门禁**：起手闸单一源两次 fail-closed 拒跑后经环境回收 PASS（详见 §7），四臂各跑一次闸，`blocked=0` × 4。

## 9. 诚实边界

- 单夹具单次（n=12，无置信区间）；跨轮**不可比**（H0 FAIL）⇒ 本轮结论只建立在**同刻四臂**上。
- 未测：端到端答复**质量面**的判定仍用「逐字去重」机械代理（无人工/模型评分）；`turn_gate` 模板通道的语义正确性未测。
- 未做：②上下文剪裁 / ③skip 显式声明 / ⑤R479 遗留（三者都要改链代码 ⇒ 换掉被测二进制，与本轮真机臂窗口互斥）。
- 未改任何 C# 源码 ⇒ **未做 AOT 重发布**（被测二进制即 R485 AOT pin，sha256 已核）；未 push（`.git/PUSH_PAUSED` 在位）。
