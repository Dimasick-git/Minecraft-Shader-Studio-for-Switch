class MSSError(Exception):
    """Base user-facing MSS error."""

class ValidationError(MSSError):
    pass

class CompatibilityError(MSSError):
    pass

class ToolchainError(MSSError):
    pass
