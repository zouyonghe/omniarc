class OmniArcError(Exception):
    pass


class ValidationError(OmniArcError):
    pass


class PermissionError(OmniArcError):
    pass


class RuntimeError(OmniArcError):
    pass


class ModelError(OmniArcError):
    pass
