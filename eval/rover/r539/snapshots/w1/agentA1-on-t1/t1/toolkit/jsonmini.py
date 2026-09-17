"""json_mini: 极简 JSON 解析 + 规范化输出。

solve(text) 接收完整 stdin 文本, 返回规范化文本 (无空白, 末尾不带换行)。
非法输入输出单行 "ERR"。
"""
from __future__ import annotations

from typing import Any, List, Tuple


class _Err(Exception):
    pass


class _Parser:
    def __init__(self, s: str) -> None:
        self.s = s
        self.i = 0
        self.n = len(s)

    def parse(self) -> Any:
        self.ws()
        v = self.value()
        self.ws()
        if self.i != self.n:
            raise _Err()
        return v

    def ws(self) -> None:
        while self.i < self.n and self.s[self.i] in " \t\r\n":
            self.i += 1

    def value(self) -> Any:
        if self.i >= self.n:
            raise _Err()
        c = self.s[self.i]
        if c == "n":
            self.lit("null")
            return None
        if c == "t":
            self.lit("true")
            return True
        if c == "f":
            self.lit("false")
            return False
        if c == '"':
            return self.string()
        if c == "[":
            return self.array()
        if c == "{":
            return self.obj()
        if c == "-" or c.isdigit():
            return self.number()
        raise _Err()

    def lit(self, word: str) -> None:
        if self.s[self.i:self.i + len(word)] != word:
            raise _Err()
        self.i += len(word)

    def string(self) -> str:
        if self.s[self.i] != '"':
            raise _Err()
        self.i += 1
        buf: List[str] = []
        while True:
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(buf)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    raise _Err()
                e = self.s[self.i]
                if e == '"':
                    buf.append('"')
                    self.i += 1
                elif e == "\\":
                    buf.append("\\")
                    self.i += 1
                elif e == "/":
                    buf.append("/")
                    self.i += 1
                elif e == "n":
                    buf.append("\n")
                    self.i += 1
                elif e == "t":
                    buf.append("\t")
                    self.i += 1
                elif e == "u":
                    if self.i + 4 >= self.n:
                        raise _Err()
                    hexs = self.s[self.i + 1:self.i + 5]
                    if len(hexs) != 4 or any(ch not in "0123456789abcdefABCDEF" for ch in hexs):
                        raise _Err()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise _Err()
                    buf.append(chr(cp))
                    self.i += 5
                else:
                    raise _Err()
            else:
                if ord(c) < 0x20:
                    raise _Err()
                buf.append(c)
                self.i += 1

    def number(self) -> int:
        start = self.i
        if self.s[self.i] == "-":
            self.i += 1
            if self.i >= self.n:
                raise _Err()
        if self.i >= self.n or not self.s[self.i].isdigit():
            raise _Err()
        if self.s[self.i] == "0":
            self.i += 1
            if self.i < self.n and self.s[self.i].isdigit():
                raise _Err()
        else:
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        if self.i < self.n and self.s[self.i] in ".eE":
            raise _Err()
        return int(self.s[start:self.i])

    def array(self) -> List[Any]:
        self.i += 1
        items: List[Any] = []
        self.ws()
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return items
        while True:
            self.ws()
            items.append(self.value())
            self.ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return items
            raise _Err()

    def obj(self) -> List[Tuple[str, Any]]:
        self.i += 1
        pairs: List[Tuple[str, Any]] = []
        self.ws()
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return pairs
        while True:
            self.ws()
            if self.i >= self.n or self.s[self.i] != '"':
                raise _Err()
            key = self.string()
            self.ws()
            if self.i >= self.n or self.s[self.i] != ":":
                raise _Err()
            self.i += 1
            self.ws()
            val = self.value()
            pairs.append((key, val))
            self.ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return pairs
            raise _Err()


def _dump(v: Any) -> str:
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return _dump_str(v)
    if isinstance(v, list):
        return "[" + ",".join(_dump(x) for x in v) + "]"
    if isinstance(v, list):
        raise _Err()
    # object: list of pairs
    merged = {}
    for key, val in v:
        merged[key] = val
    keys = sorted(merged.keys())
    return "{" + ",".join(_dump_str(kk) + ":" + _dump(merged[kk]) for kk in keys) + "}"
    raise _Err()


def _dump_str(s: str) -> str:
    buf = ['"']
    for c in s:
        if c == '"':
            buf.append('\\"')
        elif c == "\\":
            buf.append("\\\\")
        elif c == "\n":
            buf.append("\\n")
        elif c == "\t":
            buf.append("\\t")
        else:
            buf.append(c)
    buf.append('"')
    return "".join(buf)


def solve(text: str) -> str:
    try:
        v = _Parser(text).parse()
        return _dump(v)
    except _Err:
        return "ERR"
    except RecursionError:
        return "ERR"
