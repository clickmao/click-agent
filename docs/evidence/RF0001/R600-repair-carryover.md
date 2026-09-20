# R600 · 回灌修复环「带现状」（产品侧修复，用户令 2026-09-20「放行」）

## 改了哪一格读数

- **产品源码**：`src/agent/r1/ArtifactCarryover.cs`（新件）+ `R1Options`（新轴 `AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER`，缺省 on）+ `R1Pipeline`（两处回灌修复点随附盘上产物原文 + 台账字段 `artifact_carryover_rounds/chars`）
- **动机（实测定因）**：R585–R599 失败例次 100% 集中 wythoff 族（主桶冷集构造层）；R600 只读定因实测**失败臂的产物在题面公开用例上即失败**（w181-r3 `21 25`⇒`WIN 0 10`；w182-r3⇒`WIN 0 1`；w183-r3⇒`WIN 1 15` 非法着法），而管道**已**机械回放这些用例（public_probe_failed=2/8）、**已**花掉一次回灌修复 ⇒ 病灶 = 管道无状态（模型只产契约）而修复轮**不带模型上次写下的产物** ⇒ 盲修
- **语言无关**：只按字节搬运（不解析语义/不识别后缀）；越界路径、盘上缺失、二进制（含 NUL）不随附但显式列出；`__` 前缀目录静默跳过

## 门禁读数

| 面 | 读数 |
|---|---|
| build | `dotnet build` 0 error（全量测试编译通过） |
| 定向单测 | `ArtifactCarryoverTests` **7/7**（正控 3 + 零回归 1 + 反例 1 + 边界 1 + 轴解析 1） |
| 全量单测 | **1943/1943**（前态 1936 + 7） |
| 形式门禁 | `VerificationForm\|SkillGeneralization\|DevPlanDocRef` **14/14**（Failed 0） |
| API 基线 | **+8/−0**（全部为本轮新面：`ArtifactCarryover` 类型/成员 + `R1Options.ArtifactCarryoverEnabled` + 台账字段） |
| AOT 发布 | `dotnet publish src/agent.host -c Release -r linux-x64 -o …/pub_r600` **rc=0**、**IL 警告 0**、原生 ELF **19,735,472 B**、sha12 **8c3ade04d542**、`env -i` 冒烟 rc=0（禁 `-p:PublishAot`） |
| 真机 A/B | J1 PASS · J2 PASS（T 3/9 vs C 1/9）· J3 PASS · J4 FAIL |
| 铁律 11 | `exec_precondition.py --round r600` rc=1 |

## 判定与诚实边界

- 预注册 J1/J2/J3 全过 ⇒ **机制达标**；J4 为能力面次级（n=9/档 欠功率）⇒ 只并列，不作能力结论
- 被测件按设计变更（改产品源码 ⇒ 重发布 AOT）⇒ 与 R585–R599 冻结件轮**禁相减**
- J4 为 n=9/档 的欠功率读数 ⇒ 只作并列，不作能力结论
- 被测件按设计变更（产品源码改动 ⇒ 重发布 AOT）⇒ 与 R585–R599 冻结件轮**禁相减**
- 成本三列取中继 dump 时间轴；铁律 11 前置器 rc 见 precond-r600.json（rc≠0 ⇒ 标参考·未可验收）
- J2 的「收敛」按终态机械判（探针 failed==0 ∧ rc==0）；中间步骤失败不算收敛
