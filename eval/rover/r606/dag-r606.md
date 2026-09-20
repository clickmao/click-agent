# R606 DAG（放行后的产品侧单变量轮）
## 节点 / 依赖 / 并行面 / 重启判据
| 节点 | 依赖 | 并行面 | 重启判据 |
|---|---|---|---|
| N1 产品改动（R1Options 缺省翻档） | 用户「全部放行」 | 独占（写 src/） | 单测红 ⇒ 就地修，不换变量 |
| N2 形式门禁 + 定向/全量单测 + API 基线 | N1 | 与 N3 竞争 CPU ⇒ 串行 | 红 ⇒ 停止起臂 |
| N3 AOT 重发布 pub_r606（禁 -p:PublishAot） | N1 | 与 N2 串行 | IL 警告 >0 或 rc≠0 ⇒ 停止起臂 |
| N4 起手闸（清场 + 3 样本 + 连续 2 次 PASS） | N3 | 独占 | 余量不足 ⇒ fail-closed（记 WINDOW_UNOPENABLE） |
| N5 逐窗：C1 codex×1 → T×3 → C×3 | N4 | 同窗串行（内存 3.6G / 单 llama-server） | 窗内异常 ⇒ 该窗重跑，禁跨窗拼读数 |
| N6 judge_r606（J1–J5 + v3 配对 + W_floor + LD 诊断） | N5 | 独占 | 判据器自检红 ⇒ 器具缺陷，先修器具 |
| N7 报告 + 提交（逐名列名） | N6 | 独占 | 缺件 ⇒ 不得宣称可验收 |
## 变量面
- 单变量：`AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR`（T=产品缺省 1 / C=显式 0）
- 不变：冻结题集 sha e0c667c2 / carryover 缺省 on 两侧 / C1 同环境同模型
- 窗集：w196 w197 w198（第十二集）
