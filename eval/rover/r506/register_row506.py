#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R506 · 把候选④的闭合登记为**常驻守卫行** (L2)。

为什么必须登记: 项目铁律 (验证形式规范 R370) —— 任何「已完成/已验证」都要能指到
**登记行 + 可复现证据**; 指不到即视为未验证。候选④ 的闭合若只留在报告里, 下一个人
改动 `kpi_probe`/登记行时会**静默**把缺口带回来 (R504 的夹具正是硬编码 glob ⇒ 行改了
脚本不知道)。

工序纪律 (R409 实证后定稿):
  ① **先断言序列化器能逐字节复现原文件** (indent / ensure_ascii / 尾换行) —— 不复现就
     改用**文本插入**, 绝不静默重排整份 JSON;
  ② 幂等 (已存在同 id ⇒ 零改动退出 0);
  ③ 写后**读回**校验 (+ json.loads 全文件);
  ④ 只 append, 不动既有行的任何字节。

用法:
  python3 eval/rover/r506/register_row506.py --check
  python3 eval/rover/r506/register_row506.py --apply
退出码: 0 成功/已登记; 1 断言失败(拒绝落盘); 3 输入缺失。

范围: 本脚本只 append **行本身**。`evidence_generated_with` (证据绑定/器具钉) 由权威器具
`eval/capability/bind_evidence.py --only <id> --round <轮> --apply` **派生写入** —— 单一权威源,
不在此重复实现一份绑定规则 (实测: 只 append 行不带该字段 ⇒ R2f 红, 登记表闸当场拦下)。
"""
import argparse
import io
import json
import os
import sys

REG = "docs/verification-registry.json"
NEW_ID = "registry.evidence-cmd-replayable"
ROW = {
    "id": NEW_ID,
    "capability": "登记行的 evidence_cmd **可完整重放**其冻结证据面: 命令**从行自身派生**(不硬编码), "
                  "重放报告与冻结台账**逐字节等价**(白名单只含 `生成时间` 墙钟行, 其余零差异), "
                  "§二 对比段在册; 缺操作数 ⇒ 缺行判红, 多通配符 ⇒ 越界行(extra)同样判红",
    "level": "L2",
    "evidence_cmd": "python3 eval/rover/r506/replay_row2_closure.py",
    "evidence_path": "eval/rover/r506/evidence/replay-row2-closure.json",
    "negative_control": "前态臂: 逐字执行前态命令夹具 (缺 `--run <基线>` 那一版) ⇒ 必须**复现缺口**"
                        "(恰好缺 `probe-m6-agent.json` 一行: 8 行 vs 9 行) ⇒ 证明闭合非空心。"
                        "另两条结构断言: 结构变换 == 前态夹具(前态锚不漂移, 禁钉会前进的引用) ∧ "
                        "命令段数 != 3 ⇒ VOID 弃权(器具读契约不成立, 判弃权而非判红)",
    "covers": [
        "eval/rover/r506/replay_row2_closure.py",
        "eval/rover/r506/close_row2_replay_gap.py",
        "eval/rover/r506/prestate-kpi-stage.txt",
        "scripts/kpi_probe.py",
    ],
    "owner_round": "R506",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--registry", default=REG)
    a = ap.parse_args()
    if not os.path.isfile(a.registry):
        print("[致命] 登记表缺失")
        return 3
    raw = io.open(a.registry, encoding="utf-8", newline="").read()
    doc = json.loads(raw)

    # 前置: 证据面必须已存在 (禁登记「待生成」的证据)
    if not os.path.isfile(ROW["evidence_path"]):
        print("[致命] evidence_path 不存在: %s" % ROW["evidence_path"])
        return 3

    if any(r.get("id") == NEW_ID for r in doc["rows"]):
        print("[已登记] %s (幂等, 零改动)" % NEW_ID)
        return 0

    # ① 序列化器逐字节复现原文件 (形态由现盘反解, 不硬编码)
    ok_ser = False
    for indent in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=indent) + "\n" == raw:
            ok_ser = True
            print("[ser] 序列化器逐字节复现原文件: indent=%d ensure_ascii=False tail=LF" % indent)
            break
    if not ok_ser:
        print("[致命] 序列化器无法逐字节复现原文件 ⇒ 拒绝程序化改写 (改用文本插入)")
        return 1

    want = json.loads(raw)
    want["rows"].append(ROW)
    out = json.dumps(want, ensure_ascii=False, indent=2)
    # 形态与现盘一致 (现盘无尾换行? 由 raw 末字节反解, 不硬编码)
    if raw.endswith("\n"):
        out += "\n"

    # ② 语义等价: 除 append 一行外零变化
    undo = json.loads(out)
    popped = undo["rows"].pop()
    if popped != ROW or undo != doc:
        print("[致命] 写入对象 != 期望 (拒绝落盘)")
        return 1
    if len(want["rows"]) != len(doc["rows"]) + 1:
        print("[致命] 行数异常")
        return 1

    print("[plan] append 行 %s (level=%s, covers=%d)" % (NEW_ID, ROW["level"], len(ROW["covers"])))
    if a.check:
        return 0
    io.open(a.registry, "w", encoding="utf-8", newline="").write(out)
    back = io.open(a.registry, encoding="utf-8", newline="").read()
    if back != out:
        print("[致命] 写后字节不一致")
        return 1
    j = json.loads(back)          # ③ 读回可解析
    ids = [r.get("id") for r in j["rows"]]
    if ids.count(NEW_ID) != 1 or len(ids) != len(set(ids)):
        print("[致命] 读回校验失败 (重复 id 或计数不符)")
        return 1
    print("[OK] 已登记 %s; 总行数 %d -> %d" % (NEW_ID, len(doc["rows"]), len(j["rows"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
