"""tasksvc.store —— 存储层 (第 1 段职责)。

职责边界 (本段只负责这些):
  1) 全局选项 `--db <path>` 指向的 JSON 文件读写。文件形态自定, 但必须是
     合法 JSON 对象, 且含整数 `next_id` (持久化、只增不减)。
  9) 写入必须原子: 写临时文件 + 同目录原子重命名, 不留临时文件残留;
     任何时刻读到的文件都必须是完整 JSON。
 10) 只允许标准库 (禁第三方包、禁联网)。文件必须 UTF-8 无 BOM。

不负责: 时钟注入、视图过滤、id 分配策略、参数错/未找到的退出码。
(那些属于 model.py / cli.py 段。)

文件内部形态:
  {
    "next_id": 3,
    "tasks": [ {"id":1, "text":"...", "done":false,
                "created_at":1.0, "expires_at":null}, ... ]
  }

对外接口 (供后续段调用):
  - BadStore                       异常: 文件损坏 / schema 不符 (cli 段映射退出码 4)
  - empty_state()                  新建空状态
  - load(path)                     读状态, 文件不存在 -> empty_state()
  - save(path, state)              原子写状态, 并校验即将写出的 state 合法
  - validate_state(state)          严格校验 schema, 不符抛 BadStore
  - state_to_json(state)           序列化为 UTF-8 文本 (无 BOM)
  - json_to_state(text)            解析 + 校验

自检: python3 -B -m tasksvc.store --selftest
"""

from __future__ import annotations

import json
import os
import tempfile

__all__ = [
    "BadStore",
    "TASK_FIELDS",
    "empty_state",
    "validate_state",
    "state_to_json",
    "json_to_state",
    "load",
    "save",
]

# 任务对象的字段契约 (与整包规格中的 task 形状一致)
TASK_FIELDS = ("id", "text", "done", "created_at", "expires_at")


class BadStore(Exception):
    """存储文件损坏: 非 JSON、非对象, 或 schema 不符。"""


# --------------------------------------------------------------------------
# 状态构造与校验
# --------------------------------------------------------------------------
def empty_state():
    """返回全新初始状态。next_id 从 1 开始 (整数, 只增不减)。"""
    return {"next_id": 1, "tasks": []}


def _is_int(v):
    """严格整数判定: bool 不是 int (isinstance(True, int) 为真, 需排除)。"""
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number(v):
    """严格数值判定: bool 排除。"""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _validate_task(task):
    if not isinstance(task, dict):
        raise BadStore("task 不是 JSON 对象")
    for field in TASK_FIELDS:
        if field not in task:
            raise BadStore("task 缺少字段: %s" % field)
    if not _is_int(task["id"]):
        raise BadStore("task.id 必须为整数")
    if not isinstance(task["text"], str):
        raise BadStore("task.text 必须为字符串")
    if not isinstance(task["done"], bool):
        raise BadStore("task.done 必须为布尔值")
    if not _is_number(task["created_at"]):
        raise BadStore("task.created_at 必须为数字")
    exp = task["expires_at"]
    if exp is not None and not _is_number(exp):
        raise BadStore("task.expires_at 必须为数字或 null")


def validate_state(state):
    """严格校验状态 schema; 不符抛 BadStore。返回 state 本身。"""
    if not isinstance(state, dict):
        raise BadStore("根节点不是 JSON 对象")
    if "next_id" not in state:
        raise BadStore("缺少 next_id")
    if not _is_int(state["next_id"]):
        raise BadStore("next_id 必须为整数")
    if state["next_id"] < 1:
        raise BadStore("next_id 必须 >= 1")
    tasks = state.get("tasks")
    if not isinstance(tasks, list):
        raise BadStore("tasks 必须为数组")
    seen = set()
    max_id = 0
    for task in tasks:
        _validate_task(task)
        tid = task["id"]
        if tid < 1:
            raise BadStore("task.id 必须 >= 1")
        if tid in seen:
            raise BadStore("task.id 重复: %d" % tid)
        seen.add(tid)
        if tid > max_id:
            max_id = tid
    # next_id 只增不减: 必须大于当前任何已存在的 id
    if state["next_id"] <= max_id:
        raise BadStore("next_id 必须大于所有已存在 id")
    return state


