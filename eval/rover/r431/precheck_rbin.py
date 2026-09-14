#!/usr/bin/env python3
"""R431 前置机检 + fixture 生成器 (只读源 rbin, 不改任何现有文件)。

用法:
  precheck_rbin.py <src.rbin> <master.key>                 # 打印域数/种子指纹 (前置条件机检)
  precheck_rbin.py --fixture <src.rbin> <master.key> <out.rbin> [domains]  # 生成同种子+合成成长的 fixture role

rbin 容器 (权威 = src/agent.roles/RoleBinaryFile.cs):
  bytes 0-3  magic "ARBL" | 4 version=1 | 5 flags(bit0=AES-GCM) | 6-7 保留
  bytes 8-11 payload 密文长度 | 12-15 gzip 压缩长度 | 16+ payload = nonce12|tag16|cipher
  payload 内 JSON = 扁平 string→string 字典; g:<domain> = "<reward>|<penalty>" (FromPayload k[2..])
"""
import gzip
import hashlib
import json
import struct
import sys


def load(path: str, keypath: str):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    raw = open(path, "rb").read()
    assert raw[:4] == b"ARBL", "非 ARBL 文件"
    assert raw[4] == 1, f"版本不支持 {raw[4]}"
    flags = raw[5]
    plen = struct.unpack("<I", raw[8:12])[0]
    clen = struct.unpack("<I", raw[12:16])[0]
    payload = raw[16 : 16 + plen]
    if flags & 0x01:
        key = open(keypath, "rb").read()
        comp = AESGCM(key).decrypt(payload[:12], payload[28:] + payload[12:28], None)
    else:
        comp = payload
    assert len(comp) == clen, f"长度不符: {len(comp)} != {clen}"
    return json.loads(gzip.decompress(comp).decode())


def save(path: str, doc: dict, keypath: str, deterministic_nonce: bytes | None = None) -> None:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = open(keypath, "rb").read()
    plain = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()
    comp = gzip.compress(plain, compresslevel=9, mtime=0)
    nonce = deterministic_nonce or b"R431FIXTURE1"
    assert len(nonce) == 12, "nonce 必须 12 字节 (fixture 用固定 nonce ⇒ 产物可复现)"
    cipher_and_tag = AESGCM(key).encrypt(nonce, comp, None)
    cipher, tag = cipher_and_tag[:-16], cipher_and_tag[-16:]
    payload = nonce + tag + cipher  # ★ 必须是 nonce|tag|cipher (与 C# AesGcm 写出顺序一致); AESGCM.encrypt 返回的是 cipher|tag, 需拆开重排
    hdr = b"ARBL" + bytes([1, 1, 0, 0]) + struct.pack("<I", len(payload)) + struct.pack("<I", len(comp))
    open(path, "wb").write(hdr + payload)


def sha16(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def main() -> int:
    a = sys.argv[1:]
    if a and a[0] == "--fixture":
        src, keypath, out = a[1:4]
        domains = a[4] if len(a) > 4 else "general=6|0,docker=0|6"
        doc = load(src, keypath)
        for kv in domains.split(","):
            name, rp = kv.split("=")
            doc[f"g:{name}"] = rp
        save(out, doc, keypath)
        d = load(out, keypath)
        g = {k: v for k, v in d.items() if k.startswith("g:")}
        print(f"[fixture] {out} 域={len(g)} {g} profile_len={len(d['profile'])}")
        print(f"[fixture] 种子指纹 sha16={sha16(d['id'] + '|' + d['profile'])}")
        return 0

    src, keypath = a[0], a[1]
    doc = load(src, keypath)
    growth = {k[2:]: v for k, v in doc.items() if k.startswith("g:")}
    print(f"id={doc['id']} name={doc.get('name','')} profile_len={len(doc.get('profile',''))}")
    print(f"growth_domains={len(growth)} {growth}")
    print(f"role_seed_sha16={sha16(doc['id'] + '|' + doc['profile'])}")
    print("⇒ 域=0 ⇒ RenderForPrompt() 恒空串 ⇒ 门判挂载与不挂载逐位同一 (挂载在当前真实负载上不可测)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
