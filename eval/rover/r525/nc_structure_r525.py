#!/usr/bin/env python3
"""R525 结构锁负控 (NC) —— 注入缺陷必红, 证明机检有判别力 (不是恒绿)。

用法: python3 eval/rover/r525/nc_structure_r525.py
期望: 末行 NC_PANEL_PASS ; 任一项不符 ⇒ rc=1。

正控 = w3 原始转储 (已有 rc=0 记录);
NC1 段序错乱 (§2 与 §3 互换)      ⇒ S1 (段序) 必红
NC2 前缀塞遥测 (data/prompt_audit) ⇒ M2 (无遥测) 必红
NC3 常量材料回灌 user 轮 ([技能知识参考]) ⇒ M6/S5 必红
NC4 删段 (§7 整段)                 ⇒ S1/S2 必红
"""
import io, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CHK = os.path.join(ROOT, "eval", "rover", "r525", "structure_check_r525.py")
SRC = os.path.join(ROOT, "eval", "rover", "r525", "run-0917-r525-w3", "adapter", "full-agent-003.json")


def load():
    return json.load(io.open(SRC, encoding="utf-8"))


def sys_idx(msgs):
    for i, m in enumerate(msgs):
        if m.get("role") == "system":
            return i
    raise SystemExit("no system message")


def sys_text(m):
    c = m.get("content")
    return c if isinstance(c, str) else "".join(x.get("text", "") for x in c)


def set_sys(msgs, i, text):
    m = msgs[i]
    if isinstance(m.get("content"), str):
        m["content"] = text
    else:
        m["content"] = [{"type": "text", "text": text}]
    return msgs


def mutate(tag, fn):
    msgs = load()
    i = sys_idx(msgs)
    fn(msgs, i)
    d = tempfile.mkdtemp(prefix="nc_" + tag + "_")
    json.dump(msgs, io.open(os.path.join(d, "full-agent-003.json"), "w", encoding="utf-8"), ensure_ascii=False)
    # 机检器从 side-*.json 枚举调用 (usage), 故必须同目录配对
    side_src = os.path.join(os.path.dirname(SRC), "side-agent-003.json")
    if os.path.exists(side_src):
        shutil.copy(side_src, os.path.join(d, "side-agent-003.json"))


def run_checker(d):
    out = os.path.join(d, "chk.json")
    p = subprocess.run([sys.executable, CHK, "--adapter-dir", d,
                        "--range", "A1-on=3,3", "--treatment", "A1-on", "--out", out],
                       capture_output=True, text=True)
    v = {}
    if os.path.exists(out):
        v = json.load(io.open(out, encoding="utf-8")).get("verdict", {})
    return p.returncode, v


def nc1(msgs, i):  # 段序错乱: §2 与 §3 互换
    t = sys_text(msgs[i])
    import re
    m2 = re.search(r"## §2 .*?(?=## §3 )", t, re.S)
    m3 = re.search(r"## §3 .*?(?=## §4 )", t, re.S)
    if not (m2 and m3):
        raise SystemExit("NC1 定位失败")
    t2 = t[:m2.start()] + m3.group(0) + m2.group(0) + t[m3.end():]
    set_sys(msgs, i, t2)


def nc2(msgs, i):  # 前缀塞遥测
    set_sys(msgs, i, "[工作区文件 data/prompt_audit.jsonl]\n" + sys_text(msgs[i]))


def nc3(msgs, i):  # 常量材料回灌 user 轮
    for m in msgs:
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                m["content"] = c + "\n[技能知识参考]\n(4,171 字符材料)"
            break


def nc4(msgs, i):  # 删段
    import re
    t = re.sub(r"## §7 .*?(?=## §8 )", "", sys_text(msgs[i]), flags=re.S)
    set_sys(msgs, i, t)


def main():
    if not os.path.exists(SRC):
        print("缺 w3 转储: " + SRC); return 3
    cases = {"NC1_段序错乱": (nc1, ("S1_section_order",)), "NC2_前缀遥测": (nc2, ("M2_no_telemetry_in_prompt",)),
             "NC3_材料回灌user": (nc3, ("M6_user_turn_task_only", "S5_tail_only_in_user")),
             "NC4_删段": (nc4, ("S1_section_order", "S2_sections_constant"))}
    ok = True
    for tag, (fn, keys) in cases.items():
        mutate(tag, fn)
        # mutate() 只落盘; 重新取目录
        d = max([os.path.join(tempfile.gettempdir(), x) for x in os.listdir(tempfile.gettempdir())
                 if x.startswith("nc_" + tag + "_")], key=os.path.getmtime)
        rc, v = run_checker(d)
        bad = [k for k in keys if v.get(k) is not False]
        good = (rc != 0 and not bad)
        ok = ok and good
        print("%-16s rc=%d 期望键翻红=%s %s" % (tag, rc, keys, "OK" if good else "FAIL " + str({k: v.get(k) for k in keys})))
        shutil.rmtree(d, ignore_errors=True)
    print("NC_PANEL_PASS" if ok else "NC_PANEL_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
