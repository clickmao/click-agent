#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R468 器具: 门判规则 **源码派生** Python 端口 (禁手抄) + 产品测试期望值自检。

派生源 (单一权威): `src/agent.modelqueue/TurnGateJudge.cs` (TurnGateJudge)
                   `src/agent.modelqueue/LocalParaphraseChannel.cs` (改写族 + 守卫面)
  - AckFamilyChars / RepeatFamilyChars / FamilyChars / SubstantiveLengthThreshold
  - **零词表断言**: 若产品源码里重新出现标记/信号词表 (RepeatMarkers / QuestionSignals /
    RequestSignals / CorrectionSignals / ClaimWords) ⇒ 端口 fail-closed (SystemExit) ⇒
    强制同步 (R575: 判定面已改为「结构护栏 + 回补库 (`agent.nlp.NlpGate`)」, 端口必须同构)。
期望值源 (第二源): `src/agent.tests/LocalTurnGateTests.cs` 的 InlineData (G31 认可族 / G35 纯复述族),
                   以及 `src/agent.tests/R498LocalParaphraseTests.cs` 的改写族 InlineData。
⇒ 任一源改变而端口未同步 ⇒ `--selftest` 必红 (防静默漂移)。

补丁面 (回补库) 不在本端口内建模 (签名 = o200k BPE, 只在 C# 侧): 语料行自带 `patch` 声明
(repeat/para), 端口与 C# 双方**都按该声明**判定 ⇒ 结构护栏两侧同源派生, 补丁面由语料声明注入
(见 R575 证据文档「差分口径」一节)。

用法: python3 gate_rules.py --selftest            # 双源自检, PASS/FAIL + rc
      from gate_rules import classify, mechanical_ack, is_pure_repeat, mechanical_pass, RULES_META
"""
import hashlib, io, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_GATE = os.path.join(ROOT, "src", "agent.modelqueue", "TurnGateJudge.cs")
SRC_PARA = os.path.join(ROOT, "src", "agent.modelqueue", "LocalParaphraseChannel.cs")
SRC_TEST = os.path.join(ROOT, "src", "agent.tests", "LocalTurnGateTests.cs")
SRC_TEST_PARA = os.path.join(ROOT, "src", "agent.tests", "R498LocalParaphraseTests.cs")

# R575 零词表断言: 这些**词表/标记表**符号一旦在产品源码里重现, 端口必须停 (不是静默错判)。
FORBIDDEN_TABLES = ("RepeatMarkers", "QuestionSignals", "RequestSignals", "CorrectionSignals", "ClaimWords")


def _read(p):
    if not os.path.exists(p):
        raise SystemExit("派生失败: 源文件不存在 %s" % p)
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


def _table_symbols(src):
    """源码里出现的**词表符号** (字段声明面; 注释/字符串不算)。"""
    body = re.sub(r"///[^\n]*", "", src)
    return [t for t in FORBIDDEN_TABLES if re.search(r"(?:string\[\]|string\s*\[)\s*%s\s*=" % t, body)]


def _inline_cases(test_src, method):
    """取指定 Theory 方法的 InlineData("msg", expected) 对。
    边界 = 上一个 [Theory]/[Fact]/public void ⇒ 只取本方法自带的用例块。"""
    m = re.search(r'public void %s\(string msg, bool expect\w*\)' % re.escape(method), test_src)
    if not m:
        raise SystemExit("派生失败: 找不到测试方法 %s" % method)
    head = test_src[:m.start()]
    b = max(head.rfind("[Theory]"), head.rfind("[Fact]"), head.rfind("public void "))
    region = head[b:]
    return [(_unesc(mm.group(1)), mm.group(2) == "true")
            for mm in re.finditer(r'\[InlineData\("((?:[^"\\]|\\.)*)",\s*(true|false)\)\]', region)]


def _inline_cases_one(test_src, method):
    """取单参 Theory (全部期望 True) 的 InlineData("msg") 串。"""
    m = re.search(r'public void %s\(string msg\)' % re.escape(method), test_src)
    if not m:
        raise SystemExit("派生失败: 找不到测试方法 %s" % method)
    head = test_src[:m.start()]
    b = max(head.rfind("[Theory]"), head.rfind("[Fact]"), head.rfind("public void "))
    region = head[b:]
    return [_unesc(mm.group(1)) for mm in re.finditer(r'\[InlineData\("((?:[^"\\]|\\.)*)"\)\]', region)]


_gate_src = _read(SRC_GATE)
_para_src = _read(SRC_PARA)
_test_src = _read(SRC_TEST)
_test_para_src = _read(SRC_TEST_PARA)

for _src, _name in ((_gate_src, SRC_GATE), (_para_src, SRC_PARA)):
    _found = _table_symbols(_src)
    if _found:
        raise SystemExit("派生失败: %s 里重现词表 %s ⇒ 端口与产品判定面已不同构 (先同步本脚本)" % (_name, _found))

ACK_CHARS = _str_const(_gate_src, "AckFamilyChars")
REPEAT_CHARS = _str_const(_gate_src, "RepeatFamilyChars")
PARA_CHARS = _str_const(_para_src, "FamilyChars")
SUBSTANTIVE_LEN = _int_const(_gate_src, "SubstantiveLengthThreshold")

RULES_META = {
    "gate_source": "src/agent.modelqueue/TurnGateJudge.cs",
    "gate_source_sha256": hashlib.sha256(_gate_src.encode()).hexdigest(),
    "para_source": "src/agent.modelqueue/LocalParaphraseChannel.cs",
    "para_source_sha256": hashlib.sha256(_para_src.encode()).hexdigest(),
    "test_source": "src/agent.tests/LocalTurnGateTests.cs",
    "test_source_sha256": hashlib.sha256(_test_src.encode()).hexdigest(),
    "test_source_para": "src/agent.tests/R498LocalParaphraseTests.cs",
    "test_source_para_sha256": hashlib.sha256(_test_para_src.encode()).hexdigest(),
    "zero_word_tables": list(FORBIDDEN_TABLES),
    "ack_chars_n": len(ACK_CHARS),
    "repeat_chars_n": len(REPEAT_CHARS),
    "para_chars_n": len(PARA_CHARS),
    "substantive_len": SUBSTANTIVE_LEN,
    "patch_faces": ["repeat", "para"],
}


def _is_punct(ch):
    return unicodedata.category(ch).startswith("P")


def _is_symbol(ch):
    return unicodedata.category(ch).startswith("S")


def _normalize(msg, max_raw, max_norm, chars):
    """C# 结构面共同部分: 去标点/空白/符号 + 问号否决 + 两级长度 + 白名单字符集。"""
    m = (msg or "").strip()
    if not m or len(m) > max_raw:
        return None
    buf = []
    for ch in m:
        if ch in "?？":
            return None
        if _is_punct(ch) or ch.isspace() or _is_symbol(ch):
            continue
        if ch not in chars:
            return None
        buf.append(ch)
    n = "".join(buf)
    if len(n) == 0 or len(n) > max_norm:
        return None
    return n


def is_repeat_shape(msg):
    """C# IsRepeatShape: len<=24 ∧ 去标点 <=14 字 ∧ 全属复述白名单 ∧ 无问号。"""
    return _normalize(msg, 24, 14, REPEAT_CHARS) is not None


def is_paraphrase_shape(msg):
    """C# IsParaphraseShape: len<=32 ∧ 去标点 <=16 字 ∧ 全属改写白名单 ∧ 无问号。"""
    return _normalize(msg, 32, 16, PARA_CHARS) is not None


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


def mechanical_pass(msg):
    """C# MechanicalPass 逐行移植 (**零词表**): 问号 / 代码或路径符 / 数字 / 长度 ≥ 阈值 ⇒ True (保守走远端)。"""
    if msg is None or msg.strip() == "":
        return True
    m = msg.strip()
    if "?" in m or "？" in m:
        return True
    if "`" in m or "/" in m or "\\" in m:
        return True
    if any(ch.isdigit() for ch in m):
        return True
    return len(m) >= SUBSTANTIVE_LEN


def is_pure_repeat(msg, patched=False):
    """C# IsPureRepeat: 结构面 ∧ (**回补库命中**)。零词表 ⇒ 未回补一律 False (交远端)。"""
    return is_repeat_shape(msg) and bool(patched)


def is_pure_paraphrase(msg, faces=()):
    """C# IsPureParaphrase: 结构面 ∧ ¬复述族(⑤ 互斥) ∧ (**回补库命中** para 面)。"""
    if not is_paraphrase_shape(msg):
        return False
    if is_pure_repeat(msg, "repeat" in (faces or ())):
        return False
    return "para" in (faces or ())


def classify(msg, faces=()):
    """与产品前置门链同序: MechanicalPass 优先 ⇒ 纯复述 ⇒ 同义改写 ⇒ 认可族 ⇒ 其余。"""
    if mechanical_pass(msg):
        return "pass"
    if is_pure_repeat(msg, "repeat" in (faces or ())):
        return "repeat"
    if is_pure_paraphrase(msg, faces):
        return "para"
    if mechanical_ack(msg):
        return "ack"
    return "other"


# ---------------- 双源自检 ----------------
def selftest():
    ok, fails = True, []
    ack_cases = _inline_cases(_test_src, "G31_认可族结构确认")
    rep_cases = _inline_cases(_test_src, "G35_纯复述族结构确认")
    para_cases = _inline_cases_one(_test_para_src, "改写族_吸收")
    if len(ack_cases) < 5:
        ok = False
        fails.append("G31 InlineData 派生不足 (%d)" % len(ack_cases))
    if len(rep_cases) < 5:
        ok = False
        fails.append("G35 InlineData 派生不足 (%d)" % len(rep_cases))
    if len(para_cases) < 5:
        ok = False
        fails.append("改写族 InlineData 派生不足 (%d)" % len(para_cases))
    for msg, exp in ack_cases:
        got = mechanical_ack(msg)
        if got != exp:
            ok = False
            fails.append("ack(%r) 端口=%s 期望=%s" % (msg, got, exp))
    for msg, exp in rep_cases:
        # 复述族的期望值只有在**回补命中**时才可能为真 (R575 双侧语义) ⇒ 按行期望注入补丁面。
        got = is_pure_repeat(msg, patched=exp)
        if got != exp:
            ok = False
            fails.append("repeat(%r) 端口=%s 期望=%s" % (msg, got, exp))
        if is_pure_repeat(msg, patched=False):
            ok = False
            fails.append("repeat(%r) 无补丁却判真 (安全方向被破)" % msg)
    for msg in para_cases:
        if not is_pure_paraphrase(msg, ("para",)):
            ok = False
            fails.append("para(%r) 回补命中却未吸收" % msg)
        if is_pure_paraphrase(msg, ()):
            ok = False
            fails.append("para(%r) 无补丁却吸收 (安全方向被破)" % msg)
    out = {"selftest": "PASS" if ok else "FAIL", "fails": fails,
           "ack_cases": len(ack_cases), "repeat_cases": len(rep_cases),
           "para_cases": len(para_cases), "rules": RULES_META}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(json.dumps(RULES_META, ensure_ascii=False, indent=1))
