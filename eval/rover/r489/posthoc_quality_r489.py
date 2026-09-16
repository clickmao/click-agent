#!/usr/bin/env python3
"""R489 质量面读数 (post-hoc 单列; 预注册 H5 = 逐字去重口径的替代口径, 见 prereg_r489.json)。

与 R488 版的两个差别:
  1. **判据只读产品自身遥测** (`local_turn_gate` 的 verdict/basis + `local_gate_skip_reply` 的 kind/chars),
     不再手抄「确认族关键词」——类别归属由被测组件自己给出。
  2. **模板文案绑源码** (R489 裁决: `LocalSkipFallback` → 纯确认句):
     逐位取 `src/.../ModelQueueRouter.cs` 里的常量文本 + `LocalGenerationPort.cs` 的 `AckFamilyChars`,
     断言 (a) 模板字符集 ⊆ 认可族字符集 (模板永远不能声称做了事);
          (b) 每条 kind=template 遥测的 chars == 源码常量长度 (证明被测二进制就是这份源码)。
零手抄; 缺任一输入 ⇒ rc=3 (fail-closed)。
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ROUTER = os.path.join(REPO, "src", "agent.modelqueue", "ModelQueueRouter.cs")
GENPORT = os.path.join(REPO, "src", "agent.modelqueue", "LocalGenerationPort.cs")
ARMS = [("B", "Aroleb"), ("R1", "R1"), ("R2", "R2"), ("R3", "R3")]
ALLOWED_SKIP_BASIS = {"gate:skip→local", "mechanical:repeat→local"}
TEMPLATE_BASIS = "gate:skip→local"


def derive_const(path, name):
    src = io.open(path, encoding="utf-8").read()
    m = re.search(r'const\s+string\s+' + re.escape(name) + r'\s*=\s*"((?:[^"\\]|\\.)*)"\s*;', src)
    if not m:
        sys.exit("源码派生失败 (fail-closed): %s / %s" % (path, name))
    return m.group(1)


def rows(path):
    out = []
    for line in io.open(path, encoding="utf-8-sig"):
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def main():
    template = derive_const(ROUTER, "LocalSkipFallback")
    ack_family = derive_const(GENPORT, "AckFamilyChars")
    out = {
        "round": "R489", "kind": "post-hoc (telemetry-driven + source-bound)",
        "preregistered_h5": "见 prereg_r489.json H3/H5 (类别感知; 逐字去重口径已废)",
        "source_derived": {"LocalSkipFallback": template, "template_chars": len(template),
                          "AckFamilyChars": ack_family},
        "template_source_checks": [], "arms": {},
    }
    # (a) 模板字符集 ⊆ 认可族字符集 ⇒ 模板不可能声称做了事
    bad = [ch for ch in template if not ch.isspace() and ch not in ack_family
           and not (ch in "。，、！？,.!?")]
    out["template_source_checks"].append({
        "id": "SRC1", "desc": "模板每个非标点字符 ⊂ 认可族字符集 (R434 AckFamilyChars)",
        "ok": not bad, "detail": f"越界字符={bad}"})
    # (b) 模板不得含动作/承诺词 (机检, 词表来自 R489 裁决记录)
    promise = [w for w in ("继续", "推进", "规划", "安排", "已", "正在", "将") if w in template]
    out["template_source_checks"].append({
        "id": "SRC2", "desc": "模板不含动作/承诺词 (R489 文案裁决)",
        "ok": not promise, "detail": f"命中={promise}"})

    for arm, key in ARMS:
        p = os.path.join(HERE, f"tel-{key}", "host.jsonl")
        if not os.path.exists(p):
            sys.exit("缺输入 (fail-closed): %s" % p)
        cur = None
        gates, skips, bad_pairs = [], [], []
        for r in rows(p):
            pt = r.get("point")
            kv = r.get("kv") or {}
            if pt == "local_turn_gate":
                cur = {"verdict": kv.get("verdict"), "basis": kv.get("basis"), "reply": None}
                gates.append(cur)
            elif pt == "local_gate_skip_reply":
                rec = {"kind": kv.get("kind"), "chars": int(kv.get("chars") or 0)}
                skips.append(rec)
                if cur is not None:
                    cur["reply"] = rec
                    if rec["kind"] == "template" and cur.get("basis") != TEMPLATE_BASIS:
                        bad_pairs.append({"basis": cur.get("basis"), "kind": rec["kind"]})
        skip_rows = [g for g in gates if g.get("verdict") == "Skip"]
        bad_basis = [g.get("basis") for g in skip_rows if g.get("basis") not in ALLOWED_SKIP_BASIS]
        tmpl = [s for s in skips if s["kind"] == "template"]
        chars_ok = all(s["chars"] == len(template) for s in tmpl)
        out["arms"][arm] = {
            "gate_rows": len(gates), "skip_rows": len(skip_rows), "pass_rows": len(gates) - len(skip_rows),
            "skip_replies": len(skips), "template_replies": len(tmpl),
            "repeat_verbatim_replies": sum(1 for s in skips if s["kind"] == "repeat_verbatim"),
            "template_chars_ok": chars_ok,
            "template_chars_seen": sorted({s["chars"] for s in tmpl}),
            "skip_basis_hist": {b: sum(1 for g in skip_rows if g.get("basis") == b) for b in
                                sorted({g.get("basis") for g in skip_rows})},
            "illegal_template_pairing": bad_pairs,
            "illegal_skip_basis": bad_basis,
            "verdict": "PASS" if (not bad_pairs and not bad_basis and chars_ok) else "FAIL",
        }

    dst = os.path.join(HERE, "posthoc-quality-r489.json")
    io.open(dst, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"source_derived": out["source_derived"], "checks": out["template_source_checks"],
                      "arms": {a: {k: v for k, v in d.items() if not k.startswith("illegal")}
                               for a, d in out["arms"].items()}}, ensure_ascii=False, indent=1))
    print("[written]", dst)
    anyfail = (not all(c["ok"] for c in out["template_source_checks"])) or \
              any(d["verdict"] != "PASS" for d in out["arms"].values())
    sys.exit(1 if anyfail else 0)


if __name__ == "__main__":
    main()
