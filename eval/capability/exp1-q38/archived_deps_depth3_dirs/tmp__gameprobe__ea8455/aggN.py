
import json, glob, os
rows={}
import sys
PREF=sys.argv[1] if len(sys.argv)>1 else "r374"
for arm in ("A","B"):
    for i in (1,2,3):
        p=f"/tmp/gameprobe/{PREF}_{arm}_run{i}.telemetry"
        if not os.path.exists(p): continue
        calls=0; toks=0; runs={}; arts=[]; fb=[]
        for ln in open(p,encoding="utf-8-sig"):
            ln=ln.strip()
            if not ln: continue
            o=json.loads(ln); pt=o.get("point"); kv=o.get("kv",{})
            if pt=="llm_call":
                calls+=1; toks+=int(kv.get("total_tokens") or kv.get("tokens") or 0)
            elif pt=="script_run":
                runs[kv.get("path")]=kv
            elif pt=="script_artifact":
                arts.append(kv)
            elif pt=="artifact_feedback":
                fb.append(kv)
        for a in arts:
            r=runs.get(a.get("path"))
            a["ran"]= None if r is None else r.get("ran")
            a["run_exit"]= None if r is None else r.get("exit")
            a["valid"]= bool(a.get("compile_valid")) and (r is None or (r.get("ran") and r.get("exit")==0) or not r.get("ran"))
        rows[(arm,i)]=dict(calls=calls,tokens=toks,arts=arts,fb=fb,
                           final_valid=(arts[-1]["valid"] if arts else None))
for k in sorted(rows, key=lambda x:(x[0],x[1])):
    v=rows[k]
    print(f"[{k[0]}] run{k[1]}: calls={v['calls']} tokens={v['tokens']} arts={len(v['arts'])} final_valid={v['final_valid']} fb={[(f['fixed'],f['error_kind'],f['tokens']) for f in v['fb']]}")
    for a in v["arts"]:
        print(f"      {os.path.basename(a['path'])} compile={a['compile_valid']} ran={a['ran']} run_exit={a['run_exit']} -> {'PASS' if a['valid'] else 'FAIL'}")
import sys
PREF=sys.argv[1] if len(sys.argv)>1 else "r374"
for arm in ("A","B"):
    ks=[k for k in rows if k[0]==arm]
    c=sum(rows[k]['calls'] for k in ks); t=sum(rows[k]['tokens'] for k in ks)
    fv=sum(1 for k in ks if rows[k]['final_valid']); fx=sum(len([f for f in rows[k]['fb'] if f['fixed']]) for k in ks)
    trg=sum(len(rows[k]['fb']) for k in ks)
    print(f"== {arm}: runs={len(ks)} calls={c} (mean {c/len(ks):.2f}) tokens={t} 最终交付有效={fv}/{len(ks)} 触发回流={trg} 修复成功={fx}")
json.dump({f"{k[0]}{k[1]}":v for k,v in rows.items()}, open(f"/tmp/gameprobe/{PREF}_agg.json","w"), ensure_ascii=False, indent=1)
print("saved", f"/tmp/gameprobe/{PREF}_agg.json")
