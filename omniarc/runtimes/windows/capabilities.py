from __future__ import annotations

from omniarc.runtimes.base.capabilities import CapabilitySet


class WindowsCapabilityProvider:
    def get_capabilities(self) -> CapabilitySet:
        return CapabilitySet(
            values={
                "screen_capture",
                "open_application",
                "powershell",
                "shell",
            }
        )
