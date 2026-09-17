"""tasksvc.store —— 存储层。

职责 (本节点 n1 声明的范围, 不外溢):
  1) 全局选项 --db <path> 指向的 JSON 文件;
     文件必须是合法 JSON 对象, 且含整数 next_id (持久化、只增不减)。
  9) 写入原子: 写同目录临时文件 + os.replace 原子重命名;
     任何时刻读到的文件都是完整 JSON; 不留临时文件残留。
 10) 只用标准库; 文件 UTF-8 无 BOM。

文件形态 (全部为合法 JSON 对象):
  {
    "version": 1,
    "next_id": 1,                # 整数, 只增不减
    "tasks": {                   # id(str) -> task 对象
      "1": {"id":1, "text":"...", "done":false,
            "created_at":1234.0, "expires_at":null}
    }
  }

对外 API:
  StoreError          —— 存储损坏 (对应退出码 4 / bad_store)
  default_state()     —— 全新空状态
  validate_state(obj) —— 校验并归一化状态 (不合法抛 StoreError)
  load_store(path)    —— 读取 + 校验; 文件不存在返回全新状态
  save_store(path, state) —— 原子写入, 返回是否发生新建

自测 (无头):
  python3 -B -m tasksvc.store --selftest
退出码 0=PASS / 非 0=FAIL。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

__all__ = [
    "StoreError",
    "default_state",
    "validate_state",
    "load_store",
    "save_store",
]

SCHEMA_VERSION = 1
_TASK_FIELDS = ("id", "text", "done", "created_at", "expires_at")


class StoreError(Exception):
    """存储文件损坏 (非 JSON 或 schema 不符)。"""


# --------------------------------------------------------------------------
# 状态构造 / 校验
# --------------------------------------------------------------------------

def default_state() -> dict:
    """全新空状态。next_id 从 1 开始 (0 保留为哨兵)。"""
    return {"version": SCHEMA_VERSION, "next_id": 1, "tasks": {}}


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _norm_task(raw, key: str) -> dict:
    """校验单个 task 并归一化为标准形态。不合法抛 StoreError。"""
    if not isinstance(raw, dict):
        raise StoreError("task 不是对象: %r" % (key,))

    for f in _TASK_FIELDS:
        if f not in raw:
            raise StoreError("task 缺字段 %s: %r" % (f, key))

    tid = raw["id"]
    if not _is_int(tid):
        raise StoreError("task.id 非整数: %r" % (tid,))
    if str(tid) != key:
        raise StoreError("task.id 与键不一致: %r vs %r" % (tid, key))

    text = raw["text"]
    if not isinstance(text, str):
        raise StoreError("task.text 非字符串: %r" % (key,))

    done = raw["done"]
    if not isinstance(done, bool):
        raise StoreError("task.done 非布尔: %r" % (key,))

    created_at = raw["created_at"]
    if not _is_num(created_at):
        raise StoreError("task.created_at 非数值: %r" % (key,))
    created_at = float(created_at)

    expires_at = raw["expires_at"]
    if expires_at is None:
        expires_at = None
    elif _is_num(expires_at):
        expires_at = float(expires_at)
    else:
        raise StoreError("task.expires_at 非法: %r" % (key,))

    return {
        "id": tid,
        "text": text,
        "done": done,
        "created_at": created_at,
        "expires_at": expires_at,
    }


def validate_state(obj) -> dict:
    """校验并归一化整个状态; 不合法抛 StoreError。"""
    if not isinstance(obj, dict):
        raise StoreError("根节点不是 JSON 对象")

    if "next_id" not in obj:
        raise StoreError("缺 next_id")
    next_id = obj["next_id"]
    if not _is_int(next_id) or next_id < 1:
        raise StoreError("next_id 非法: %r" % (next_id,))

    raw_tasks = obj.get("tasks", {})
    if not isinstance(raw_tasks, dict):
        raise StoreError("tasks 不是对象")

    tasks: dict = {}
    max_id = 0
    for key, raw in raw_tasks.items():
        if not isinstance(key, str):
            raise StoreError("tasks 键非字符串: %r" % (key,))
        task = _norm_task(raw, key)
        tasks[key] = task
        if task["id"] > max_id:
            max_id = task["id"]

    # next_id 只增不减: 必须严格大于现存最大 id。
    if next_id <= max_id:
        raise StoreError("next_id(%d) 未超过现存最大 id(%d)" % (next_id, max_id))

    return {"version": SCHEMA_VERSION, "next_id": next_id, "tasks": tasks}


# --------------------------------------------------------------------------
# 读取
# --------------------------------------------------------------------------

def load_store(path: str) -> dict:
    """读取并校验存储。文件不存在 -> 全新状态。损坏 -> StoreError。"""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except FileNotFoundError:
        return default_state()
    except OSError as exc:
        raise StoreError("无法读取存储文件: %s" % (exc,))

    if raw.startswith(b"\xef\xbb\xbf"):
        raise StoreError("存储文件含 UTF-8 BOM")
    if not raw.strip():
        raise StoreError("存储文件为空")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StoreError("存储文件非 UTF-8: %s" % (exc,))

    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StoreError("存储文件非合法 JSON: %s" % (exc,))

    return validate_state(obj)


# --------------------------------------------------------------------------
# 原子写入
# --------------------------------------------------------------------------

def _dump(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2)


def save_store(path: str, state: dict) -> bool:
    """原子保存。写同目录临时文件 -> flush+fsync -> os.replace。

    返回 True 表示本次新建了存储文件路径 (调用前不存在), 否则 False。
    失败时清理临时文件并抛出原异常 (不留残留)。
    """
    state = validate_state(state)

    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)

    existed = os.path.exists(path)
    payload = (_dump(state) + "\n").encode("utf-8")

    fd, tmp = tempfile.mkstemp(
        prefix=".tasksvc-tmp-", suffix=".json", dir=parent or "."
    )
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass

    # 目录 fsync, 保证重命名元数据落盘 (best-effort)。
    try:
        dfd = os.open(parent or ".", os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except OSError:
        pass

    return not existed


# --------------------------------------------------------------------------
# 自测
# --------------------------------------------------------------------------

def _assert(cond: bool, label: str, failures: list) -> None:
    if cond:
        print("  PASS %s" % label)
    else:
        print("  FAIL %s" % label)
        failures.append(label)


def _selftest() -> int:
    failures: list = []
    print("[tasksvc.store] selftest")

    with tempfile.TemporaryDirectory(prefix="tasksvc-store-test-") as td:
        db = os.path.join(td, "db.json")

        # 1) 文件不存在 -> 全新状态
        st = load_store(db)
        _assert(st == default_state(), "missing file -> default_state", failures)
        _assert(st["next_id"] == 1, "next_id starts at 1", failures)

        # 2) 新建 + 往返
        st["next_id"] = 5
        st["tasks"]["1"] = {
            "id": 1, "text": " 中文emoji🙂 ", "done": False,
            "created_at": 100.5, "expires_at": None,
        }
        st["tasks"]["4"] = {
            "id": 4, "text": "x", "done": True,
            "created_at": 101.0, "expires_at": 200.0,
        }
        created = save_store(db, st)
        _assert(created is True, "save_store reports new file", failures)

        back = load_store(db)
        _assert(back["next_id"] == 5, "next_id persisted", failures)
        _assert(back["tasks"]["1"]["text"] == " 中文emoji🙂 ",
                "text byte-preserved (spaces/cjk/emoji)", failures)
        _assert(back["tasks"]["1"]["expires_at"] is None,
                "expires_at null preserved", failures)
        _assert(back["tasks"]["4"]["expires_at"] == 200.0,
                "expires_at float preserved", failures)

        created2 = save_store(db, back)
        _assert(created2 is False, "save_store reports existing file", failures)

        # 3) 磁盘上必须是合法 JSON 且无 BOM
        with open(db, "rb") as fh:
            raw = fh.read()
        _assert(not raw.startswith(b"\xef\xbb\xbf"), "no UTF-8 BOM", failures)
        _assert(json.loads(raw.decode("utf-8"))["next_id"] == 5,
                "on-disk content is valid JSON", failures)

        # 4) 无临时文件残留
        leftovers = [n for n in os.listdir(td) if n.startswith(".tasksvc-tmp-")]
        _assert(leftovers == [], "no temp file residue", failures)

        # 5) 损坏: 非 JSON -> StoreError
        with open(db, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        try:
            load_store(db)
            _assert(False, "non-JSON raises StoreError", failures)
        except StoreError:
            _assert(True, "non-JSON raises StoreError", failures)

        # 6) 损坏: 顶层非对象 -> StoreError
        with open(db, "w", encoding="utf-8") as fh:
            fh.write("[1,2,3]")
        try:
            load_store(db)
            _assert(False, "non-object root raises StoreError", failures)
        except StoreError:
            _assert(True, "non-object root raises StoreError", failures)

        # 7) 损坏: 缺 next_id -> StoreError
        with open(db, "w", encoding="utf-8") as fh:
            fh.write('{"tasks": {}}')
        try:
            load_store(db)
            _assert(False, "missing next_id raises StoreError", failures)
        except StoreError:
            _assert(True, "missing next_id raises StoreError", failures)

        # 8) 损坏: next_id 非整数 -> StoreError
        with open(db, "w", encoding="utf-8") as fh:
            fh.write('{"next_id": "x", "tasks": {}}')
        try:
            load_store(db)
            _assert(False, "non-int next_id raises StoreError", failures)
        except StoreError:
            _assert(True, "non-int next_id raises StoreError", failures)

        # 9) 损坏: next_id 未超过最大 id (只增不减不变式) -> StoreError
        with open(db, "w", encoding="utf-8") as fh:
            fh.write(
                '{"next_id": 3, "tasks": {"3": {"id":3, "text":"t", '
                '"done": false, "created_at": 1.0, "expires_at": null}}}'
            )
        try:
            load_store(db)
            _assert(False, "next_id<=max_id raises StoreError", failures)
        except StoreError:
            _assert(True, "next_id<=max_id raises StoreError", failures)

        # 10) 损坏: task 缺字段 / text 非字符串 -> StoreError
        with open(db, "w", encoding="utf-8") as fh:
            fh.write(
                '{"next_id": 2, "tasks": {"1": {"id":1, "text":123, '
                '"done": false, "created_at": 1.0}}}'
            )
        try:
            load_store(db)
            _assert(False, "bad task raises StoreError", failures)
        except StoreError:
            _assert(True, "bad task raises StoreError", failures)

        # 11) 备份/新建父目录
        nested = os.path.join(td, "sub", "deep", "db.json")
        save_store(nested, default_state())
        _assert(load_store(nested)["next_id"] == 1, "creates parent dirs", failures)

    print("[tasksvc.store] %s (%d failures)"
          % ("PASS" if not failures else "FAIL", len(failures)))
    return 0 if not failures else 1


def _main(argv) -> int:
    if argv == ["--selftest"]:
        return _selftest()
    sys.stderr.write("usage: python3 -B -m tasksvc.store --selftest\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
