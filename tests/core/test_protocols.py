from omniarc.runtimes.base.capabilities import CapabilitySet


def test_capability_set_reports_support() -> None:
    caps = CapabilitySet(values={"screen_capture", "open_application"})
    assert caps.supports("screen_capture") is True
    assert caps.supports("ocr") is False
