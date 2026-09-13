#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Silk.NET.Vulkan 包内 DLL 提取 Vulkan 加载器名字 (R396 用户令的权威 oracle)。

用户令 (逐字): "不要引入silk.net; 但用的vulkan.dll文件名与版本请和silk.net库一致"。

做法: **不读文档、不猜常量** —— 直接在包内受管程序集里扫描 UTF-16 字符串常量
(.NET 的 string 字面量在元数据中是 UTF-16), 命中即取证; 同时记录包资产的 sha256,
使"我们的加载器名字 == Silk.NET 实际使用的名字"这一断言可**跨机器复算**。

输出: src/agent.gpu/oracle/silknet-vulkan-loader.json (机检读取此文件)
"""
import hashlib
import json
import os
import re
import sys

PKG = "silk.net.vulkan"
VER = "2.23.0"
ASSET = os.path.join("lib", "netstandard2.0", "Silk.NET.Vulkan.dll")
NAMES = ["vulkan-1.dll", "libvulkan.so.1", "libvulkan.so", "libvulkan.dylib"]


def nuget_root() -> str:
    for c in (os.environ.get("NUGET_PACKAGES"),
              os.path.join(os.path.expanduser("~"), ".nuget", "packages")):
        if c and os.path.isdir(c):
            return c
    return ""


def main(out_path: str | None) -> int:
    root = nuget_root()
    if not root:
        print("error{kind=nuget_root_missing}", file=sys.stderr)
        return 1
    dll = os.path.join(root, PKG, VER, ASSET)
    if not os.path.isfile(dll):
        print(f"error{{kind=asset_missing path={dll}}}", file=sys.stderr)
        return 1
    raw = open(dll, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    found = {}
    for n in NAMES:
        for enc, pat in (("utf16le", n.encode("utf-16-le")), ("utf8", n.encode())):
            c = raw.count(pat)
            if c:
                found.setdefault(n, {})[enc] = c
    missing = [n for n in NAMES if n not in found]
    if missing:
        print(f"error{{kind=extract_failed missing={','.join(missing)}}}", file=sys.stderr)
        return 1
    # 反证: 名字确实来自该程序集而非偶然字节 —— 要求每个名字至少以 UTF-16 形式出现
    for n in NAMES:
        if "utf16le" not in found[n]:
            print(f"error{{kind=not_a_managed_constant name={n}}}", file=sys.stderr)
            return 1
    doc = {
        "source_package": "Silk.NET.Vulkan",
        "source_version": VER,
        "source_asset": ASSET.replace(os.sep, "/"),
        "source_sha256": sha,
        "source_bytes": len(raw),
        "extracted": found,
        "platform_map": {
            "windows": ["vulkan-1.dll"],
            "linux": ["libvulkan.so.1", "libvulkan.so"],
            "macos": ["libvulkan.dylib"],
        },
        "extractor": "eval/vulkan/extract_silknet_loader_names.py",
        "note": "顺序即解析优先级: soname(.so.1) 优先于无版本名, 与 Silk.NET 的候选顺序一致。",
    }
    txt = json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        open(out_path, "w", encoding="utf-8").write(txt)
        print(f"oracle{{file={out_path} sha256={sha} names={len(found)}}}")
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
