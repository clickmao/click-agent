#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R593 收口补丁：把 D1 探针的**具体形态族**回填到 轮志 / verdict / 主报告 §7 块（只改本轮自己新增的行；幂等）。"""
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r593")
PLAN = os.path.join(REPO, "docs/reports/iteration-master-plan.md")

FAM = ("`AttributeError: module 'games.wythoff' has no attribute 'solve'` **30**"
       "（= **2 个整跑次** `r588/w163`、`r591/w166` 各 15 例全灭 ⇒ 交付物未暴露入口）、"
       "`IndexError: list index out of range` **15**、"
       "`TypeError: 'NoneType' object is not subscriptable` **11**、"
       "`TIMEOUT_60s` **8**、`TypeError: %d format: a real number is required, not NoneType` **2**")


def patch(path, old, new, must=1):
    t = io.open(path, encoding="utf-8").read()
    n = t.count(old)
    if n == must:
        io.open(path, "w", encoding="utf-8").write(t.replace(old, new))
        print("patched %s (x%d)" % (os.path.basename(path), n))
    elif n == 0 and new.split("**形态族**")[0] in t and new in t:
        print("already patched %s" % os.path.basename(path))
    else:
        print("SKIP %s (count=%d != %d)" % (os.path.basename(path), n, must))


def main():
    d = json.load(io.open(os.path.join(R, "d1-stderr-probe-r593.json"), encoding="utf-8"))
    rank = d["family_rank"]
    old_a = ("追加探针把 66 例次定因到具体形态：产物侧 rc 分布 `{1: 58, 124: 8}` ⇒ "
             "**58/66 = 带异常退出、8/66 = 60s 挂死超时**；探针逐例重放与产物侧 rc/空正文"
             "**零不一致**（`mismatch=0`）⇒ 重放可信。")
    new_a = (old_a + " **形态族**：" + FAM + "；探针逐例重放与产物侧 rc/空正文**零不一致**"
                     "（`mismatch=0`，66/66）⇒ 重放可信、rc 口径与产物侧同源。"
                     "⇒ **定因收口**：D 桶最大单一形态 = **交付物未暴露入口**（2 整跑次全灭），"
                     "其次输出侧下标/None 类异常与挂死 —— **均属执行/交付形态面，非题目语义错**。")
    patch(os.path.join(PLAN), "**58/66 = 带异常退出、8/66 = 60s 挂死超时**；探针逐例重放与产物侧 rc/空正文**零不一致**（`mismatch=0`）⇒ 重放可信。",
          "**58/66 = 带异常退出、8/66 = 60s 挂死超时**；**形态族**：" + FAM +
          "；探针逐例重放与产物侧 rc/空正文**零不一致**（`mismatch=0`，66/66）⇒ 重放可信、rc 口径与产物侧同源；"
          "⇒ **定因收口**：D 桶最大单一形态 = **交付物未暴露入口**（2 整跑次全灭），其次下标记/None 类异常与挂死 —— **均属执行/交付形态面，非题目语义错**。")
    patch(os.path.join(PLAN),
          "② **执行面崩溃面只读定因**：58 例 `rc=1` 的 stderr 形态族（异常类名 / 消息首词，已按族落盘）⇒ 判「交付出畸形产物」还是「答案错但格式合法」",
          "② **降级为已闭合（R594 不再重做）**：58 例 `rc=1` 的 stderr 形态族**已在本轮落盘**（`AttributeError: … has no attribute 'solve'` 30 / `IndexError` 15 / `NoneType` 下标 11 / `%d` 2）；R594 改为**入口契约面只读定因**：判「2 整跑次缺入口」是**产物侧契约未暴露**还是**题面未写明入口名**（只读：比对裁判侧导入路径 vs 题面文字）")
    patch(os.path.join(PLAN),
          "④ codex 独有 (b) 窗 `w154` 单窗只读定因。",
          "④ codex 独有 (b) 窗 `w154` 单窗只读定因 ⑤ **形态族按窗集分层**：`IndexError`/`NoneType` 是否集中在特定窗（只读，扩展本轮探针的按窗聚合）。")
    patch(os.path.join(R, "report-r593.md"),
          "- 探针定因（66 例次逐例重放，`mismatch=0`）：rc 分布 `{1: 58, 124: 8}` ⇒ 主体为**带异常退出**，另 **8 例 60s 挂死**",
          "- 探针定因（66 例次逐例重放，`mismatch=0`）：rc 分布 `{1: 58, 124: 8}` ⇒ 主体为**带异常退出**，另 **8 例 60s 挂死**\n"
          "- **形态族（机械归类，只看末行异常类名/消息首词）**：\n"
          "\n| 形态 | 例次 | 说明 |\n|---|---|---|\n"
          "| `AttributeError: module 'games.wythoff' has no attribute 'solve'` | **30** | = **2 个整跑次**（`r588/w163`、`r591/w166`）各 15 例全灭 ⇒ 交付物未暴露入口 |\n"
          "| `IndexError: list index out of range` | 15 | 输入解析/边界处理缺失 |\n"
          "| `TypeError: 'NoneType' object is not subscriptable` | 11 | 未自验产物 |\n"
          "| `TIMEOUT_60s` | 8 | 挂死（rc=124） |\n"
          "| `TypeError: %d format: a real number is required, not NoneType` | 2 | 打印未自验 |\n")

    vp = os.path.join(R, "verdict-r593.json")
    v = json.load(io.open(vp, encoding="utf-8"))
    v["candidate2_D_subdivision"]["probe_family_rank"] = rank
    v["candidate2_D_subdivision"]["decision"] = (
        "D 桶 95.65% 为进程非零退出（执行/交付形态面），非非法着法/词标/畸形输出；"
        "最大单一形态 = 交付物未暴露入口 `solve`（30 例 = 2 整跑次全灭），其次 IndexError 15 / NoneType 下标 11 / 挂死 8 / %d 2")
    with io.open(vp, "w", encoding="utf-8") as fh:
        json.dump(v, fh, ensure_ascii=False, indent=1)
    print("verdict 已回填形态族")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
