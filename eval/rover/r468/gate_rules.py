#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R468 器具: 门判规则 **源码派生** Python 端口 (禁手抄) + 产品测试期望值自检。

派生源 (单一权威): src/agent.modelqueue/LocalGenerationPort.cs (TurnGateJudge)
  - AckFamilyChars / RepeatFamilyChars / RepeatMarkers / SubstantiveLengthThreshold
  - QuestionSignals / RequestSignals / CorrectionSignals
期望值源 (第二源): src/agent.tests/LocalTurnGateTests.cs 的 InlineData (G31 认可族 / G35 纯复述族)
⇒ 任一源改变而端口未同步 ⇒ `--selftest` 必红 (防静默漂移)。

用法: python3 gate_rules.py --selftest            # 双源自检, PASS/FAIL + rc
      from gate_rules import classify, mechanical_ack, is_pure_repeat, mechanical_pass, RULES_META
"""
import hashlib, io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_GATE = os.path.join(ROOT, "src", "agent.modelqueue", "LocalGenerationPort.cs")
SRC_TEST = os.path.join(ROOT, "src", "agent.tests", "LocalTurnGateTests.cs")


def _read(p):
    return io.open(p, encoding="utf-8").read()



_ESC = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'"}


def _unesc(s):
    """C# 字面量反转义 (只处理转义序列, **不动非 ASCII 字符** —— unicode_escape 会把 UTF-8 变乱码)。"""
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n == "u" and re.match(r"[0-9a-fA-F]{4}", s[i + 2:i + 6] or ""):
                out.append(chr(int(s[i + 2:i + 6], 16)))
                i += 6
                continue
            out.append(_ESC.get(n, n))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _str_const(src, name):
    m = re.search(r'const\s+string\s+%s\s*=\s*"((?:[^"\\]|\\.)*)"' % re.escape(name), src)
    if not m:
        raise SystemExit("派生失败: 找不到常量 %s" % name)
    return _unesc(m.group(1))


def _int_const(src, name):
    m = re.search(r'const\s+int\s+%s\s*=\s*(\d+)' % re.escape(name), src)
    if not m:
        raise SystemExit("派生失败: 找不到常量 %s" % name)
    return int(m.group(1))


def _array_of_strings(src, name):
    m = re.search(r'string\[\]\s+%s\s*=\s*\{(.*?)\};' % re.escape(name), src, re.S)
    if not m:
        raise SystemExit("派生失败: 找不到数组 %s" % name)
    return [_unesc(s) for s in re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))]


def _inline_cases(test_src, method):
    """取 LocalTurnGateTests 里指定 Theory 方法的 InlineData("msg", expected) 对。
    边界 = 上一个 [Theory]/[Fact]/public void ⇒ 只取本方法自带的用例块。"""
    m = re.search(r'public void %s\(string msg, bool expect\w*\)' % re.escape(method), test_src)
    if not m:
        raise SystemExit("派生失败: 找不到测试方法 %s" % method)
    head = test_src[:m.start()]
    b = max(head.rfind("[Theory]"), head.rfind("[Fact]"), head.rfind("public void "))
    region = head[b:]
    return [(_unesc(mm.group(1)), mm.group(2) == "true")
            for mm in re.finditer(r'\[InlineData\("((?:[^"\\]|\\.)*)",\s*(true|false)\)\]', region)]


_gate_src = _read(SRC_GATE)
_test_src = _read(SRC_TEST)

ACK_CHARS = _str_const(_gate_src, "AckFamilyChars")
REPEAT_CHARS = _str_const(_gate_src, "RepeatFamilyChars")
SUBSTANTIVE_LEN = _int_const(_gate_src, "SubstantiveLengthThreshold")
_m = re.search(r'string\[\]\s+RepeatMarkers\s*=\s*\{(.*?)\};', _gate_src, re.S)
REPEAT_MARKERS = [_unesc(s) for s in re.findall(r'"((?:[^"\\]|\\.)*)"', _m.group(1))]
QUESTION_SIGNALS = _array_of_strings(_gate_src, "QuestionSignals")
REQUEST_SIGNALS = _array_of_strings(_gate_src, "RequestSignals")
CORRECTION_SIGNALS = _array_of_strings(_gate_src, "CorrectionSignals")

