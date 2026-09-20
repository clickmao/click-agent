#!/usr/bin/env python3
"""R592 探查: 精确量出 v1 定因器「冷集比较域」的真实缺陷（先量再改）。"""
import importlib.util, io, json, os, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
REPO="/home/agentuser/AgentFramework"; SRC562=f"{REPO}/eval/rover/r562/wythoff_cause_r562.py"
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
m562=load(SRC562,"w562")
cases=json.load(io.open(f"{REPO}/eval/rover/r591/cases/cases-r521.json",encoding="utf-8"))
ora=m562.build_oracle(cases)
print("oracle cold_n:",len(ora["cold"]))
print("oracle cold (sorted):",sorted(ora["cold"]))
L=25
c_true={p for p in ora["cold"] if max(p)<=L}
print("c_true (max<=L): n=%d"%len(c_true), sorted(c_true))
WIN=re.compile(r"^WIN\s+(\d+)\s+(\d+)\s*$")
def run(tree,stdin,timeout=15):
    env={"PATH":"/usr/local/bin:/usr/bin:/bin","LANG":"C.UTF-8","HOME":tree,"PYTHONPATH":tree,"PYTHONDONTWRITEBYTECODE":"1"}
    p=subprocess.Popen([sys.executable,"-B","-m","games","wythoff"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=tree,env=env,start_new_session=True)
    try:
        o,e=p.communicate(stdin,timeout=timeout); return o,p.returncode
    except subprocess.TimeoutExpired:
        try: os.killpg(os.getpgid(p.pid),9)
        except Exception: pass
        return "",124
tmp=tempfile.mkdtemp(prefix="r592probe-")
src=f"{REPO}/eval/rover/r591/snapshots/w166/agentD-r1/g1"
tree=os.path.join(tmp,"t"); shutil.copytree(src,tree)
pos=[(a,b) for a in range(0,L+1) for b in range(a,L+1)]
def one(p):
    o,rc=run(tree,"%d %d\n"%p,10); return p,o.strip()[:60],rc
with ThreadPoolExecutor(max_workers=8) as ex: res=list(ex.map(one,pos))
c_prod=set(); errs=[]; weird=[]
for p,raw,rc in res:
    m=WIN.match(raw)
    if m: weird.append((p,int(m.group(1)),int(m.group(2))))
    elif raw=="LOSE": c_prod.add(p)
    else: errs.append((p,raw,rc))
print("grid positions:",len(pos),"| LOSE(=c_prod) n=%d | WIN-with-move n=%d | ERROR n=%d"%(len(c_prod),len(weird),len(errs)))
print("c_prod sorted:",sorted(c_prod))
print("only_prod:",sorted(c_prod-c_true))
print("only_true:",sorted(c_true-c_prod))
print("sample ERRORs:",errs[:5])
print("sample moves:",weird[:5])
# 例级: 15 条 wythoff 用例
wy=[c for c in cases if c["game"]=="wythoff"]; o2={"cold":ora["cold"],"lexmin":ora["lexmin"]}
bad=[]
for i,c in enumerate(wy):
    got,rc=run(tree,c["stdin"],60)
    cls,det=m562.classify(c,got,rc,o2)
    if cls!="OK": bad.append((i,c["stdin"].strip(),cls,det,got.strip()[:40]))
print("case-level failures:",len(bad))
for x in bad: print("   ",x)
shutil.rmtree(tmp,ignore_errors=True)
