import io, json, os, re, sys
D = os.path.expanduser("~/.agentframework/harness/runs/r585")
rows = []
for w in ("w154", "w155", "w156"):
    wd = os.path.join(D, w)
    if not os.path.isdir(wd):
        continue
    for sub in sorted(os.listdir(wd)):
        f = os.path.join(wd, sub, "g1", "cases.txt")
        if not os.path.isfile(f):
            continue
        txt = io.open(f, encoding="utf-8", errors="replace").read()
        fails = [l for l in txt.splitlines() if " FAIL" in l]
        kinds = {}
        fams = {}
        for l in fails:
            m = re.match(r"CASE (\S+) FAIL\s*(.*)", l.strip())
            if not m:
                continue
            fam = m.group(1).split("#")[0]
            kinds[m.group(2).strip() or "?"] = kinds.get(m.group(2).strip() or "?", 0) + 1
            fams[fam] = fams.get(fam, 0) + 1
        tot = re.search(r"R521_CASES (\d+)/(\d+)", txt)
        rows.append({"win": w, "sub": sub, "pass": int(tot.group(1)) if tot else None,
                     "total": int(tot.group(2)) if tot else None,
                     "fail_kinds": kinds, "fail_fams": fams})
for r in rows:
    print(json.dumps(r, ensure_ascii=False))
io.open("eval/rover/r585/per-case-failures-r585.json", "w", encoding="utf-8").write(
    json.dumps({"rows": rows}, ensure_ascii=False, indent=1))
