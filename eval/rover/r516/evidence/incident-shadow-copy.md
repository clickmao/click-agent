
## 7 事故与修复 (R516 自抓, 记为诚实边界而非静默)
**现象**: 提交前钩子 BLOCKED (R2e) —— `r444.separability-precheck` 自证器具路径与声明不符, `r444.instrument-acceptance` 语义投影 pin 与现盘不符。
**根因 (机检定位)**: ① 我在 `/tmp/r516/head_tree` 建了一份**归档影子副本**去跑器具面 (想取 HEAD 基线, 该路后废弃); ② `eval/rover/r444/precheck_prefilter.py:22` **硬编码** `ROOT = pathlib.Path("/home/agentuser/AgentFramework")`, 于是**影子副本进程写回了真实仓**的产物, 且 `INSTRUMENT.relative_to(ROOT)` 失配 ⇒ 产物与登记行被写入**绝对 /tmp 路径** (`provenance.instrument` / `evidence_generated_with.instrument`); ③ 器具面每次执行都会**重跑**自身 evidence_cmd ⇒ 产物 (及其 pin) 必然随树态漂移 (自指成员)。
**修复 (逐条可复跑)**: `python3 eval/rover/r444/precheck_prefilter.py --out eval/rover/r444/precheck-prefilter.json` (rc=0) → `--neg-control` (rc=2 设计值, 负控「检出 ≥1 反例」OK) → 登记行 instrument 复原为仓内相对路径 → `bind_evidence --only r444.separability-precheck --round R516 --apply` 与 `--only r444.instrument-acceptance` (各 `R2E_R2F_EXIT=0`) → 提交态核验 `COMMITTED_STATE_CHECK=OK (rows=232 claims=296 blobs=252)`。
**残留**: 两条 r444 行的 `audited_by_round` 因本轮定向重审由 EXP1-Q34/EXP1-Q39 前进为 R516 (pin 确由 R516 写入, 属事实记录)。
**教训 (下轮候选 ⑥)**: 器具面复跑前必须先确认**无影子副本**; 硬编码 ROOT 的器具在副本内执行会污染真实仓 ⇒ 需给器具面加「根路径自证」负控 (副本内跑必须判红)。
