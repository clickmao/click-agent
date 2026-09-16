#!/usr/bin/env python3
"""R481-A 代理面: 【探索】跨文件/跨URL 精准度基线 (语言无关: 只看地址语法, 不看后缀语义)。
诚实边界: 只测"内容自带的地址能否精准落地", 不测产品面(agent.recall)延迟/实现;
URL 离线不可验证 => 单列 external(unreported), 禁当0。"""
import os, re, sys, json, statistics

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SKIP = {".git", "bin", "obj", "node_modules", ".vs", "dist", "artifacts", "__pycache__"}
TEXT_EXT = None  # 语言无关: 靠内容探测, 不靠后缀
MAX_BYTES = 1_000_000

URL_RE = re.compile(r"https?://[^\s\)\]\"'<>，、）]+")
MD_RE = re.compile(r"\[[^\]\n]{0,80}\]\(([^)\s]+)\)")
PATH_RE = re.compile(r"(?<![\w/.-])((?:\.{1,2}/)?(?:[\w.@+-]+/){1,8}[\w.@+-]+\.[A-Za-z0-9]{1,6})")
SAFE_EXT = {"cs","md","json","jsonl","py","js","ts","tsx","jsx","yml","yaml","toml","sh","html","css","txt","sln","csproj","csv","xml","props","targets","sql","ps1","bat"}

def is_text(b: bytes) -> bool:
    if not b or b"\x00" in b[:8192]:
        return False
    sample = b[:4096]
    ctrl = sum(1 for c in sample if c < 9 or (13 < c < 32))
    return ctrl <= max(1, len(sample) // 100)

def collect():
    out = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP and not d.startswith(".git")]
        for fn in fns:
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) > MAX_BYTES:
                    continue
                with open(p, "rb") as f:
                    b = f.read()
            except OSError:
                continue
            if not is_text(b):
                continue
            out.append((os.path.relpath(p, ROOT), b.decode("utf-8", "replace")))
    return out

def main():
    files = collect()
    stats = {"files": len(files), "refs": 0, "resolved": 0, "dangling": 0, "external": 0,
             "rel_refs": 0, "rel_ok": 0, "root_ok": 0, "per_file": [], "dangling_samples": []}
    for rel, txt in files:
        base = os.path.dirname(os.path.join(ROOT, rel))
        seen = set()
        n_here = 0
        for m in list(MD_RE.finditer(txt)) + [None]:
            pass
        cands = [m.group(1) for m in MD_RE.finditer(txt)]
        cands += [m.group(1) for m in PATH_RE.finditer(txt)
                  if m.group(1).rsplit(".", 1)[-1].lower() in SAFE_EXT]
        urls = URL_RE.findall(txt)
        stats["external"] += len(urls)
        for raw in cands:
            t = raw.strip().strip("<>\"'`").split("#")[0].split("?")[0]
            if not t or t.startswith("http") or t in seen:
                continue
            seen.add(t)
            n_here += 1
            stats["refs"] += 1
            is_rel = t.startswith("./") or t.startswith("../") or "/" not in t
            if is_rel:
                stats["rel_refs"] += 1
            full = os.path.normpath(os.path.join(base, t))
            if os.path.exists(full):
                stats["resolved"] += 1
                if is_rel and full.startswith(ROOT):
                    stats["rel_ok"] += 1
                continue
            rootfull = os.path.normpath(os.path.join(ROOT, t.lstrip("./")))
            if os.path.exists(rootfull):
                stats["resolved"] += 1
                stats["root_ok"] += 1
                continue
            stats["dangling"] += 1
            if len(stats["dangling_samples"]) < 5:
                stats["dangling_samples"].append(f"{rel} -> {t}")
        stats["per_file"].append(n_here)
    pf = stats["per_file"]
    res_rate = stats["resolved"] / max(1, stats["refs"])
    dang_rate = stats["dangling"] / max(1, stats["refs"])
    p50 = statistics.median(pf) if pf else 0
    print(json.dumps({
        "files": stats["files"], "refs": stats["refs"],
        "resolved_rate": round(res_rate, 4), "dangling_rate": round(dang_rate, 4),
        "rel_refs": stats["rel_refs"], "rel_ok_rate": round(stats["rel_ok"] / max(1, stats["rel_refs"]), 4),
        "root_fallback_ok": stats["root_ok"],
        "external_urls_unreported": stats["external"],
        "per_file_p50_refs": p50, "per_file_mean": round(sum(pf) / max(1, len(pf)), 2),
        "files_with_0_refs_rate": round(sum(1 for x in pf if x == 0) / max(1, len(pf)), 4),
        "dangling_samples": stats["dangling_samples"],
        "G1": res_rate >= 0.90, "G2": dang_rate <= 0.35, "G3": (stats["rel_ok"] / max(1, stats["rel_refs"])) >= 0.85,
        "G4": p50 >= 1,
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
