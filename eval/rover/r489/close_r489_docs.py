#!/usr/bin/env python3
"""R489 收口: 把 R489 段写入 iteration-master-plan.md（含**机取**索引表）与 improvements.md。
幂等: 段已存在则自 '## R489' 起整段替换; 保形: 段间空行 1, 索引表**只**由 registry 机取 (禁手改)。
"""
import io, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PLAN = os.path.join(ROOT, "docs", "reports", "iteration-master-plan.md")
IMP = os.path.join(ROOT, "docs", "improvements.md")
REG = os.path.join(ROOT, "docs", "verification-registry.json")

PLAN_NARR = """## R489（2026-09-16）主臂稳定性三跑 + 同窗基线 + 本地确认语文案裁决 — R488 的 −33.28% 降级为**单次读数**

- 靶点：把 R488 的「主 KPI 首次达线」变成**可信读数**。动因 = 同一臂参跨轮摆动（R487 `R485`=81,770 vs R488 `Rr`=47,333，**−42.1%**）且 R488 自身 H0 锚已 FAIL ⇒ 单次读数不作验收证据。
- 设计：**同一 AOT**（`/tmp/pub_r489/agenthost`，sha256 `e9b86fc9…`，15,363,728 B，IL 警告 0，`--version` rc=0）/ 同夹具 p12 / 同 role / 同窗口，臂 = `B`(gate=off,rs=off) ×1 + `R`(gate=on,rs=on) **×3**；分母只取**同窗 B**（跨轮一律不相减）。
- 本轮唯一源码改动 = **文案裁决**：`ModelQueueRouter.LocalSkipFallback` 由 `收到，继续按当前方向推进，本轮不重新规划。`（21 字，含**未被任何工作背书的动作声明**）→ **`收到。`**（3 字纯确认）；全量测试 **1510/1510 PASS**。
- 真跑：`bash eval/rover/r489/run_rest_r489.sh` ⇒ rc=0 / ALLDONE；B 臂 17 调用 **85,028 tok**；R1 **10/49,775（−41.46%）**、R2 **16/85,718（+0.81%）**、R3 **8/34,726（−59.16%）** ⇒ 三跑极差/中位 **102.45%**。
- 判据：**H1 FAIL**（min ≥30% 不成立，最差 **−0.81%**）· **H2 FAIL**（摆动 ≤0.15 不成立）· **H4 FAIL**（调用极差 8）· **H0 FAIL**（锚漂移 **+19.85%**）· **H3 PASS**（类别感知质量：非法模板 0/12，模板字符数 == 源码常量）。
- **方差归因（post-hoc）**：调用 = 远端轮 + **上游空正文(带 `tool_calls`)调用**（4/4/10/2；token 占比 22.8%/29.4%/**58.8%**/18.8%，`retry_skipped=True` 全真）；本地闸决策**三跑完全一致**（每臂 Skip 6 = 4 ack + 2 复述）⇒ 摆动**不来自本地通道**。
  剔除上游空正文后同窗降幅 **−46.46% / −46.21% / −57.05%**，调用数三跑同为 **6**（−53.85%）⇒ 本地通道增益稳定达线，**总口径不稳由上游行为面造成**。
- 器具：teardown **先按命名空间收口再断言** —— 首跑即捕获真泄漏（B 臂 `llama-server` RSS **1,781.8 MB**，cwd `rundata-Aroleb`，**非 host 直接子进程** ⇒ 既有 `pkill -P` 漏杀，与 R488 收尾泄漏同族）；修后 R1..R3 teardown 全 clean，`--selftest` 三例全过。
- 候选④：R486 差分夹具在 **`ACTION_LOOP=on`** 下重跑 ⇒ 桩请求 pre-empty **7** = post-empty **7**（差 0）⇒ 预注册 H1 **被证伪**；plain 阴性对照 1=1 ⇒ 该差分 **off/on 两形态均不复现**，宣称收窄。
- 诚实边界：n=3 跑 / 单夹具 / 无置信区间；**H5 为预注册缺陷**（B 臂 gate=off ⇒ 模板 0 是应然）保留 FAIL 不回改；跨轮不可比（H0 FAIL）；去空正文为 **post-hoc 单列**；候选⑤（R479 遗留）/⑥（上下文剪裁）**未做**（改链 ⇒ 换被测二进制，与稳定性窗口互斥）。
- registry：本轮 +5 行（`updated_round=R489`）。

### R489 · 轮次索引增量（机取自 `docs/verification-registry.json`，禁手改）
"""

