#!/usr/bin/env python3
"""R431 冻结基线互证: 本侧 python 独立重建 BuildPrompt → 引擎侧 /apply-template 渲染 → 与 R430 发布读数比对。

目的: 让「零回归基线」不是自说自话 —— 两套独立实现 (python 重建源码字符串 / llama.cpp 模板渲染) 必须给出同一指纹,
且该指纹必须等于 R430 真机遥测记录值 (`prompt_sha`)。若 growth 曾被挂载, 渲染后 sha 不可能与 R430 相同。

用法: frozen_baseline.py --port 47951 [--msg "好，按这个来。"] [--growth <文本>]
前置: 一个同 r1 模型的 llama-server (见 docs/plans/v0.52.0-r431-growth-mount.md §5)
"""
import argparse
import gzip
import hashlib
import json
import re
import struct
import urllib.request

REPO = "/home/agentuser/AgentFramework"
R430_RECORDED_PROMPT_SHA = "850f6cb17181a38f"   # eval/rover/r430/verdict-C-k8r-r430fix1.json
R430_RECORDED_SEED_SHA = "0aa656fa7eafd93a"


def sha16(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def profile_seed(rbin: str, keypath: str) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    raw = open(rbin, "rb").read()
    plen = struct.unpack("<I", raw[8:12])[0]
    pay = raw[16 : 16 + plen]
    key = open(keypath, "rb").read()
    comp = AESGCM(key).decrypt(pay[:12], pay[28:] + pay[12:28], None)
    return json.loads(gzip.decompress(comp).decode())["profile"]


def build_prompt_parts() -> list:
    """从源码抽 BuildPrompt 的字面量 Appends (不手抄 ⇒ 与实现同步)。"""
    src = open(f"{REPO}/src/agent.modelqueue/LocalGenerationPort.cs", encoding="utf-8").read()
    body = src[src.index("public static string BuildPrompt") : src.index("public static string Clip")]
    return [m.group(1).replace("\\n", "\n") for m in re.finditer(r'sb\.Append\("((?:[^"\\]|\\.)*)"\)', body)]


def build_prompt(msg: str, seed: str, growth: str | None, parts: list) -> str:
    # 对应 BuildPrompt: 头部 11 段字面量 → 【角色设定】seed → (growth clip300) → 【用户消息】msg → 答案:
    s = "".join(parts[0:11]) + "【角色设定】" + seed + "\n"
    if growth:
        s += growth[:300] + "\n"
    return s + "【用户消息】" + msg + "\n" + "答案:\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=47951)
    ap.add_argument("--msg", default="好，按这个来。")
    ap.add_argument("--growth", default=None)
    ap.add_argument("--role", default=f"{REPO}/skeptic.rbin")
    ap.add_argument("--key", default=f"{REPO}/data/master.key")
    a = ap.parse_args()

    seed = "skeptic|" + profile_seed(a.role, a.key)
    bp = build_prompt(a.msg, seed, a.growth, build_prompt_parts())
    req = urllib.request.Request(
        f"http://127.0.0.1:{a.port}/apply-template",
        data=json.dumps({"messages": [{"role": "user", "content": bp}]}).encode(),
        headers={"Content-Type": "application/json"},
    )
    tpl = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())["prompt"]

    print(f"seed_sha16                = {sha16(seed)}   (R430 记录 {R430_RECORDED_SEED_SHA})")
    print(f"BuildPrompt len/sha16     = {len(bp)} / {sha16(bp)}   growth={'on' if a.growth else 'off'}")
    print(f"templated  len/sha16      = {len(tpl)} / {sha16(tpl)}")
    print(f"R430 发布读数 prompt_sha  = {R430_RECORDED_PROMPT_SHA}")
    if a.growth is None and a.msg == "好，按这个来。":
        ok = sha16(tpl) == R430_RECORDED_PROMPT_SHA and sha16(seed) == R430_RECORDED_SEED_SHA
        print("判定: " + ("MATCH ⇒ 零回归基线成立 (且反证 R430 时 growth 为 null)" if ok else "MISMATCH ⇒ 基线不可用"))
        return 0 if ok else 1
    print("判定: 非基线模式 (挂载/其它消息) —— 只用于比对该模式下的指纹")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
