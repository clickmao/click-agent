#!/usr/bin/env python3
"""R418 复盘: 用归档回复离线复判 p002，取出**具体失分用例**（防「失分原因」写错）。"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
sys.path.insert(0, str(ROOT / "eval/probe"))
import tasks as taskgen  # noqa: E402
import grade as G  # noqa: E402

rnd = random.Random(20260916)
raw = [json.loads(taskgen.gen_program_task(i, ["json_mini"], rnd).to_json()) for i in (1, 2, 3)]
print("replay tids=%s" % [t["tid"] for t in raw])
d = json.loads((ROOT / "data/probe/probe-r418-agent.json").read_text(encoding="utf-8"))
by_tid = {t["tid"]: t for t in raw}
for t in d["per_task"]:
    tid = t["tid"]
    rep = (ROOT / t["solve"]["reply_path"]).read_text(encoding="utf-8", errors="replace")
    if tid not in by_tid:
        print("%s SKIP (replay 未生成该 tid ⇒ 不可离线复判)" % tid)
        continue
    g = G.grade_program(by_tid[tid], rep, timeout=5.0)
    bad = [x for x in g.get("detail", []) if x.get("verdict") != "ok"]
    print("%s mode=%s %d/%d tax=%s reply_chars=%d" % (tid, g["mode"], g["passed"], g["total"], g["taxonomy"], len(rep)))
    for x in bad:
        print("   FAIL case#%s verdict=%s" % (x.get("case"), x.get("verdict")))
        print("     got=%r" % (str(x.get("got"))[:200],))
        print("     want=%r" % (str(x.get("want"))[:200],))
print("by_family=%s" % json.dumps(d["by_family"], ensure_ascii=False))
