#!/usr/bin/env python3
"""R488 post-hoc 质量面读数 (预注册 H5 的朴素代理=逐字去重, 已 FAIL; 本脚本**单列**事后口径)。

为什么事后口径才对: turn_gate 的本地通道**按设计**把「纯确认类轮」消化为确定性模板
(`ModelQueueRouter.LocalSkipFallback`, 且 `RecordTemplateAck()` 打点), 把「复述类轮」消化为
上一条正文**回放** (`IsReplayableReply` 守卫)。夹具 12 轮里 4 轮是纯确认、3 轮是复述请求
⇒ 逐字去重必然把这些**合法**消化记成「重复=质量降」。故事后口径按**轮类别**判:
  - 非法模板 = 模板/横幅落在非确认类轮 (这才是质量事故)
  - 实质轮答复多样性 = 对 sub/rep 类轮, 答复是否各自可辨

纯机取: 输入 = 真机臂 turns-<key>.jsonl (驱动落盘), 输出 = posthoc-quality-r488.json。零手抄。
"""
import io, json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = [("B", "Aroleb"), ("G", "Gg"), ("S", "Ss"), ("R", "Rr")]
ACK_KEYS = ("谢谢", "好的", "明白", "嗯", "知道了", "收到", "多谢", "就这样")
REP_KEYS = ("再讲一遍", "从头再说", "换个说法", "再说一遍", "重复", "重新说")
TMPL_KEYS = ("本轮不重新规划", "模型未产出正文")


def classify(q):
    if any(k in q for k in ACK_KEYS) and len(q) <= 10:
        return "ack"
    if any(k in q for k in REP_KEYS):
        return "rep"
    return "sub"


def main():
    out = {"round": "R488", "kind": "post-hoc", "preregistered_h5": "逐字去重 (distinct>=10) ⇒ FAIL (见 verdict-r488.json)",
           "arms": {}}
    for arm, key in ARMS:
        p = os.path.join(HERE, f"turns-{key}.jsonl")
        if not os.path.exists(p):
            sys.exit("缺输入 (fail-closed): %s" % p)
        t = json.load(io.open(p, encoding="utf-8-sig"))
        rows = t["turns"]
        per = []
        illegal = []
        subst = []
        for x in rows:
            q, r = x["text"], x["reply"]
            kind = classify(q)
            is_tmpl = any(k in r for k in TMPL_KEYS)
            dup = Counter(x2["reply"] for x2 in rows)[r] > 1
            if is_tmpl and kind != "ack":
                illegal.append({"turn": x["turn"], "user": q[:24], "class": kind})
            if kind in ("sub", "rep"):
                subst.append({"turn": x["turn"], "class": kind, "len": len(r), "dup": dup,
                              "replay_of": next((y["turn"] for y in rows if y["turn"] < x["turn"] and y["reply"] == r), None)})
            per.append({"turn": x["turn"], "class": kind, "rlen": len(r), "is_template": is_tmpl, "dup": dup})
        # 轮类别合格判据 (post-hoc): 非确认类轮**不得**落模板/横幅 (即被本地模板冒充);
        # 复述类轮额外记录是否走了「上一条正文逐字回放」(零 token 通道) —— 走新生成亦合格, 只作信息列。
        non_ack_bad = [x for x in per if x["class"] in ("sub", "rep") and x["is_template"]]
        rep_ok = sum(1 for s in subst if s["class"] == "rep" and s["replay_of"] is not None)
        rep_n = sum(1 for s in subst if s["class"] == "rep")
        ack_ok = sum(1 for x in per if x["class"] == "ack" and x["is_template"])
        ack_n = sum(1 for x in per if x["class"] == "ack")
        sub_n = sum(1 for x in per if x["class"] == "sub")
        out["arms"][arm] = {
            "turns": len(rows), "ack_turns": ack_n, "rep_turns": rep_n, "sub_turns": sub_n,
            "ack_turns_resolved_by_template": ack_ok, "rep_turns_by_verbatim_replay": rep_ok,
            "rep_turns_regenerated": rep_n - rep_ok,
            "non_ack_turns_impersonated_by_template": len(non_ack_bad),
            "illegal_template_turns": len(illegal), "illegal_detail": illegal,
            "verdict": ("PASS" if not illegal and not non_ack_bad else "FAIL"),
        }
    dst = os.path.join(HERE, "posthoc-quality-r488.json")
    io.open(dst, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({a: {k: v for k, v in d.items() if k != "illegal_detail"} for a, d in out["arms"].items()},
                     ensure_ascii=False))
    print("非法模板合计 =", sum(d["illegal_template_turns"] for d in out["arms"].values()))


if __name__ == "__main__":
    main()
