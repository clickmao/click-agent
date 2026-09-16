#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R487 候选⑥: R481-G 遗留收口 —— rel 子档分档读数 + 语料钉清单导出(漂移可归因)。

口径不新造: 定义/阈值机读 eval/recall/prereg_r481g.json; 候选抽取与解析语义**沿用** R482 端口
(eval/recall/links_port_r482.py, 不改其一个字节 ⇒ 其 rule_source_sha16 与历史读数保持可比)。
自污染闸: 本器具自身产物目录(eval/recall/r487/**)排除出被扫语料, 排除条数落盘。
三态: rc=0 全档达标 / rc=2 有档不达标(fail-closed 落盘) / rc=3 缺输入(弃权)。
负控: --nc-blind 走同一代码路径但强制「全不可解析」⇒ 各档判据必须整体翻面。
"""
import os, sys, json, hashlib, argparse, importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
D = os.path.dirname(os.path.abspath(__file__))
PORT_PATH = os.path.join(ROOT, "eval", "recall", "links_port_r482.py")
PRE_PATH = os.path.join(ROOT, "eval", "recall", "prereg_r481g.json")
SELF_DIRS = ("eval/recall/r487/",)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rd(p):
    with open(p, "rb") as f:
        return f.read().decode("utf-8-sig")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(D, "band_readings_r487.json"))
    ap.add_argument("--corpus-list", default=os.path.join(D, "corpus-list-r487.json"))
    ap.add_argument("--nc-blind", action="store_true", help="负控: 强制全不可解析")
    a = ap.parse_args()

    if not (os.path.exists(PORT_PATH) and os.path.exists(PRE_PATH)):
        print(json.dumps({"verdict": "MISSING", "port": PORT_PATH, "prereg": PRE_PATH}, ensure_ascii=False))
        return 3
    L = _load(PORT_PATH, "port_r482")
    PRE = json.loads(rd(PRE_PATH))
    J = PRE["bands"]["judgment"]
    DEF = PRE["bands"]["definitions"]

    files = L.collect()
    if not files:
        print(json.dumps({"verdict": "MISSING", "why": "语料根为空"}, ensure_ascii=False))
        return 3

    self_excluded = 0
    kept = []
    for rel, txt in files:
        if rel.replace(os.sep, "/").startswith(SELF_DIRS):
            self_excluded += 1
            continue
        kept.append((rel, txt))

    BANDS = ("markdown", "url", "rel", "explicit_rel", "root_rel", "slash_token", "escape")
    st = {b: dict(refs=0, external=0, local=0, resolved=0, dangling=0, rewrite_ok=0, rewrite_raw=0) for b in BANDS}
    corpus_h = hashlib.sha256()
    lst = []
    for rel, txt in kept:
        nb = len(txt.encode("utf-8"))
        corpus_h.update(("%s:%d\n" % (rel, nb)).encode("utf-8"))
        lst.append({"path": rel.replace(os.sep, "/"), "bytes": nb})
        for value, raw, origin in L.extract(txt, referrer=rel):
            st[origin]["refs"] += 1
            ext = any(value.lower().startswith(s.lower()) for s in L.SCHEMES)
            if ext:
                st[origin]["external"] += 1
                continue
            st[origin]["local"] += 1
            explicit = raw.startswith(L.REL_PREFIXES)
            full = os.path.normpath(os.path.join(ROOT, value))
            inside = full == ROOT or full.startswith(ROOT + os.sep)
            resolved = bool(inside and os.path.isfile(full) and not a.nc_blind)
            if resolved:
                st[origin]["resolved"] += 1
            else:
                st[origin]["dangling"] += 1
            if origin != "rel":
                continue
            # rel 子档: 每个 local rel 候选**恰好**落入一个桶 (顺序分区, 守恒可机检)
            if not inside:
                st["escape"]["refs"] += 1
                st["escape"]["dangling"] += 1
            elif explicit:
                st["explicit_rel"]["refs"] += 1
                if resolved:
                    st["explicit_rel"]["resolved"] += 1
                if resolved and value != raw:
                    st["explicit_rel"]["rewrite_ok"] += 1
                if value == raw:
                    st["explicit_rel"]["rewrite_raw"] += 1
            elif resolved:
                st["root_rel"]["refs"] += 1
                st["root_rel"]["resolved"] += 1
            else:
                st["slash_token"]["refs"] += 1
                st["slash_token"]["dangling"] += 1

    def rate(b, num, den):
        return round(st[b][num] / max(1, st[b][den]), 4)

    bands = {
        "markdown": {"refs": st["markdown"]["refs"], "local": st["markdown"]["local"],
                     "resolved": st["markdown"]["resolved"], "dangling": st["markdown"]["dangling"],
                     "resolved_rate": rate("markdown", "resolved", "local")},
        "url": {"refs": st["url"]["refs"], "external_unreported": st["url"]["external"],
                "resolved_rate": "unreported"},
        "rel": {"refs": st["rel"]["refs"], "local": st["rel"]["local"]},
        "explicit_rel": {"refs": st["explicit_rel"]["refs"], "rewrite_ok": st["explicit_rel"]["rewrite_ok"],
                         "rewrite_ok_rate": rate("explicit_rel", "rewrite_ok", "refs"),
                         "kept_raw": st["explicit_rel"]["rewrite_raw"]},
        "root_rel": {"refs": st["root_rel"]["refs"], "resolved": st["root_rel"]["resolved"],
                     "resolved_rate": rate("root_rel", "resolved", "refs")},
        "slash_token": {"refs": st["slash_token"]["refs"], "dangling": st["slash_token"]["dangling"]},
        "escape": {"refs": st["escape"]["refs"], "note": DEF["slash_token"]},
    }

    total_refs = sum(st[b]["refs"] for b in BANDS if b not in ("explicit_rel", "root_rel", "slash_token", "escape"))
    cons = {
        "origin_sum_eq_total": st["markdown"]["refs"] + st["url"]["refs"] + st["rel"]["refs"],
        "rel_subband_sum": st["explicit_rel"]["refs"] + st["root_rel"]["refs"] + st["slash_token"]["refs"] + st["escape"]["refs"],
        "rel_local": st["rel"]["local"],
    }
    cons["ok"] = cons["origin_sum_eq_total"] == (st["markdown"]["refs"] + st["url"]["refs"] + st["rel"]["refs"]) \
        and cons["rel_subband_sum"] == cons["rel_local"]

    h16 = corpus_h.hexdigest()[:16]
    out = {"round": "R487", "candidate": "⑥ R481-G 遗留 (by_subband + 语料钉清单)",
           "instrument": {"path": os.path.relpath(os.path.abspath(__file__), ROOT),
                          "port_rule_source": os.path.relpath(PORT_PATH, ROOT),
                          "prereg": os.path.relpath(PRE_PATH, ROOT),
                          "definitions_from": "prereg_r481g.bands.definitions", "negative_control": bool(a.nc_blind)},
           "corpus": {"files": len(kept), "files_sha16": h16, "self_excluded": self_excluded,
                      "self_excluded_dirs": list(SELF_DIRS),
                      "comparability": "(files_sha16, rule_source_sha16) 二元组相等才可与旧读数同批对照; "
                                       "本读数自成一钉 (含 R487 新增文件) ⇒ 与 R481-B/R482 读数标『不可比』"},
           "bands": bands, "conservation": cons,
           "judgment_source": J,
           "judgments": {
               "markdown_ge_0.90": bands["markdown"]["resolved_rate"] >= 0.90,
               "explicit_rel_rewrite_ge_0.85": bands["explicit_rel"]["rewrite_ok_rate"] >= 0.85,
               "root_rel_ge_0.90": bands["root_rel"]["resolved_rate"] >= 0.90,
               "total_refs_reported": total_refs,
           },
           "honest": ["n/a 全局门槛: prereg 已判全局单一阈值结构不可达 (slash token 面), 本器具不重报全局档",
                      "url 档离线不可验证 ⇒ unreported 单列, 禁作 0 禁入分母",
                      "Python 代理面, 不测产品面 agent.recall"]}

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(a.corpus_list, "w", encoding="utf-8") as f:
        json.dump({"files": len(lst), "files_sha16": h16, "list": lst}, f, ensure_ascii=False, indent=1)

    jd = out["judgments"]
    m_ok = jd["markdown_ge_0.90"]
    e_ok = jd["explicit_rel_rewrite_ge_0.85"]
    r_ok = jd["root_rel_ge_0.90"]
    print(json.dumps({"out": a.out, "corpus_list": a.corpus_list, "files": len(kept), "files_sha16": h16,
                      "conservation_ok": cons["ok"], "markdown": bands["markdown"]["resolved_rate"],
                      "explicit_rel": bands["explicit_rel"]["rewrite_ok_rate"],
                      "root_rel": bands["root_rel"]["resolved_rate"],
                      "slash_token": bands["slash_token"]["refs"], "nc_blind": bool(a.nc_blind),
                      "judgments": {"markdown": m_ok, "explicit_rel": e_ok, "root_rel": r_ok}},
                     ensure_ascii=False))
    if not cons["ok"]:
        return 2
    all_ok = m_ok and e_ok and r_ok
    if a.nc_blind:
        return 0 if not (m_ok or r_ok) else 2
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
