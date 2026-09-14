#!/usr/bin/env python3
"""R428 · 同文折叠 (排序/去重层) 真机成对臂机检。
外部真值: 每臂每语料 = 独立 cwd 的冻结语料副本 + 通道级遥测 + stdout 渲染原文; 语料逐字节校验未被改动。
判据见 docs/plans/v0.49.0-r428-duplicate-collapse.md (T0 冻结)。"""
import hashlib, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FIX_A = os.path.join(REPO, "eval", "capability", "r422", "fixture-sessions")
CORPUS_D = "/tmp/r428-corpus-D"
ARMS = {"N": "/tmp/pub_r423/agenthost", "T": "/tmp/pub_r428/agenthost"}
QUERIES = {"A": ["存在", "不存在"], "D": ["存在", "外星词zzq"]}
# R423 verdict 已落档读数 (T_treated|A) —— 臂身份自证锚点 (C1)
REG_TREATED_A = [["cli-6bf6dc8d", 0.2798],
                 ["probe-0914125816-p004", 0.1408],
                 ["probe-0914125831-p005", 0.1408]]
FACTS = "/tmp/r428_facts.json"          # 外部事实: C6 单测 / C7 形态 (由真实命令输出机检生成)
OUT = os.path.join(HERE, "verdict-r428.json")

RX_HIT = re.compile(r"^(\d+)\. (\S+)\s+score=([0-9.]+)\s+entries=(\d+)(?:\s+同文副本\+(\d+))?\s*$", re.M)
RX_DECL = re.compile(r"命中 (\d+)\)")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def digest(d):
    return {n: sha256(os.path.join(d, n)) for n in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, n))}


def write_corpus_d():
    os.makedirs(CORPUS_D, exist_ok=True)
    for f in os.listdir(CORPUS_D):
        os.remove(os.path.join(CORPUS_D, f))
    docs = [("r428-d1", "存在 甲甲甲甲甲甲甲甲甲甲 乙乙乙乙乙乙乙乙乙乙"),
            ("r428-d2", "存在 丙丙丙丙丙丙丙丙丙丙 丁丁丁丁丁丁丁丁丁丁")]
    for sid, body in docs:
        with open(os.path.join(CORPUS_D, sid + "_memory.json"), "w", encoding="utf-8") as f:
            json.dump({"SessionId": sid, "MaxChars": 1000, "LongTermMemory": body, "EntryCount": 1},
                      f, ensure_ascii=False)
    return digest(CORPUS_D)


def identical_groups(corpus_dir):
    """闭式同文判定 (Python 侧独立实现): 正文剥空白后逐字符相等 ⇒ 同文组。"""
    bytext = {}
    for n in sorted(os.listdir(corpus_dir)):
        if not n.endswith("_memory.json"):
            continue
        with open(os.path.join(corpus_dir, n), encoding="utf-8") as f:
            d = json.load(f)
        key = "".join((d.get("LongTermMemory") or "").split())
        bytext.setdefault(key, []).append(d.get("SessionId"))
    dup = {k: v for k, v in bytext.items() if len(v) > 1}
    return {"groups": [sorted(v) for v in dup.values()],
            "expected_keeper": [min(v) for v in dup.values()],
            "docs": sum(len(v) for v in bytext.values())}


def run_arm(arm, corpus_key, binary, fixture):
    cwd = "/tmp/r428-cwd-%s-%s" % (arm, corpus_key)
    shutil.rmtree(cwd, ignore_errors=True)
    os.makedirs(os.path.join(cwd, "data", "sessions"), exist_ok=True)
    for n in os.listdir(fixture):
        shutil.copy2(os.path.join(fixture, n), os.path.join(cwd, "data", "sessions", n))
    before = digest(os.path.join(cwd, "data", "sessions"))
    telemetry = os.path.join(cwd, "data", "telemetry", "host.jsonl")
    readings = {}
    for q in QUERIES[corpus_key]:
        if os.path.exists(telemetry):
            os.remove(telemetry)
        p = subprocess.run([binary, "-q", "/recall " + q], cwd=cwd, capture_output=True, text=True,
                           timeout=180, env={k: v for k, v in os.environ.items() if k != "DOTNET_ROOT"})
        points = []
        if os.path.exists(telemetry):
            with open(telemetry, encoding="utf-8-sig", errors="replace") as f:
                for ln in f:
                    ln = ln.strip()
                    if ln:
                        try:
                            points.append(json.loads(ln))
                        except json.JSONDecodeError:
                            points.append({"raw": ln})
        hits = [{"rank": int(m.group(1)), "id": m.group(2), "score": float(m.group(3)),
                 "entries": int(m.group(4)), "folded": int(m.group(5) or 0)} for m in RX_HIT.finditer(p.stdout)]
        decl = RX_DECL.search(p.stdout)
        readings[q] = {
            "rc": p.returncode,
            "hits": hits,
            "hit_ids": [h["id"] for h in hits],
            "ranked": [[h["id"], h["score"]] for h in hits],
            "folded": {h["id"]: h["folded"] for h in hits if h["folded"]},
            "declared": int(decl.group(1)) if decl else None,
            "recall_points": len([x for x in points if x.get("point") == "recall_query"]),
            "llm_call_points": len([x for x in points if x.get("point") == "llm_call"]),
        }
        with open(os.path.join(HERE, "stdout-%s-%s-%s.txt" % (arm, corpus_key, q)), "w", encoding="utf-8") as f:
            f.write(p.stdout)
    after = digest(os.path.join(cwd, "data", "sessions"))
    return {"binary": binary, "binary_sha256": sha256(binary) if os.path.exists(binary) else None,
            "corpus_untouched": before == after, "corpus_digest": before, "readings": readings}


