#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R553 KPI 表: 行 = 本轮三臂 + codex 外部真值(同题面同夹具, R547 落盘) + R552 追溯回算。"""
import io, json, os, sys
REPO="/home/agentuser/AgentFramework"; HERE=os.path.join(REPO,"eval/rover/r553")
rd=lambda p: json.load(io.open(p,encoding="utf-8-sig"))
r=rd(os.path.join(HERE,"readings-r553.json"))
ret=rd(os.path.join(HERE,"readings-r552-retro.json"))
co=rd(os.path.join(REPO,"eval/rover/r547/posthoc-codex-g1/summary.json"))
rows=[]
def hit_from(p,c):
    return None if not p else (c/p if p else None)
for arm in ("R553b0","R553b1","R553b2"):
    s=r["summary"].get(arm)
    if not s: rows.append({"arm":arm,"status":"未测"}); continue
    hr=r["hitrate"].get(arm,{}).get("rows",[])
    vals=[x for x in hr if x.get("status")=="ok"]
    va=sum(x.get("v_all",0) for x in vals)/len(vals) if vals else None
    vi=[x.get("v_incr") for x in vals if x.get("v_incr") is not None]
    rows.append({"arm":arm,"dose":arm[-1],"windows":s["windows"],"quality":s["quality"],
        "median":s["median"],"range":s["range"],"n_valid":s["n_valid"],"n_valid_old_rule":s["n_valid_old_rule"],
        "calls":s["calls_sum"],"new_prompt":s["new_prompt_sum"],"completion":s["completion_sum"],
        "v_all":va,"v_incr":(sum(vi)/len(vi) if vi else None),"per_window":s["per_window"]})
for x in co:
    if x.get("side")=="codex":
        p,c=x.get("prompt"),x.get("cached")
        rows.append({"arm":"codex(外部真值, R547 同题面同夹具)","win":x.get("win"),"quality":"%d/%d"%(x["pass"],x["total"]),
            "calls":x.get("calls"),"new_prompt":(p-c) if p is not None else None,"prompt":p,"cached":c,
            "completion":x.get("completion"),"v_all":hit_from(p,c)})
for x in co:
    if x.get("side")=="R1":
        p,c=x.get("prompt"),x.get("cached")
        rows.append({"arm":"R1@R547(与 codex 同窗)","win":x.get("win"),"quality":"%d/%d"%(x["pass"],x["total"]),
            "calls":x.get("calls"),"new_prompt":(p-c) if p is not None else None,"prompt":p,"cached":c,
            "completion":x.get("completion"),"v_all":hit_from(p,c)})
for arm in ("R552b0","R552b1","R552b2"):
    s=ret["summary"].get(arm)
    if s: rows.append({"arm":arm+" (追溯回算, 零远端调用)","quality":s["quality"],"median":s["median"],
        "range":s["range"],"n_valid":s["n_valid"],"n_valid_old_rule":s["n_valid_old_rule"],"windows":s["windows"]})
out={"round":"R553","hit_rule":"v_all=1-Smiss/Sprompt(中继 dump 时间轴, 逐窗平均) / v_incr=仅增量",
     "rows":rows,"precheck_confusion":r.get("precheck_confusion"),
     "voidrule_selfcheck":rd(os.path.join(HERE,"voidrule_selfcheck.json")),
     "codex_note":"codex 行 = R547 posthoc-codex-g1 落盘真值(同题面 g1 / 同 58 用例夹具); 非同窗 ⇒ 只作对照行, 跨轮禁相减"}
io.open(os.path.join(HERE,"kpi-table-r553.json"),"w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=1))
for x in rows:
    print(x.get("arm"), "|", x.get("quality") or x.get("status"), "| med", x.get("median"), "| rg", x.get("range"),
          "| nv", x.get("n_valid"), "(旧", x.get("n_valid_old_rule"), ") | calls", x.get("calls"),
          "| new", x.get("new_prompt"), "| comp", x.get("completion"),
          "| v_all", ("%.3f"%x["v_all"]) if x.get("v_all") is not None else None)
print("起手闸C:", json.dumps(r.get("precheck_confusion"),ensure_ascii=False)[:300])
