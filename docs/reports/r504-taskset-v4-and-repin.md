# R504 · 题集 v4 扩面 + 同窗外部对照 + 器具改后重审

## 因果链
R503 留下 6 项候选 ⇒ 本轮按「全候选并轮」一次推进: ① 题集 v4 扩到 11 题 (游戏族 3→5: +`nim_multi`/`wythoff`; 见证族 3→4: +`witness_crt`) ⇒ 仪器自检 53/39/31 ⇒ **61/48/37** ⇒ 器具一改, 引用它的两条冻结行 (registry) 立即失配 ⇒ 候选⑥ 全量单测首轮**真实抓到** `Registry_Exists_And_HasNoViolations` 红 (1633/1634) ⇒ 触发 R2e 重审规程 (证据面重生成 + 3 字段重钉 + 声明重审 + 权威门禁 + 负控) ⇒ 修后 10 连跑 1634/1634 全绿。主线上: 11 题冻结题集, oracle 正控 97/97, 同窗 codex-cli 对照判据全过。

## 本轮产出 (文件 / 命令 / 读数)
1. **题集 v4** (`eval/rover/r504/taskset-r504.json`, 11 题 = 7 程序族 + 4 见证族): oracle **97/97=1.0000**。
   - `nim_multi`: 自检 4/4 满分; 负控 `mutation:nim_greedy` 整题 **0/2** (用例级 0.25 — 口径=整题)
   - `wythoff`: 自检 4/4 满分; 负控 `mutation:wyth_greedy` 整题 **0/2** (用例级 0.154)
   - `witness_crt`: 正控满分; 负控 `mutation:wrongfinal` 单题 `wrong_witness` 判红
2. **同窗外部对照** (`eval/rover/r504/run_contrast_r504.sh` → `verdict-r504.json`, judge rc=0, H1–H6 全 PASS):
   | 侧 | 调用数 | prompt | completion | 总 token | 整题全对 |
   |--|--|--|--|--|--|
   | codex-cli | 21 | 144,168 | 8,281 | **152,449** | 11/11 |
   | 本项目 AOT | 17 | 86,755 | 8,047 | **94,802** | 10/11 |
   ⇒ token **−37.8%** (判据① 成立); 调用数 **−19.0%** (判据② 未达 −30%); 质量 10/11 vs 11/11 (唯一失手 p004 `wythoff` 用例 10/13)。
3. **候选② `vm_run` 归因**: 冻结 vm_run 题集 (2 题/23 用例) 连跑 **6 臂** ⇒ 6/6 整题全对、23/23 用例; 叠本轮主窗 12/12 ⇒ R503 的 partial **不复现** (n=7 观测 0 次)。
4. **候选⑤ 全量单测 n=10** (`eval/rover/r504/cand5_unit_n10.sh`): 10 连跑 **1634/1634 passed, failed=0, rc=0** (修前首轮 1633/1634)。
5. **候选④ r433 行证据面可重放夹具** (`replay_r433_face.py`): 9 行冻结读数 ⇒ 重放复现 **8 行, drift=0**; 声明缺口 1 行 (`probe-m6-agent.json`, 行自带 glob `*r433*` 覆盖不到 = **行自身的 evidence_cmd 不足以完整重放**) ⇒ `PASS_DECLARED_GAP`。
6. **器具改后重审** (R2e): `gen_probe_evidence_q28.py` 重生成 ⇒ 53/39/31→**61/48/37**, artifact sha12 `0cdf31bdb101`→`0f16d271c894`, instrument `2dba8418221c`; `decl_sweep.py --apply` 2 处漂移→**0**; `ruling_r504_repin.py --apply --only` 重钉 2 行 (行 658/660/662/1518/1520); 门禁 `bind_evidence.py --check` → **0 VIOLATION, R2E_R2F_EXIT=0**; 负控 (假 sha) → 门禁红且**点名该行**, exit=2。
7. **AOT**: `dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r504/agenthost` ⇒ rc=0, **IL 警告 0** (CS 警告 6 为既有), 二进制 15,409,088 B, sha256 `dcb747e873645084adc5c560cab24382a54836a49ef9312c42ada4ccfcdbb57c`。

## 诚实边界
- 候选③ **未跑通**: `cand3_degrade_longsrc.py` 起手闸 (连续 2 PASS) 未 PASS (本地 3B server 缺席, curl rc=7) ⇒ **fail-closed rc=3**, 退化率读数**为 0 条**(不是 0.0 的读数, 是「未测到」)。
- 判据② (远端调用数 ↓≥30%) 本轮 **不成立** (17:21 = −19.0%), 只有判据① (token −37.8%) 成立; 本轮 token 差主要来自 prompt 侧 (agent 86,755 vs codex 144,168)。
- 质量面 n≥3: 本轮仅 vm_run 族做了 n≥3 (6 臂); **全 11 题集质量面仍是单窗** (n=1)。
- 候选④ 的重放缺口 1 行**未闭合** (行 2 的 evidence_cmd 缺 baseline 文件名 glob)。
- ② 的 6 臂只覆盖 vm_run 2 题/23 用例, 不等于「全族无摆动」。

## 下轮候选 (R505)
① (主线) 题集 v4 上**质量面 n≥3** 同窗对照 (全 11 题, 每臂逐字节同题集) ② 判据② 攻坚: 远端调用数 ↓≥30% (在 17 → ≤14 上做定位: 逐题列调用构成) ③ 本地 3B 长原文退化率扫描 (**须先起 llama-server + 起手闸 2 PASS**, 否则继续 fail-closed) ④ 行 2 重放缺口: 把 baseline run 纳入行内夹具 glob 或降级声明 ⑤ MCP 链级 E2E (需用户改立场, 排除项) ⑥ 全量 n≥10 已达成 → 转「每提交必跑」。
