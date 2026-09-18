"""用于以自动模式运行示例的辅助工具。

当设置了环境变量 ``EXAMPLES_INTERACTIVE_MODE=auto`` 时，这些辅助函数会提供
确定性的输入和确认，使示例无需手动交互即可运行。这些辅助函数刻意保持轻量，
以避免为示例代码引入额外依赖。
"""

from __future__ import annotations

import os


def is_auto_mode() -> bool:
    """Return True when examples should bypass interactive prompts."""
    return os.environ.get("EXAMPLES_INTERACTIVE_MODE", "").lower() == "auto"


def input_with_fallback(prompt: str, fallback: str) -> str:
    """Return the fallback text in auto mode, otherwise defer to input()."""
    if is_auto_mode():
        print(f"[auto-input] {prompt.strip()} -> {fallback}")
        return fallback
    return input(prompt)


def confirm_with_fallback(prompt: str, default: bool = True) -> bool:
    """Return default in auto mode; otherwise ask the user."""
    if is_auto_mode():
        choice = "yes" if default else "no"
        print(f"[auto-confirm] {prompt.strip()} -> {choice}")
        return default

    answer = input(prompt).strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}