import json
import sys
import types
import unittest
import tempfile
import importlib.util
from pathlib import Path


def load_utils_with_mocks():
    """
    在导入 src/plugins/utils.py 前，向 sys.modules 注入必要的桩模块，
    以避免项目未安装的第三方依赖导致导入失败。
    """
    # nonebot 主模块及其属性
    nonebot_mod = types.ModuleType("nonebot")

    class _DummyLogger:
        def exception(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

    def _get_driver():
        class _Cfg:
            pass

        class _Driver:
            config = _Cfg()

        return _Driver()

    nonebot_mod.logger = _DummyLogger()
    nonebot_mod.get_driver = _get_driver
    sys.modules["nonebot"] = nonebot_mod

    # 子模块：nonebot.adapters.onebot.v11
    adapters_mod = types.ModuleType("nonebot.adapters")
    onebot_mod = types.ModuleType("nonebot.adapters.onebot")
    v11_mod = types.ModuleType("nonebot.adapters.onebot.v11")

    class Message(str):
        pass

    class MessageEvent:
        message_id = 0

    class MessageSegment:
        @staticmethod
        def reply(x):
            return f"reply({x})"

        @staticmethod
        def image(x):
            return f"image({x})"

        @staticmethod
        def text(x):
            return f"text({x})"

        @staticmethod
        def node_custom(user_id, nickname, content):
            return f"node({user_id},{nickname},{content})"

    v11_mod.Message = Message
    v11_mod.MessageEvent = MessageEvent
    v11_mod.MessageSegment = MessageSegment
    sys.modules["nonebot.adapters"] = adapters_mod
    sys.modules["nonebot.adapters.onebot"] = onebot_mod
    sys.modules["nonebot.adapters.onebot.v11"] = v11_mod

    # 子模块：nonebot.exception
    exception_mod = types.ModuleType("nonebot.exception")

    class MatcherException(Exception):
        pass

    exception_mod.MatcherException = MatcherException
    sys.modules["nonebot.exception"] = exception_mod

    # 子模块：nonebot.matcher
    matcher_mod = types.ModuleType("nonebot.matcher")

    class Matcher:
        pass

    matcher_mod.Matcher = Matcher
    sys.modules["nonebot.matcher"] = matcher_mod

    # httpx / httpcore（仅用于类型判断）
    httpx_mod = types.ModuleType("httpx")

    class ReadTimeout(Exception):
        pass

    httpx_mod.ReadTimeout = ReadTimeout
    sys.modules["httpx"] = httpx_mod

    httpcore_mod = types.ModuleType("httpcore")

    class RemoteProtocolError(Exception):
        pass

    httpcore_mod.RemoteProtocolError = RemoteProtocolError
    sys.modules["httpcore"] = httpcore_mod

    # 计算被测模块路径：项目根/tests/.. -> 项目根/src/plugins/utils.py
    module_path = Path(__file__).resolve().parents[1] / "src" / "plugins" / "utils.py"
    spec = importlib.util.spec_from_file_location("plugins_utils", str(module_path))
    utils_module = importlib.util.module_from_spec(spec)
    sys.modules["plugins_utils"] = utils_module  # 名称占位，便于相互引用
    assert spec and spec.loader, "无法创建模块加载器"
    spec.loader.exec_module(utils_module)
    return utils_module


class HandleJsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.utils = load_utils_with_mocks()

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_read_valid_json(self):
        data = {"a": 1, "b": "测试", "c": [1, 2, 3]}
        f = self.tmp_path / "valid.json"
        f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        result = self.utils.handle_json(f, "r")
        self.assertEqual(result, data)

    def test_write_valid_json(self):
        f = self.tmp_path / "write.json"
        payload = {"msg": "你好", "n": 42}
        ret = self.utils.handle_json(f, "w", payload)
        self.assertIsNone(ret)
        content = json.loads(f.read_text(encoding="utf-8"))
        self.assertEqual(content, payload)

    def test_invalid_mode_raises_value_error(self):
        f = self.tmp_path / "x.json"
        with self.assertRaises(ValueError):
            self.utils.handle_json(f, "x")

    def test_write_without_data_raises_value_error(self):
        f = self.tmp_path / "w.json"
        with self.assertRaises(ValueError):
            self.utils.handle_json(f, "w")

    def test_read_file_not_found_raises_file_not_found_error(self):
        f = self.tmp_path / "not_exists.json"
        with self.assertRaises(FileNotFoundError):
            self.utils.handle_json(f, "r")

    def test_read_invalid_json_raises_value_error(self):
        f = self.tmp_path / "bad.json"
        f.write_text("{bad json", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.utils.handle_json(f, "r")


if __name__ == "__main__":
    unittest.main()