RULES_META = {
    "gate_source": "src/agent.modelqueue/LocalGenerationPort.cs",
    "gate_source_sha256": hashlib.sha256(_gate_src.encode()).hexdigest(),
    "test_source": "src/agent.tests/LocalTurnGateTests.cs",
    "test_source_sha256": hashlib.sha256(_test_src.encode()).hexdigest(),
    "repeat_markers_n": len(REPEAT_MARKERS),
    "question_signals_n": len(QUESTION_SIGNALS),
    "request_signals_n": len(REQUEST_SIGNALS),
    "correction_signals_n": len(CORRECTION_SIGNALS),
    "substantive_len": SUBSTANTIVE_LEN,
}


def mechanical_ack(msg):
    """C# MechanicalAck 逐行移植: 去标点/空白/符号后 ≤10 字 且 字符全属白名单 且 非空。"""
    m = (msg or "").strip()
    if not m:
        return False
    n = 0
    for ch in m:
        if _is_punct(ch) or ch.isspace() or _is_symbol(ch):
            continue
        if ch not in ACK_CHARS:
            return False
        n += 1
        if n > 10:
            return False
    return n > 0


def is_pure_repeat(msg):
    """C# IsPureRepeat 逐行移植: ① 完整复述标记 ② 去标点后 ≤14 字且字符全属白名单 ③ 无问号。"""
    m = (msg or "").strip()
    if not m or len(m) > 24:
        return False
    buf = []
    for ch in m:
        if ch in "?？":
            return False
        if _is_punct(ch) or ch.isspace() or _is_symbol(ch):
            continue
        buf.append(ch)
    n = "".join(buf)
    if len(n) == 0 or len(n) > 14:
        return False
    for ch in n:
        if ch not in REPEAT_CHARS:
            return False
    return any(mk in n for mk in REPEAT_MARKERS)


def mechanical_pass(msg):
    """C# MechanicalPass 逐行移植: 任何疑问/指令/纠正/代码/数字/长文本 ⇒ True (保守走远端)。"""
    if msg is None or msg.strip() == "":
        return True
    m = msg.strip()
    if "?" in m or "？" in m:
        return True
    for w in QUESTION_SIGNALS + REQUEST_SIGNALS + CORRECTION_SIGNALS:
        if w in m:
            return True
    if "`" in m or "/" in m or "\\" in m:
        return True
    if any(ch.isdigit() for ch in m):
        return True
    return len(m) >= SUBSTANTIVE_LEN


def classify(msg):
    """与产品前置门链同序: MechanicalPass 优先 ⇒ 纯复述 ⇒ 认可族 ⇒ 其余 (非认可短句)。"""
    if mechanical_pass(msg):
        return "pass"
    if is_pure_repeat(msg):
        return "repeat"
    if mechanical_ack(msg):
        return "ack"
    return "other"


def _is_punct(ch):
    import unicodedata
    return unicodedata.category(ch).startswith("P")


def _is_symbol(ch):
    import unicodedata
    return unicodedata.category(ch).startswith("S")


# ---------------- 双源自检 ----------------
def selftest():
    ok, fails = True, []
    ack_cases = _inline_cases(_test_src, "G31_认可族结构确认")
    rep_cases = _inline_cases(_test_src, "G35_纯复述族结构确认")
    if len(ack_cases) < 5:
        ok = False
        fails.append("G31 InlineData 派生不足 (%d)" % len(ack_cases))
    if len(rep_cases) < 5:
        ok = False
        fails.append("G35 InlineData 派生不足 (%d)" % len(rep_cases))
    for msg, exp in ack_cases:
        got = mechanical_ack(msg)
        if got != exp:
            ok = False
            fails.append("ack(%r) 端口=%s 期望=%s" % (msg, got, exp))
    for msg, exp in rep_cases:
        got = is_pure_repeat(msg)
        if got != exp:
            ok = False
            fails.append("repeat(%r) 端口=%s 期望=%s" % (msg, got, exp))
    out = {"selftest": "PASS" if ok else "FAIL", "fails": fails,
           "ack_cases": len(ack_cases), "repeat_cases": len(rep_cases), "rules": RULES_META}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(json.dumps(RULES_META, ensure_ascii=False, indent=1))
