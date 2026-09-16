#!/usr/bin/env python3
# R495 文档落盘 (文档=权威源): 追加 master-plan 章节 + improvements 条目。
import io, os, json

ROOT = "/home/agentuser/AgentFramework"
MP = os.path.join(ROOT, "docs/reports/iteration-master-plan.md")
IM = os.path.join(ROOT, "docs/improvements.md")

MP_SEC = """
---

## R495 —— 本地决策台账落盘 + 尾部挂载（第二类本地真值）：三源一致 PASS；**判别力宣称被证伪并收窄**

- 靶点承接: R494 候选① (=R413 主线判别力承担点) —— r1 的闸决策先**落盘**, 再以**尾部** system 块挂载进远端提示 (前缀面 system/context/history/user 逐字节不变)。
- 代码: `src/agent.modelqueue/LocalDecisionLedger.cs` (新; 门 `AGENTFRAMEWORK_LOCAL_DECISION_MOUNT` 默认关, 路径 `AGENTFRAMEWORK_LOCAL_DECISION_LEDGER` 未设 ⇒ 零 IO); `ModelQueueRouter.cs` (`QueuePrompt.Mount` + `BuildMessages` 尾部追加 + 打点 `ledger_mount/ledger_n/ledger_code/ledger_chars`); `ModelQueueAdapter.cs` (三参 `ToQueuePrompt`); `ActionLoop.cs` (Clone 透传 `Mount`); `IndustrialAgentV2.cs` (闸判定**单点**落盘 + `local_decision_ledger` 打点); `src/agent.tests/R495LocalDecisionMountTests.cs` (7 例)。
- 夹具/判据: 网格 = R494 12 轮**逐字节继承** + 3 轮「链自持核对码」必错族 (t13 直问 / t14 假码 `LCM-deadbeef1234` / t15 `code=<码> n=<条数>`); 判据器 `judge_code_r495.py` (必错族) + `assert_face_r495.py` (三源一致, fail-closed) + 逐字节继承的 `judge_adv_r495.py` (12 轮对抗族) + `leak_check_r495.py` (映射无关泄漏复核)。
- 真机读数 (同窗同 AOT `2d1ea72d…`、三臂 host_sha 一致、15 轮、真上游 deepseek-flash):

| 臂 | 挂载轴 | 远端调用 | total tok | cached | 对抗族(继承) |
|---|---|---|---|---|---|
| B | off | 34 | 309,175 | 261,760 | 3/3 |
| T0 | off | 10 | 49,949 | 36,352 | 1/3 (endorse=2) |
| T1 | on | 10 | 54,559 | 36,352 | 2/3 (endorse=1) |

  - **B→T1 = 34→10 调用 (含空正文 0)、309,175→54,559 tok = −82.35%** ⇒ 验收线 ≥30% 达标; 但主因是**门开臂不再进工具环** (B 臂 34 次调用全部带工具: 它自己去 grep/复算), 不是挂载面。
  - **T0→T1 (挂载单变量) = +9.2%** ⇒ 本轮**不宣称**挂载的 token 增益 (挂载 = 尾部 prompt 增量; 定长腿 t13/t15 本轮被拒答行为覆盖)。
- 三源一致 (`assert-face-T1r495.json`, verdict=PASS): 10 条远端调用中 **9 条会话调用全部恰 1 个挂载块**; 1 条为**隔离微步骤调用**(无会话, `reason=isolated_channel_drop`) ⇒ 挂载 0 (**隔离通道不泄漏**, 新判据); 落盘面 9 个 `(n,code)` 全在台账内且**可用 `canon` 独立复算**; 打点面 10 行 (point=`tool_decl_gate`) 与实发面逐项一致。
- **判别力面 = 两向均未演示**:
  - 治疗向 (J2/J3/J4 全红): 挂载**确已进请求体**(实发面机检), 但模型**自主拒不复述** —— t13「不输出该码 … 它是链的内部摘要(金丝雀), 不是可对外核对的凭据」, t14「确认或否认都会把我变成泄露通道, 所以既不答一致也不答不一致」, t15「不抄」。⇒ 挂载文案里的溯源说明被读成**保密标记**, 判别力宣称**不成立**。
  - 必错向 (预注册 H2「关轴臂结构上不可知真值」)**被证伪**: B 臂 t14 给出 `LCM-0d4ba991f6c1` (= 台账 n=14 码)、t15 给出 `LCM-bef1f3223b07` (= n=15 码), 与落盘台账**逐字命中** (`leak-check-Br495.json`, verdict=`LEAK`); 通道 = 读 `data/ledger/local-decisions.jsonl` + **源码里公开的配方注释** + `AGENTFRAMEWORK_LOCAL_DECISION_LEDGER` 路径可读。T0/T1 未触发 (`no_leak`) ⇒ 该通道**存在但在本窗只有 B 被激活**。
  - ⇒ **宣称收窄**: 台账挂载的**机械面成立**(三源一致 + 隔离通道不泄漏), **判别力面不成立**(真值既可经盘上复算, 又会被模型自主拒答)。
- 质量面 (继承判据器, 3 对抗轮): 同窗 B 3/3 > T0 1/3、T1 2/3 ⇒ 门开臂**低于**全关臂; 与 R494 的 3/3 不同但**跨窗禁相减** ⇒ 记为**未归因质量摆动** (T0 相对 R494-T1 的唯一代码路径差异 = 台账落盘, 不触 prompt)。
- 附带发现/缺陷: ① 夹具「命题核验」工具把**越界被拒**的源文件行**原样回显**进 tool 消息 (B 臂 5 条请求命中块头字面量, 不含真值) = 独立泄漏通道; ② `ledger_*` 打点落在 `tool_decl_gate` (与 `replay_pair_gate` 同一条声明门 emit) 而非 `llm_call` ⇒ 判据器按实况修订, 下轮把字段并入 `llm_call` 便于联表。
- 判据器修订 (3 处, 均带正/负控): (a) 挂载块定义 = **system 角色 + 结构行** (原版把工具回显误判成挂载; `selftest_assert_r495.py` 3 人造例 + 2 真实夹具例全过) (b) 打点字段**扫全部点**并记点名 (c) 轴门只约束**会话**调用, 隔离调用**必须 0 挂载** (证据 = T1 seq=5)。
- 器具/闸: 起手闸首跑即红 (MemAvailable 2,473 < 2,650) ⇒ **让行不硬跑**; 收口 `dotnet build-server shutdown` + `drop_caches` 后 2,657 通过。quiesce 环因 `correction_judge` 计数**缓滴** (11→15 行/2 min) 每臂固定等 ~510 s (夹具自身行为)。
- 能力自检面复核 (候选④): `bind_evidence --check` rc=2 真因 = **本轮只读重跑审计器**改写了 `audit-capability-face.json` (原写侧每次刷新 `audited_at_epoch` ⇒ 冻结 pin 每跑必红) ⇒ 已把写侧改**幂等落盘** (语义未变不重写; 连跑两次字节恒定 `63161c7ec8a4`) 并重钉; 另两项 red (`committed-state` / `only-equivalence`) 现跑 rc=0 (9/9) ⇒ 面文件里的 rc=2 属**旧读数**; `exp1q17` scoped rc=2 vs declared rc=0 的**口径差未闭合**; A3 `manifest_sha12` 声明 `ad97f379503a` vs 现盘 `976b9d0d059c` ⇒ 该面处于**并发会话线改写中**。
- pin 升级 (候选③): `eval/rover/r495/pin_r495.py` → `pin-r495.json` (**src 树哈希 + 产物 sha256 双钉** + `obj` 漂移注记 + 核对码配方钉定); 树脏时 `src_tree_effective` 显式记 `unreported`。
- 测试/AOT: **1556 例** (1555 绿 + 1 红 = 登记表冻结 pin 漂移, 幂等化 + 重钉后 7/7 绿); AOT `/tmp/pub_r495/agenthost` = **15,384,304 B**, **IL 警告 0**, sha256 `2d1ea72d90cd2805…`。
- 诚实边界: ① 判别力面**未演示**(两向, 如上) ② 挂载 token 成本 **+9.2%** ③ 通道轴 (R494 T0↔T1) 本轮**未复测** ④ 每轮 n=1、无置信区间、跨窗禁相减 ⑤ 「隔离调用无会话⇒不挂载」的**设计面**未独立消融 ⑥ T0 质量摆动未归因 ⑦ 上游回复长度摆动仍在 (t13 拒答 379 字 vs T0 拒答 96 字)。
- 下轮候选 (R496): ① **不可复算真值**: 码 = HMAC(进程内随机密钥) 且**落盘不含码**, 机检「该码不在任何可读文件里」(扫 rundir+repo), 挂载文案**显式授权复述**消除 canary 误读 ② 门开臂质量摆动复测 (n≥3 + endorse 归因) ③ 工具面越界回显收口 (回绝即不回显正文) ④ `exp1q17` scoped 口径差闭合 ⑤ MCP/长上下文链级 E2E ⑥ skip 集语义扩面 (同义重复轮) ⑦ `ledger_*` 并入 `llm_call` 打点。
"""