def main():
    facts = {}
    if os.path.exists(FACTS):
        with open(FACTS, encoding="utf-8") as f:
            facts = json.load(f)
    fix_a = digest(FIX_A)
    fix_d = write_corpus_d()
    arms = {a: run_arm(a, "A", ARMS[a], FIX_A) for a in ARMS}
    for a in ARMS:
        arms[a]["readings_D"] = run_arm(a, "D", ARMS[a], CORPUS_D)["readings"]

    def rd(a, c, q):
        return (arms[a]["readings"] if c == "A" else arms[a]["readings_D"])[q]

    grp_a, grp_d = identical_groups(FIX_A), identical_groups(CORPUS_D)
    n_a, t_a = rd("N", "A", "存在"), rd("T", "A", "存在")
    n_d, t_d = rd("N", "D", "存在"), rd("T", "D", "存在")

    shared_a = [i for i in n_a["hit_ids"] if i in t_a["hit_ids"]]
    checks = {
        "C1": n_a["ranked"] == REG_TREATED_A and n_a["hit_ids"] == [x[0] for x in REG_TREATED_A],
        "C2": t_a["hit_ids"] == ["cli-6bf6dc8d", "probe-0914125816-p004"]
              and "probe-0914125831-p005" not in t_a["hit_ids"]
              and t_a["folded"] == {"probe-0914125816-p004": 1}
              and len(n_a["hit_ids"]) == 3 and len(t_a["hit_ids"]) == 2,
        "C3": t_d["hit_ids"] == n_d["hit_ids"] == ["r428-d1", "r428-d2"] and not t_d["folded"],
        "C4": all(rd("T", c, "存在")["ranked"] == [x for x in rd("N", c, "存在")["ranked"] if x[0] in shared_a or c == "D"]
                  for c in ["D"]) and all(dict(rd("N", "A", "存在")["ranked"])[i] == dict(t_a["ranked"])[i] for i in shared_a),
        "C5": all(r["rc"] == 0 and r["llm_call_points"] == 0 and r["recall_points"] == 1
                  and r["declared"] == len(r["hits"])
                  for a in ARMS for c in ["A", "D"] for r in (arms[a]["readings"] if c == "A" else arms[a]["readings_D"]).values())
              and all(arms[a]["corpus_untouched"] for a in ARMS),
        "C6": bool(facts.get("unit_tests", {}).get("ok")),
        "C7": bool(facts.get("aot", {}).get("ok")) and arms["N"]["binary_sha256"] != arms["T"]["binary_sha256"],
    }
    closed_form = {
        "A_dup_groups": grp_a["groups"], "A_docs": grp_a["docs"],
        "A_keeper_predicted": grp_a["expected_keeper"],
        "A_keeper_observed": [i for i in t_a["hit_ids"] if t_a["folded"].get(i)],
        "D_dup_groups": grp_d["groups"], "D_docs": grp_d["docs"],
        "folded_out_ids": [i for i in n_a["hit_ids"] if i not in t_a["hit_ids"]],
    }
    closed_form["keeper_match"] = closed_form["A_keeper_predicted"] == closed_form["A_keeper_observed"]
    checks["C2b"] = closed_form["keeper_match"] and closed_form["folded_out_ids"] == ["probe-0914125831-p005"]

    verdict = "PASS" if all(checks.values()) else ("UNDECIDABLE" if not checks["C1"] else "FAIL")
    out = {"round": "R428", "verdict": verdict, "checks": checks, "facts": facts,
           "arms": {a: {"binary": arms[a]["binary"], "sha256": arms[a]["binary_sha256"],
                        "A": arms[a]["readings"], "D": arms[a]["readings_D"]} for a in ARMS},
           "fixtures": {"A": {"dir": FIX_A, "sha256": fix_a}, "D": {"dir": CORPUS_D, "sha256": fix_d}},
           "closed_form": closed_form, "registered_anchor_A": REG_TREATED_A}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"verdict": verdict, "checks": checks, "closed_form": closed_form,
                      "N_A": n_a["ranked"], "T_A": t_a["ranked"], "N_D": n_d["ranked"], "T_D": t_d["ranked"]},
                     ensure_ascii=False, indent=2))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
