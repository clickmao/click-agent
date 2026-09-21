# R623 DAG（意图 → 子任务；节点/依赖边/可并行面/收尾重启判据）

意图：把 **DoD 面 4「上下文精排」从「未测」变为「有读数」**（唯一权威进度面 = RF0005 §0 七面表；
唯一排期面 = RF0004 §4「DoD 缺口（并行面）· 精排四项实测」）。换杠杆依据 = RF0005 §3 **R2**：
wythoff 缺口已连续 3 轮（R620/R621/R622）无改判，且 R621 定案关闭等价面、R622 定案关闭成本三条款
⇒ **禁再加轮**，改面。

## 节点 / 依赖

| 节点 | 动作 | 依赖 | 出口证据 |
|---|---|---|---|
| N0 | 起手闸（roundcheck preflight R623 + 清 VBCSCompiler/MSBuild/pyright + 记 MemAvailable） | — | `preflight rc=0`（FAIL=0 WARN=0） |
| N1 | 主线提醒 1 行（§7 最新块 + RF0004/§0.4 + RF0005 §0/§3） | N0 | 报告结论行 |
| N2 | 选靶 = DoD 面 4（换杠杆） | N1 | 本节 + 预注册 `lever_switch_reason` |
| N3 | 文献小步（arXiv ≤3 query / 全文 ≤2 篇 / 间隔 ≥4s；只产机制假设） | — | `docs/research/lit-review-ledger.md` 追加行 |
| N4 | **预注册**（跑前落盘：轴 / 臂 / 冻结件 sha / 判据 / 证伪 ≥2 / 不宣称面） | N2 | `prereg-r623.json` |
| N5 | 器具（唯一落码面）：`src/agent.tests/RerankFaceTests.cs` = 在产品真身 `RAGRecall` 路径上驱动精排段并落盘逐查询读数 | N4 | 测试文件 + `readings` |
| N6 | 真机跑 = 定向跑该测试（本面**零远端调用**、零 LLM ⇒ 无 tokens/成本读数） | N5 | 测试 rc + 落盘 JSON |
| N7 | 判决：四值（NDCG@1/5/10 · MRR · P@1/5/10 · R@N）+ 生效遥测 + 两侧控制分离 | N6 | `verdict-r623.json` |
| N8 | 收口：报告 + registry 行 + kpi 行（带 `baselines`）+ 形式门禁 14/14 + `status_gen --check` PASS + 逐名列名提交 | N7 | commit + 回读 |

## 可并行面

- N3（网络只读检索）可与 N4 并行：**零仓内写**、零子 agent 抢仓 ⇒ 并行安全。
- **禁并行面**：N6 真机跑期间禁并发 build / 禁改 `src/`（本仓铁律）；N5 写 `src/agent.tests` 属被测工程
  ⇒ 与 N6 串行。

## 收尾重启判据（不重跑全轮）

| 触发 | 重启边 |
|---|---|
| N6 因 fixture 缺失 `skipped` | 只重启 N6 的前置（补件）后重跑 N6，**不重跑 N5** |
| N7 判据器读法定因（键/路径不符） | 只重启 N7（**只重跑后处理，不重测**；首跑读数留档不翻案） |
| N8 形式门禁红 | 只重启 N8 的失败项（旧读数保留） |
| 起手闸 fail-closed | 回 N0 清场重采样，**禁挪阈值** |