# --------------------------------------------------------------------------
# 序列化
# --------------------------------------------------------------------------
def state_to_json(state):
    """序列化为 UTF-8 文本 (无 BOM、无多余空白)。"""
    validate_state(state)
    return json.dumps(state, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def json_to_state(text):
    """解析文本为状态并校验; 失败抛 BadStore。"""
    try:
        state = json.loads(text)
    except Exception as exc:  # JSONDecodeError 等
        raise BadStore("不是合法 JSON: %s" % exc)
    return validate_state(state)


# --------------------------------------------------------------------------
# 读写 (原子)
# --------------------------------------------------------------------------
def load(path):
    """读取状态文件。

    - 文件不存在 -> empty_state() (首次运行, 不是错误)
    - 文件存在但非 JSON / schema 不符 -> BadStore
    """
    if not os.path.exists(path):
        return empty_state()
    try:
        with open(path, "r", encoding="utf-8", newline="") as fh:
            text = fh.read()
    except FileNotFoundError:
        return empty_state()
    except UnicodeDecodeError as exc:
        raise BadStore("文件不是合法 UTF-8: %s" % exc)
    return json_to_state(text)


def save(path, state):
    """原子写入状态文件。

    流程: 同目录临时文件 -> flush + fsync -> os.replace 原子重命名。
    失败路径清理临时文件, 不留残留。
    """
    validate_state(state)
    text = state_to_json(state)
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tasksvc-tmp-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    return state


# --------------------------------------------------------------------------
# 自检入口
# --------------------------------------------------------------------------
def _selftest():
    """无头自检: 覆盖 schema 校验、往返、原子写、无残留、幂等读。

    运行: python3 -B -m tasksvc.store --selftest
    """
    results = []

    def check(name, fn):
        try:
            fn()
            results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            results.append((name, False, "%s: %s" % (type(exc).__name__, exc)))

    tmpdir = tempfile.mkdtemp(prefix="tasksvc-selftest-")
    db = os.path.join(tmpdir, "db.json")
    try:
        # 1. 首次读取: 文件不存在 -> 空状态, next_id == 1
        def t1():
            st = load(db)
            assert st == {"next_id": 1, "tasks": []}, st
        check("load_missing_returns_empty", t1)

        # 2. 保存后可完整读回 (往返)
        def t2():
            st = empty_state()
            st["tasks"].append({"id": 1, "text": "中文 😀", "done": False,
                                "created_at": 1.5, "expires_at": None})
            st["next_id"] = 2
            save(db, st)
            back = load(db)
            assert back == st, back
        check("roundtrip", t2)

        # 3. 文本逐字节保留 (中文/emoji/首尾空格)
        raw = "  a b\t😀中文 \n"
        def t3():
            st = empty_state()
            st["tasks"].append({"id": 1, "text": raw, "done": False,
                                "created_at": 0, "expires_at": 10})
            st["next_id"] = 2
            save(db, st)
            back = load(db)
            assert back["tasks"][0]["text"] == raw, repr(back["tasks"][0]["text"])
        check("text_bytewise", t3)

        # 4. 原子写: 无临时文件残留
        def t4():
            leftovers = [n for n in os.listdir(tmpdir) if n.startswith(".tasksvc-tmp-")]
            assert leftovers == [], leftovers
        check("no_temp_residue", t4)

        # 5. 写入过程中并发读: 读到的永远是完整 JSON
        def t5():
            st = load(db)
            for i in range(5):
                st["tasks"] = [{"id": i + 1, "text": "x" * 2000, "done": False,
                                "created_at": 0, "expires_at": None}]
                st["next_id"] = i + 2
                save(db, st)
                parsed = json_to_state(open(db, "r", encoding="utf-8").read())
                assert parsed["next_id"] == i + 2, parsed["next_id"]
        check("atomic_visible_complete", t5)

        # 6. 损坏检测: 非 JSON -> BadStore
        def t6():
            with open(db, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            try:
                load(db)
            except BadStore:
                return
            raise AssertionError("应抛 BadStore")
        check("corrupt_not_json", t6)

        # 7. 损坏检测: schema 不符 (next_id 缺失 / 类型错)
        def t7():
            cases = [
                {"tasks": []},                                  # 缺 next_id
                {"next_id": "3", "tasks": []},                  # 类型错
                {"next_id": 1, "tasks": [{"id": 1}]},           # task 缺字段
                {"next_id": 1, "tasks": [{"id": 1, "text": "a", "done": False,
                                          "created_at": 0, "expires_at": None},
                                         {"id": 1, "text": "b", "done": False,
                                          "created_at": 0, "expires_at": None}]},  # id 重复
                {"next_id": 1, "tasks": [{"id": 5, "text": "a", "done": False,
                                          "created_at": 0, "expires_at": None}]},  # next_id <= max_id
            ]
            for state in cases:
                try:
                    validate_state(state)
                except BadStore:
                    continue
                raise AssertionError("schema 应被判非法: %r" % (state,))
        check("corrupt_schema", t7)

        # 8. 负向控制: 合法状态必须通过 (含空 tasks 且 next_id>0)
        def t8():
            validate_state({"next_id": 7, "tasks": [
                {"id": 1, "text": "", "done": True, "created_at": 0, "expires_at": 3.0}]})
        check("negative_control_valid_passes", t8)

        # 9. 无 BOM: 文件首字节不是 0xEF 0xBB 0xBF
        def t9():
            st = empty_state()
            st["tasks"].append({"id": 1, "text": "u", "done": False,
                                "created_at": 0, "expires_at": None})
            st["next_id"] = 2
            save(db, st)
            with open(db, "rb") as fh:
                head = fh.read(3)
            assert head != b"\xef\xbb\xbf", head
        check("no_bom", t9)

    finally:
        for name in os.listdir(tmpdir):
            try:
                os.unlink(os.path.join(tmpdir, name))
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass

    failed = [r for r in results if not r[1]]
    for name, ok, msg in results:
        print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" | " + msg) if msg else ""))
    print("TOTAL %d/%d" % (len(results) - len(failed), len(results)))
    print("PASS" if not failed else "FAIL")
    return 0 if not failed else 1


if __name__ == "__main__":
    import sys

    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print("usage: python3 -B -m tasksvc.store --selftest")
    sys.exit(2)
