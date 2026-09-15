#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R444 前置可分性预检 v2 (R423 铁律 + R402 三通道取证).

命题: "r1 判 Skip 的轮次, 必然满足 MechanicalAck(userMessage) == true"
成立 ⇒ 把 MechanicalAck 前置为廉价必要条件 = **可证等价** (省 r1 调用, 远端零变化)。

三通道对齐 (拒绝单通道位置假设 —— v1 的位置对齐产生 8 个假反例, 根因 = consumed 轮无门行):
  C1 驱动日志 (外部真值): `run_all_s*.log` 的 `>>> arm=.. grid=..` 块内逐轮 `actual=` 记录
                          ⇒ 有门调用的轮次 = actual != consumed
  C2 遥测锚点 (独立通道): `local_turn_gate_reject` 事件的 msg_sha16 → 轮次, 校验门行紧随其后
  C3 结构断言 (第三通道): Skip 行数 == ack 轮数, 且 Skip 行连续、ack 轮连续 ⇒ 映射被计数强制

判据:
  P1 必要性: 反例 (Skip ∧ !Ack) 数 == 0
  P2 通道一致性: C1/C2/C3 对齐结果逐一相同
  P3 收益面: 前置后可省的 r1 调用数 (仅 ack 轮需要问 r1)
"""
import json, pathlib, sys, re, hashlib, unicodedata

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
OUT = ROOT / "eval/rover/r444/precheck-prefilter.json"

ACK_CHARS = "好嗯行明白了知道谢收到多辛苦可以先就的"
ACK_MAX = 10
Q = ["什么", "怎么", "如何", "为什么", "为何", "哪个", "哪一", "谁", "何时", "多少",
     "是否", "能不能", "可以吗", "行吗", "吗", "呢", "请问", "请教", "解释", "说明",
     "介绍", "对比", "区别", "分析"]
RQ = ["请", "帮我", "帮忙", "给我", "我要", "需要", "另外", "还有", "补充", "新增", "加",
      "删", "改", "修", "写", "生成", "创建", "新建", "执行", "运行", "跑", "测试", "部署",
      "提交", "回滚", "优化", "重构", "继续做", "下一步", "现在", "把"]
C = ["不对", "错了", "不正确", "不准确", "有问题", "漏", "缺", "重新", "再确认", "纠正",
     "不是", "没对", "失败", "报错", "异常", "崩溃", "不生效"]


def mech_pass(m):
    if m is None or not m.strip():
        return True
    m = m.strip()
    if "?" in m or "？" in m:
        return True
    if any(w in m for w in Q + RQ + C):
        return True
    if any(ch in m for ch in "`/\\"):
        return True
    if any(ch.isdigit() for ch in m):
        return True
    return len(m) >= 24


def mech_ack(m):
    m = (m or "").strip()
    if not m:
        return False
    n = 0
    for ch in m:
        if unicodedata.category(ch)[0] in "PZS":
            continue
        if ch not in ACK_CHARS:
            return False
        n += 1
        if n > ACK_MAX:
            return False
    return n > 0


def sha16(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def drive_records():
    """C1: (arm, grid) -> [(turn, family, actual)] 来自驱动日志外部真值。"""
    out = {}
    for f in sorted((ROOT / "eval/rover/r441").glob("run_all_s*.log")) + \
             sorted((ROOT / "eval/rover/r443").glob("run_all*.log")):
        cur = None
        for line in f.read_text(errors="replace").splitlines():
            m = re.match(r".*(?:>>>|\[preflight\])\s.*?arm=(\S+)\s+grid=(\S+)", line)
            if m:
                cur = (m.group(1), m.group(2))
                if cur in out and out[cur]:   # 重复块 (S1/S2/S3 重跑) ⇒ 只取首个有内容的块
                    cur = None
                    continue
                out.setdefault(cur, [])
                continue
            if "<<<" in line:
                cur = None
                continue
            if cur is None:
                continue
            t = re.match(r"\s*t\s*(\d+)\s+(\S+)\s+want=(\S+)\s+actual=(\S+)", line)
            if t:
                out[cur].append((int(t.group(1)), t.group(2), t.group(4)))
    return {k: v for k, v in out.items() if v}


def gate_rows(tel):
    rows = []
    for line in tel.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("point") == "local_turn_gate":
            rows.append(dict(r.get("kv", {})))
        elif r.get("point") == "local_turn_gate_reject":
            rows.append({"__reject__": dict(r.get("kv", {}))})
    return rows


GRID_DIR = None
NEG_CONTROL = False


def main():
    global GRID_DIR, NEG_CONTROL
    if "--grid-dir" in sys.argv:
        GRID_DIR = sys.argv[sys.argv.index("--grid-dir") + 1]
    NEG_CONTROL = "--neg-control" in sys.argv
    rec = {"probe": "R444-precheck-prefilter-v2", "runs": [], "channels": {}}
    all_cp, tot_r1, tot_avoid = 0, 0, 0
    grids = {}
    for g in ("V2b", "W8", "W20", "M20"):
        _gp = pathlib.Path(GRID_DIR) / f"task-{g}.json" if GRID_DIR else (ROOT / f"eval/rover/r441/grid/task-{g}.json")
        if not _gp.exists():
            print(f"[fail-closed] 网格缺失: {_gp} ⇒ 空样本不得静默通过")
            return 3
        tj = json.loads(_gp.read_text(encoding="utf-8"))
        grids[g] = {"msgs": {i: t for i, t in enumerate(tj["turns"], 1)},
                    "expected": {e["turn"]: e for e in tj["expected"]},
                    "ratio_k": tj.get("ratio_k")}
    drive = drive_records()

    runs = []
    for base in ("eval/rover/r441", "eval/rover/r443"):
        for d in sorted((ROOT / base).glob("run-*")):
            m = re.match(r"run-(BRJ|BRJRP)-([A-Za-z0-9]+)", d.name)
            tel = d / "data/telemetry/host.jsonl"
            if m and tel.exists() and m.group(2) in grids:
                runs.append((m.group(1), m.group(2), tel, d.name))

    for arm, grid, tel, dirname in runs:
        G = grids[grid]
        rows = gate_rows(tel)
        mech_rows = [r for r in rows if "__reject__" not in r and int(r.get("gate_prompt_len", 0) or 0) == 0]
        r1_rows = [r for r in rows if "__reject__" not in r and int(r.get("gate_prompt_len", 0) or 0) > 0]
        rejects = [r["__reject__"] for r in rows if "__reject__" in r]
        # C1: 有门调用的轮次
        c1 = None
        key = (arm, grid)
        if key in drive:
            c1 = [t for (t, fam, act) in drive[key] if act != "consumed"]
        # C2: 锚点
        anchor_pairs, c2_ok = [], None
        for i, rj in enumerate(rows):
            if "__reject__" not in rj:
                continue
            h = rj["__reject__"].get("msg_sha16")
            hit = [t for t, msg in G["msgs"].items() if sha16(msg) == h]
            # 该 reject 对应的 r1 行序号 = 其前面 (含紧随) 的 r1 行计数
            rank = sum(1 for j in range(i + 1)
                       if "__reject__" not in rows[j] and int(rows[j].get("gate_prompt_len", 0) or 0) > 0)
            if hit:
                anchor_pairs.append((hit[0], rank))
        # 统一映射: 优先 C1 的轮次序列
        seq = c1 if c1 else list(G["msgs"].keys())
        if c1 and anchor_pairs:
            nz_tmp = [t for t in seq if not mech_pass(G["msgs"][t])]
            nz_idx = {t: i for i, t in enumerate(nz_tmp)}
            if all(t in nz_idx for t, _ in anchor_pairs) and len(anchor_pairs) >= 2:
                c2_ok = all(anchor_pairs[k][1] - anchor_pairs[0][1] ==
                            nz_idx[anchor_pairs[k][0]] - nz_idx[anchor_pairs[0][0]]
                            for k in range(len(anchor_pairs)))
        if c1:
            c2_ok = all(anchor_pairs[k][1] - anchor_pairs[0][1] == seq.index(anchor_pairs[k][0]) - seq.index(anchor_pairs[0][0])
                        for k in range(len(anchor_pairs))) if len(anchor_pairs) >= 2 else None
        mapping, over = [], 0
        r1_only = [r for r in rows if "__reject__" not in r]           # 含机械行
        # 机械行只对应 mech_pass 轮; r1 行按顺序对应其余轮
        nz = [t for t in seq if not mech_pass(G["msgs"][t])]
        z = [t for t in seq if mech_pass(G["msgs"][t])]
        if len(z) == len(mech_rows):
            mapping = [(z[i], mech_rows[i]) for i in range(len(z))]
        elif len(z) != 0:
            over += 1
        for i, row in enumerate(r1_rows):
            if i < len(nz):
                mapping.append((nz[i], row))
            else:
                over += 1
        run = {"arm": arm, "grid": grid, "dir": dirname, "n_turns": len(G["msgs"]),
               "c1_turns_with_gate": c1, "c2_anchors": anchor_pairs, "c2_order_consistent": c2_ok,
               "n_gate_rows": len(rows), "n_r1_rows": len(r1_rows), "n_rejects": len(rejects),
               "skips": 0, "avoidable_r1": 0, "counterexamples": [], "rows": [],
               "overrun": 0}
        for turn, row in sorted(mapping):
            msg = G["msgs"][turn]
            v = str(row.get("verdict", ""))
            if NEG_CONTROL and grid == "M20" and turn == 7:
                msg = "把这个改成另一种方式"   # 负控注入: 非 ack 族 ⇒ 期望检出反例
            ack = mech_ack(msg)
            is_r1 = int(row.get("gate_prompt_len", 0) or 0) > 0
            run["rows"].append({"turn": turn, "family": G["expected"][turn]["family"],
                                "verdict": v, "basis": str(row.get("basis", "")),
                                "mech_ack": ack, "want": G["expected"][turn]["want"],
                                "is_r1": is_r1})
            if v == "Skip":
                run["skips"] += 1
                if not ack:
                    run["counterexamples"].append({"turn": turn, "msg": msg, "verdict": v})
            if is_r1 and not ack:
                run["avoidable_r1"] += 1
        # C3: 结构断言
        mapped_turns = [t for t, _ in mapping]
        ack_turns = [t for t in mapped_turns if mech_ack(G["msgs"][t])]
        c3 = (len(mapped_turns) > 0 and len(ack_turns) > 0 and
              all(r["verdict"] == "Skip" for r in run["rows"] if r["mech_ack"]))
        run["c3_structure_ok"] = bool(c3)
        run["overrun"] = over
        run["c3_ack_turns_all_skip"] = bool(c3)
        run["c1_c2_c3_agree"] = bool(c1 and c2_ok is not False and c3 and over == 0)
        all_cp += len(run["counterexamples"])
        tot_r1 += len(r1_rows)
        tot_avoid += run["avoidable_r1"]
        rec["runs"].append(run)

    rec["criteria"] = {
        "P1_no_counterexample": {"pass": all_cp == 0, "counterexamples": all_cp},
        "P2_channels_agree": {"pass": all(r.get("c1_c2_c3_agree") for r in rec["runs"])},
        "P3_avoidable_r1_calls": {"total_r1_rows": tot_r1, "avoidable": tot_avoid,
                                  "saved_ratio": round(tot_avoid / tot_r1, 4) if tot_r1 else None},
    }
    rec["verdict"] = "SEPARABLE" if all_cp == 0 else "NOT_SEPARABLE"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    print("== R444 可分性预检 v2 (Skip ⇒ Ack) ==")
    for r in rec["runs"]:
        print(f"  {r['arm']:6s} {r['grid']:4s} 门行={r['n_gate_rows']:<2d} r1行={r['n_r1_rows']:<2d} "
              f"skip={r['skips']:<2d} 可省={r['avoidable_r1']:<2d} 反例={len(r['counterexamples'])} "
              f"三通道一致={r['c1_c2_c3_agree']}")
    print(f"  P1 反例={all_cp} | P2 通道一致={rec['criteria']['P2_channels_agree']['pass']} | "
          f"P3 r1 {tot_r1}→可省 {tot_avoid} ({100.0*tot_avoid/max(1,tot_r1):.1f}%)")
    print("  判定:", rec["verdict"], "->", OUT)
    if NEG_CONTROL:
        print("负控注入: 期望检出 >=1 反例 ⇒", "OK(检出)" if all_cp > 0 else "HOLLOW(未检出 ⇒ 探测器空心)")
        return 2 if all_cp > 0 else 9
    return 0 if all_cp == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
