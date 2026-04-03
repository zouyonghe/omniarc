from __future__ import annotations

import platform

from omniarc.core.errors import PermissionError


def is_macos() -> bool:
    return platform.system() == "Darwin"


def ensure_macos_ready() -> None:
    if not is_macos():
        raise PermissionError("macOS runtime requires Darwin")