IMP_NARR = """## R489（2026-09-16）主臂稳定性三跑：**单次读数不可用于验收**；本地通道增益稳定，摆动来自上游空正文

- 教训一（口径）：「主 KPI 达线」必须带**摆动**。R488 的 −33.28% 在 R487/R488/R489 三次同臂参读数里是 81,770 / 47,333 / {49,775, 85,718, 34,726} ⇒ 单点达线**不能**作验收证据；正确形态 = 同窗分母 + 重复 N 跑 + 报**下界**（本轮下界 −0.81%）。
- 教训二（归因顺序）：先问「摆动的来源」再谈优化。本轮把调用数拆成「远端轮 + 上游空正文调用」后，摆动 100% 落在上游空正文数（2..10/轮，占 token 0..59%）⇒ 剔除该面后本地通道的降幅**三次全 ≥46%** 且调用数三跑相同。**未做此拆解前，任何「臂不稳」的结论都会归错因**。
- 教训三（器具）：`pkill -P $HOST_PID` **不足以**收夹具 —— 实测 `llama-server` 不是 host 直接子进程，断言/收口都必须**按命名空间**扫 `/proc`（并排除自身与全祖先链，禁 `pgrep -f` 直喂 kill）。
- 教训四（预注册质量）：H5「template 轮数 == 确认类轮数」对 gate=off 的 B 臂**结构性不可满足** ⇒ 预注册写判据时必须逐臂检查可满足性；本轮保留 FAIL、post-hoc 修正读数单列。
- 教训五（文案）：本地确定性答复**不得声称做了事**。`收到，继续按当前方向推进，本轮不重新规划。` → `收到。`，并以「模板字符 ⊂ 认可族字符集 ∧ 遥测 chars == 源码常量长度」机检绑定二进制与源码。
"""


def main():
    reg = json.load(io.open(REG, encoding="utf-8-sig"))
    rows = sorted([r for r in reg["rows"] if r.get("owner_round") == "R489"], key=lambda r: r["id"])
    lines = ["| %s | `%s` | %s | %s … |" % (r["owner_round"], r["id"], r["level"],
                                           r["capability"].replace("\n", " ")[:90]) for r in rows]
    rounds = sorted({r["owner_round"] for r in reg["rows"]})
    tail = ("\n".join(lines) + "\n\n覆盖自检: 轮号 %s；registry rows=%d，updated_round=%s。\n"
            "**缺登记行轮号: %s**\n" % (rounds, len(reg["rows"]), reg["updated_round"],
                                        "无" if "R489" in rounds else "R489"))

    def write(path, header, body):
        txt = io.open(path, encoding="utf-8").read()
        m = re.search(r"^## R489", txt, re.M)
        if m:
            txt = txt[:m.start()]
        while not txt.endswith("\n\n"):
            txt += "\n"
        io.open(path, "w", encoding="utf-8").write(txt + header + body)
        return bool(m)

    r1 = write(PLAN, PLAN_NARR, tail)
    r2 = write(IMP, IMP_NARR + "\n", "")
    print(json.dumps({"rows_machined": len(rows), "registry_rows": len(reg["rows"]),
                      "plan_replaced": r1, "improvements_replaced": r2,
                      "plan_lines": len(io.open(PLAN, encoding="utf-8").read().splitlines()),
                      "imp_lines": len(io.open(IMP, encoding="utf-8").read().splitlines())},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
