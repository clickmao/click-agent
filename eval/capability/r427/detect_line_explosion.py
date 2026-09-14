#!/usr/bin/env python3
# R427 行结构检测器: 捕获「逐字符换行」型文档破坏 (行级判读会全部假阴性)
# 用法: python3 detect_line_explosion.py <dir|file> [...]
import sys, os
def scan(p):
    try: t=open(p,encoding="utf-8",errors="replace").read()
    except Exception: return None
    L=t.split(chr(10))
    if len(L)<40: return None
    best=cur=0; at=0
    for i,x in enumerate(L):
        if len(x)<=1: cur+=1
        else:
            if cur>best: best,at=cur,i-cur
            cur=0
    if best>0 and best>=0.5*len(L): return (p,len(L),best,at)
    return None
def walk(a):
    if os.path.isfile(a): 
        r=scan(a); 
        if r: print("BROKEN", r)
        return
    for root,_,fs in os.walk(a):
        if "/.git" in root: continue
        for n in fs:
            if n.endswith((".md",".json",".jsonl",".txt",".cs",".py")): 
                r=scan(os.path.join(root,n))
                if r: print("BROKEN", r)
for a in sys.argv[1:]: walk(a)
print("SCAN_DONE")
