#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q7 · 文档侧定点修复器 (apply_doc_fixes_q7-v1.1.0).

只做两件事, 全部由**产物自身派生** (禁手打字面量):
  A) 改写 `relocated` 引用: 旧路径字面量 -> 唯一候选路径 (仪器读数 JSON 的 relocated_to[0]);
  B) 对 `retired_after_write` 引用补退役标记: 标记文本由仪器模块常量 RETIRED_MARKERS[0] +
     退役提交短 sha (Q6 复核器产物 per_path_stale_truth[*].deletion_sha) 组装;
     插入位置 = 引用 token **(含行号) 之后**, 由仪器自己的 extractor 给出 pos_end 派生, 且在 `]`/`` ` `` 之外。

v1.1.0 修 v1.0.0 的测量层缺陷 D1: 首版按 path 子串 find() 定位, 标记被插进 `path` 与 `:行号` **之间**,
使引用 token 不再被 CITE_RE 匹配 —— 13 条引用**从语料中消失**(桶计数看着变绿, 实为数据销毁)。
修后判据改为**绑定仪器真实行为**: 复跑 extractor + judge_citation, 断言该引用仍被抽取且判为预期档。
另加**计数守恒不变量**: 每个被改文档的引用条数必须逐文档相同 (总条数守恒)。
不修改仪器判据面; 不做全文重排 (行数必须不变); 幂等 (已达标行跳过).
"""
import hashlib
import importlib.util
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
Q7 = REPO / "eval/capability/exp1-q7"
BEFORE = Q7 / "attribution_q7_before.json"
Q6 = REPO / "eval/capability/exp1-q6/attribution_q6_v120.json"
PROBE = REPO / "eval/capability/exp1-q4/probe_doc_ref_integrity.py"
PLAN_OUT = Q7 / "edit_plan.json"


def load_probe():
    spec = importlib.util.spec_from_file_location("probe", str(PROBE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def build_ops(probe):
    marker_word = probe.RETIRED_MARKERS[0]            # 派生, 不手打
    br_open, br_close = chr(0x3010), chr(0x3011)      # 由码位构造, 不手打
    before = json.loads(BEFORE.read_text(encoding="utf-8"))
    q6 = json.loads(Q6.read_text(encoding="utf-8"))
    truth = q6["per_path_stale_truth"]
    reloc = []
    for c in before["relocated_citations"]:
        cands = c.get("relocated_to") or []
        if len(cands) != 1:
            raise SystemExit("非唯一候选, 拒绝改写: %s:%s" % (c["doc"], c["doc_line"]))
        reloc.append({"doc": c["doc"], "line": c["doc_line"], "old": c["path"], "new": cands[0],
                      "fact": c.get("relocated_fact_verdict")})
    marks, excluded = [], []
    for c in before["stale_citations"]:
        if c.get("verdict") != "stale_path":
            continue
        t = truth.get(c["path"]) or {}
        cls = t.get("classes") or {}
        if "retired_after_write" not in cls or "same_commit_as_deletion" in cls:
            # 预注册 H.2 排除项: 同提交类(弃权)与混合类一律零动作
            excluded.append({"doc": c["doc"], "line": c["doc_line"], "path": c["path"], "classes": cls})
            continue
        sha = (t.get("deletion_sha") or "")[:7]
        if not sha:
            raise SystemExit("无删除提交真值, 拒绝补标记: %s" % c["path"])
        marks.append({"doc": c["doc"], "line": c["doc_line"], "path": c["path"],
                      "marker": br_open + marker_word + " " + sha + br_close, "sha": sha})
    return marker_word, reloc, marks, excluded


def _anchor_end(probe, doc, line_no, path, insert_mode="token_end"):
    """引用 token 的插入锚点.

    token_end (默认, 正确): 仪器 extractor 的 pos_end, (+1 若紧跟 `]` 或 `` ` ``) ⇒ 标记落在**完整引用 token 之外**;
    path_end (缺陷复现/负控): 只取路径子串末尾 ⇒ 标记被插进 `path` 与 `:行号` 之间, 破坏 CITE_RE 匹配
      (v1.0.0 实测: 13 条引用从语料消失, 桶计数反而"变绿" ⇒ 该模式专用于**证明计数守恒闸会报红**)。
    """
    text = (REPO / doc).read_text(encoding="utf-8")
    line = text.split("\n")[line_no - 1]
    for c in probe.extract_citations(doc, text):
        if c["doc_line"] == line_no and c["path"] == path:
            if insert_mode == "path_end":
                return c["pos_start"] + len(c["path"])
            end = c["pos_end"]
            if end < len(line) and line[end] in "]`":
                end += 1
            return end
    return None


def apply_ops(probe, reloc, marks, dry=False, insert_mode="token_end"):
    per_doc = {}
    for op in reloc:
        per_doc.setdefault(op["doc"], {"reloc": [], "mark": []})["reloc"].append(op)
    for op in marks:
        per_doc.setdefault(op["doc"], {"reloc": [], "mark": []})["mark"].append(op)
    plan = {"version": "apply_doc_fixes_q7-v1.1.0", "dry_run": dry, "files": [], "n_replace": 0, "n_marker": 0,
            "skipped_idempotent": [], "count_invariant": {}}
    for doc, ops in sorted(per_doc.items()):
        path = REPO / doc
        text = path.read_text(encoding="utf-8")
        before_sha = sha256_text(text)
        n_cites_before = len(probe.extract_citations(doc, text))
        lines = text.split("\n")
        n_before = len(lines)
        rec = {"doc": doc, "sha256_before": before_sha, "edited_lines": [], "n_marker": 0, "n_replace": 0,
               "n_cites_before": n_cites_before}
        for op in ops["reloc"]:
            i = op["line"] - 1
            line = lines[i]
            if op["new"] in line and op["old"] not in line:
                plan["skipped_idempotent"].append("%s:%d" % (doc, op["line"]))
                continue
            n = line.count(op["old"])
            if n == 0:
                raise SystemExit("改写锚点缺失: %s:%d %s" % (doc, op["line"], op["old"]))
            lines[i] = line.replace(op["old"], op["new"])
            plan["n_replace"] += n
            rec["n_replace"] += n
            rec["edited_lines"].append(op["line"])
        # 标记插入: 位置先全部由**原始(改写后)行**的 extractor 派生, 同线多标记按位置降序应用防错位
        todo = []
        for op in ops["mark"]:
            i = op["line"] - 1
            if op["marker"] in lines[i]:
                plan["skipped_idempotent"].append("%s:%d" % (doc, op["line"]))
                continue
            end = _anchor_end(probe, doc, op["line"], op["path"], insert_mode)
            if end is None:
                raise SystemExit("标记锚点缺失: %s:%d %s" % (doc, op["line"], op["path"]))
            todo.append((end, i, op))
        for end, i, op in sorted(todo, key=lambda x: (-x[0], x[1])):
            line = lines[i]
            lines[i] = line[:end] + op["marker"] + line[end:]
            plan["n_marker"] += 1
            rec["n_marker"] += 1
            rec["edited_lines"].append(op["line"])
        out = "\n".join(lines)
        assert len(lines) == n_before, "行数变了: %s" % doc
        if not dry:
            path.write_text(out, encoding="utf-8")
        rec["sha256_after"] = sha256_text(out)
        rec["lines_unchanged"] = len(lines) == n_before
        n_cites_after = len(probe.extract_citations(doc, (REPO / doc).read_text(encoding="utf-8")))
        rec["n_cites_after"] = n_cites_after
        rec["count_ok"] = (n_cites_before == n_cites_after)
        plan["count_invariant"][doc] = [n_cites_before, n_cites_after]
        plan["files"].append(rec)
    return plan


def verify(probe, reloc, marks, repo):
    """读回校验 + **绑定仪器真实行为**: 每条 op 复跑 extractor/judge_citation 判其最终档."""
    bad, verdicts = [], {}
    for op in reloc:
        got = None
        for c in probe.extract_citations(op["doc"], (REPO / op["doc"]).read_text(encoding="utf-8")):
            if c["doc_line"] == op["line"] and c["path"] == op["new"]:
                got = probe.judge_citation(repo, c)
        if got is None:
            bad.append("RELOC-MISSING %s:%d" % (op["doc"], op["line"]))
        elif got["verdict"] not in ("ok", "symbol_absent", "stale_lines", "waived"):
            bad.append("RELOC-VERDICT %s:%d %s" % (op["doc"], op["line"], got["verdict"]))
        else:
            verdicts["%s:%d" % (op["doc"], op["line"])] = got["verdict"]
    for op in marks:
        got = None
        for c in probe.extract_citations(op["doc"], (REPO / op["doc"]).read_text(encoding="utf-8")):
            if c["doc_line"] == op["line"] and c["path"] == op["path"]:
                got = probe.judge_citation(repo, c)
        if got is None:
            bad.append("MARK-MISSING %s:%d" % (op["doc"], op["line"]))
        elif got["verdict"] != "retired":
            bad.append("MARK-VERDICT %s:%d %s" % (op["doc"], op["line"], got["verdict"]))
        else:
            verdicts["%s:%d" % (op["doc"], op["line"])] = got["verdict"]
            expect = chr(0x3010) + probe.RETIRED_MARKERS[0] + " " + op["sha"] + chr(0x3011)
            line = (REPO / op["doc"]).read_text(encoding="utf-8").split("\n")[op["line"] - 1]
            if expect not in line:
                bad.append("MARK-TEXT %s:%d" % (op["doc"], op["line"]))
            if "\u200b" in line:
                bad.append("CHANNEL-REWRITE %s:%d" % (op["doc"], op["line"]))
    return bad, verdicts


def main():
    dry = "--apply" not in sys.argv
    insert_mode = "token_end"
    plan_out = PLAN_OUT
    for a in sys.argv[1:]:
        if a.startswith("--insert-mode="):
            insert_mode = a.split("=", 1)[1]
        elif a.startswith("--plan-out="):
            plan_out = pathlib.Path(a.split("=", 1)[1])
    if insert_mode not in ("token_end", "path_end"):
        raise SystemExit("未知 insert-mode: %s" % insert_mode)
    probe = load_probe()
    marker_word, reloc, marks, excluded = build_ops(probe)
    plan = apply_ops(probe, reloc, marks, dry=dry, insert_mode=insert_mode)
    plan["insert_mode"] = insert_mode
    plan["marker_word"] = marker_word
    plan["retired_window"] = probe.RETIRED_WINDOW
    plan["n_reloc_ops"] = len(reloc)
    plan["n_mark_ops"] = len(marks)
    plan["marker_sample_codepoints"] = [ord(c) for c in marks[0]["marker"]] if marks else []
    plan["unique_docs"] = sorted({o["doc"] for o in reloc} | {o["doc"] for o in marks})
    plan["reloc_fact_verdicts"] = {o["line"]: o["fact"] for o in reloc}
    plan["excluded_stale_path"] = excluded
    plan["total_cites_before"] = sum(v[0] for v in plan["count_invariant"].values())
    plan["total_cites_after"] = sum(v[1] for v in plan["count_invariant"].values())
    repo = probe.Repo(REPO)
    bad, verdicts = verify(probe, reloc, marks, repo)
    plan["verify_verdicts"] = verdicts
    plan["verify_bad"] = bad
    plan["count_invariant_ok"] = all(v[0] == v[1] for v in plan["count_invariant"].values())
    plan_out.write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"dry_run": plan["dry_run"], "insert_mode": plan["insert_mode"],
                      "n_reloc_ops": plan["n_reloc_ops"], "n_mark_ops": plan["n_mark_ops"],
                      "n_replace": plan["n_replace"], "n_marker": plan["n_marker"],
                      "unique_docs_n": len(plan["unique_docs"]), "excluded_n": len(excluded),
                      "total_cites_before": plan["total_cites_before"], "total_cites_after": plan["total_cites_after"],
                      "count_invariant_ok": plan["count_invariant_ok"], "skipped": plan["skipped_idempotent"]},
                     ensure_ascii=False))
    print("verify_bad=%d %s" % (len(bad), bad))
    print("verdict_hist=%s" % json.dumps({v: list(verdicts.values()).count(v) for v in set(verdicts.values())},
                                         ensure_ascii=False))
    ok = (not bad) and plan["count_invariant_ok"]
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