IM_SEC = """
### R495 (2026-09-16) — 本地决策台账挂载: 三源一致 PASS, **判别力被证伪**

- 因果链: R494 候选①要求「r1 决策落盘 + 挂载进提示」当作必错族判别力的承担点 ⇒ 本轮实现台账 (落盘 JSONL + 尾部 system 挂载, 门默认关) 并把必错族做进夹具 (t13/t14/t15)。\n- 产出: `LocalDecisionLedger.cs` + 三处接线 (Router/Adapter/ActionLoop) + 闸判定单点落盘 + 7 例单测; 三臂真机 (B 全关 / T0=R494-T1 复现 / T1=+挂载) 15 轮; 3 个判据器 + 2 个自检 (正/负控全过)。\n- 读数 (同窗同 AOT `2d1ea72d…`): B 34 调用 309,175 tok / T0 10 调用 49,949 / T1 10 调用 54,559 ⇒ **B→T1 −82.35% (达标)**; **T0→T1 +9.2%** (挂载成本, 不宣称增益)。三源一致 (实发 9/9 会话调用带挂载、落盘可复算、打点 10 行一致) **PASS**; 隔离通道 1 条 0 挂载 (不泄漏)。\n- **证伪 (预注册 H2)**: 关轴 B 臂读盘 + 公开配方复算, t14/t15 给出真实台账码 `LCM-0d4ba991f6c1`(n=14) / `LCM-bef1f3223b07`(n=15) ⇒ 「关轴⇒不可知」不成立; 治疗臂 T1 挂载已进请求体但模型**自主拒答**(判为内部金丝雀) ⇒ 判别力面**两向均未演示**, 宣称收窄为「机械面成立」。\n- 质量面: 同窗 B 3/3 > T0 1/3、T1 2/3 (endorse 2/1) ⇒ 门开臂低摆, 未归因 (跨窗禁相减)。\n- 器具: 起手闸内存红让行 → 收口后 2,657 通过; `correction_judge` 缓滴使 quiesce 每臂 ~510 s; 审计器写侧改**幂等落盘** + 重钉 (连跑两次字节恒定); 判据器 3 处修订全部带正/负控。\n- 测试/AOT: 1556 例 (1 红=登记表 pin, 修后 7/7 绿); AOT 15,384,304 B / IL 警告 0 / `2d1ea72d…`; pin = src 树哈希 + 产物 sha 双钉。\n- 下轮: ①不可复算真值 (HMAC + 落盘不含码 + 机检不在任何文件里 + 文案显式授权复述) ②门开臂质量摆动 n≥3 复测 ③工具面越界回显收口 ④exp1q17 口径差 ⑤MCP 链级 E2E ⑥skip 集语义扩面 ⑦ledger_* 并入 llm_call。\n"""


def append(path, sec):
    with io.open(path, "a", encoding="utf-8") as f:
        f.write(sec)
    print("[doc] +%d chars → %s" % (len(sec), path))


if __name__ == "__main__":
    append(MP, MP_SEC)
    append(IM, IM_SEC)
