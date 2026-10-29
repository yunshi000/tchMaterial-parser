# -*- coding: utf-8 -*-
# 内置登录窗口：用 pywebview 打开平台页面，登录成功后自动读取 localStorage 里的
# 凭据（取值规则与 ui/token_window.py 的控制台脚本一致），免去手动复制 JSON。
#
# 选型说明：本项目要求 Python 3.10+，cefpython3 已停止维护且没有对应版本的
# 二进制轮子；pywebview 在 Windows 上使用系统 Edge WebView2（常青内核），
# Linux 上使用 WebKitGTK，macOS 上使用 WKWebView，各平台均能正常渲染登录页。
# pywebview 的 GUI 循环独占主线程运行，调用前需先隐藏 Tk 窗口，结束后恢复。

import threading, time

from .auth import format_token_json, parse_token_input

LOGIN_PAGE_URL = "https://basic.smartedu.cn/" # 平台首页，登录后凭据写在该域的 localStorage
LOGIN_WINDOW_TITLE = "国家中小学智慧教育平台 登录"
POLL_INTERVAL_SECONDS = 1.0 # 凭据写入 localStorage 的轮询间隔
POLL_TIMEOUT_SECONDS = 300.0 # 登录等待超时，超时后自动关闭登录窗口

# 与 ui/token_window.py 的 ACCESS_TOKEN_SCRIPT 保持相同取值规则：只认
# ND_UC_AUTH-...&token，不能取到同前缀的 sdk_cache（#89）。
# 未登录时返回 null，登录后返回凭据 JSON 字符串。
EXTRACT_CREDENTIALS_SCRIPT = """\
(function () {
  const authKey = Object.keys(localStorage).find(
    key => /^ND_UC_AUTH-[^&]+&[^&]+&token$/.test(key),
  );
  if (!authKey) return null;
  const tokenData = JSON.parse(localStorage.getItem(authKey));
  const { access_token, mac_key, diff } = JSON.parse(tokenData.value);
  return JSON.stringify({ access_token, mac_key, diff });
})();"""

class BrowserLoginError(RuntimeError):
    """内置登录窗口不可用（缺少 pywebview 或浏览器内核无法启动）。"""

def is_available() -> bool: # 内置登录窗口是否可用，仅检查 pywebview 是否已安装
    try:
        import webview # noqa: F401
    except ImportError:
        return False
    return True

def format_credential_result(raw: str | None) -> str | None:
    """校验登录窗口取到的凭据并格式化为三项 JSON；未取到（用户关闭窗口或超时）返回 None。"""
    if not raw:
        return None
    credentials = parse_token_input(raw) # 复用粘贴内容的校验，无效时抛出 TokenInputError
    return format_token_json(credentials.access_token, credentials.mac_key, credentials.diff)

def acquire_credentials() -> str | None:
    """打开内置登录窗口并等待，直到自动取到凭据、用户关闭窗口或登录超时。

    返回凭据 JSON 字符串；未取到时返回 None。此函数会阻塞直至登录窗口关闭，
    调用方应先隐藏 Tk 窗口，并在返回后恢复。
    """
    try:
        import webview
    except ImportError:
        raise BrowserLoginError("内置登录窗口需要 pywebview 支持，请先执行 pip install pywebview") from None

    closed = threading.Event()
    result: list[str] = [] # 借助列表在闭包之间传递取到的凭据

    window = webview.create_window(
        LOGIN_WINDOW_TITLE,
        LOGIN_PAGE_URL,
        width=1080,
        height=760,
        min_size=(640, 480),
    )
    window.events.closed += closed.set

    def poll_credentials() -> None: # 登录成功后凭据才会写入 localStorage，轮询读取
        deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if closed.is_set():
                return
            try:
                raw = window.evaluate_js(EXTRACT_CREDENTIALS_SCRIPT)
            except Exception: # 页面尚未加载完成或正在跳转时读取会失败，等待下次轮询
                raw = None
            if raw:
                result.append(raw)
                window.destroy()
                return
            time.sleep(POLL_INTERVAL_SECONDS)
        if not closed.is_set():
            window.destroy() # 超时自动关闭，避免窗口一直挂起

    try:
        webview.start(poll_credentials) # 阻塞直至登录窗口关闭
    except Exception as error:
        raise BrowserLoginError(f"登录窗口启动失败：{error}") from None
    return result[0] if result else None
