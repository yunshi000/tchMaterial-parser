# 内置登录窗口：凭据校验、格式化，以及取值脚本必须指向 ND_UC_AUTH-...&token（#89）。
import json
import unittest

from src.tchmaterial_parser import browser_login
from src.tchmaterial_parser.auth import TokenInputError


class CredentialResultTest(unittest.TestCase):
    def test_formats_valid_credentials(self) -> None:
        raw = '{"access_token":"token","mac_key":"key","diff":"100"}'
        self.assertEqual(
            browser_login.format_credential_result(raw),
            '{\n  "access_token": "token",\n  "mac_key": "key",\n  "diff": 100\n}',
        )

    def test_accepts_quoted_json_from_console_copy(self) -> None:
        raw = json.dumps({"access_token": "token", "mac_key": "key", "diff": 0})
        self.assertIsNotNone(browser_login.format_credential_result(json.dumps(raw)))

    def test_returns_none_when_nothing_captured(self) -> None:
        self.assertIsNone(browser_login.format_credential_result(None))
        self.assertIsNone(browser_login.format_credential_result(""))

    def test_rejects_missing_fields(self) -> None:
        with self.assertRaises(TokenInputError):
            browser_login.format_credential_result('{"access_token":"token"}')


class ExtractScriptTest(unittest.TestCase):
    def test_selects_token_suffix_not_sdk_cache(self) -> None:
        self.assertIn('/^ND_UC_AUTH-[^&]+&[^&]+&token$/.test(key)', browser_login.EXTRACT_CREDENTIALS_SCRIPT)
        self.assertNotIn('key.startsWith("ND_UC_AUTH")', browser_login.EXTRACT_CREDENTIALS_SCRIPT)


if __name__ == "__main__":
    unittest.main()
