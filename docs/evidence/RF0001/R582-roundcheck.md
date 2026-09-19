# R582 — 每轮有效性校对 + 起臂前置闸器具（`tools/roundcheck`）

口径（用户令逐字）：「**你需要一些额外的调试工具来帮你校对每轮有效性和验证你的方案可行性**」
⇒ 拆成两问落地：**「这一轮算不算有效」**（台账/证据/提交面一致性）与**「方案跑不跑得起来」**（起臂前置条件）。

## 1. 交付物

| 文件 | 作用 |
|---|---|
| `tools/roundcheck/roundcheck.py` | `audit`（10 条轮有效性判据）+ `preflight`（8 条起臂可行性判据）+ `--selftest` |
| `tools/roundcheck/README.md` | 判据表 / 用法 / 纪律 / 边界 |

`audit` 判据：R1 登记行 · R2 提交唯一（0 = 未落档，≥2 = **轮号重号**）· R3 证据在位 · **R4 冻结 pin 与现盘字节一致**
· R5 文档结构（诚实边界/无占位符）· R6 提交面卫生（文件数 ≤40 = 疑 `git add -A` 的**代理**判据）· **R7 提交内无 key 面**
· R8 读数有档（build · 形式门禁 · 通过率 `x/y`）· R9 暂存面卫生 · W1 工作区 key 面提醒。
`preflight` 判据：P1 依赖 key 面 set/unset（**只回字符数, 绝不回显值**）· P2 权重在盘 · P3 `MemAvailable` · P4 磁盘余量
· P5 在飞执行体 · P6 轮号仲裁 · P7 目标轮号空闲 · P8 `PUSH_PAUSED`。退出码 0/1/2 = 无 FAIL / ≥1 FAIL / 用法错。

## 2. 读数（真机实跑）

| 命令 | 结果 |
|---|---|
| `roundcheck.py --selftest` | **PASS** — 负控 3/3 有牙（错 pin⇒R4 红 · 提交内 key 面⇒R7 红 · 无提交轮号⇒R2 红）+ 假红控制 1/1 + 正控 1/1 |
| `roundcheck.py audit --round R580` | **rc=0**（10 条无 FAIL；首跑曾 R7 假红，见 §3） |
| `roundcheck.py audit --round R581` | **rc=1** — `R1_registry_row` 无 `owner_round=R581` 行 ∧ `R8_readings_backed` 缺 build/形式/通过率读数 |
| `roundcheck.py preflight --round R582` | **rc=1** — `AGENTFRAMEWORK_FRONTEND_TOKEN` UNSET · `MemAvailable=2467MB < 2650MB` · `free=2GB < 5GB` |

R581 那两条 FAIL 是**发现**（该轮 KPI 只在 tick 消息里声明，登记表与证据面无背书），本轮**不替对侧登记**（共享台账纪律）；
preflight 三条 FAIL 恰是器具要提前拦下的三类翻车（key 面缺 ⇒ 臂全 VOID / 起手闸不过 / 磁盘告警），非器具缺陷。

## 3. 器具自证过程（一次真翻车 + 修）

- R580 首跑 `R7` 判红 `docs/verification-registry.json` 与 `eval/capability/kpi.jsonl`；**查证为假红** ——
  正则 `sk-...` 吃掉了合法标识符 `ta|sk-plan-...` / `ta|sk-lengt...` ⇒ 加左边界 `(?<![A-Za-z0-9_])`，
  并补**假红控制**（`task-*` 不得误判）入 `--selftest` ⇒ 复跑 R580 rc=0、selftest 仍 PASS。

## 4. 闸

build `agent.sln -c Release` **0 error**（84 warning）；形式门禁（`VerificationForm|SkillGeneralization|DevPlanDocRef`）
**14/14**（Failed 0 / Skipped 0 / Total 14）；全量 `agent.tests` Release **1920/1920**（Failed 0 / Skipped 0 / Total 1920）。

## 5. 诚实边界

- 器具**只审「台账 / 证据 / 提交面」的一致性，不判产品能力**；R6 的 40 文件阈值是 `git add -A` 的**代理判据，不是证明**。
- 判据本身未被第三方（codex 对照臂）复核；未接 CI/门禁，靠人工在每轮起手与收口各跑一次。
- 本轮实跑为**单次确定性比对**（非统计量）⇒ 不适用 reps≥3；但 R2/R4/R7 依赖 git 与文件字节，无随机面。
- 未做：轮内「读数真实性」核验（文档里的数字能否追到日志文件）—— 现只校验「有没有」，不校验「对不对」。
