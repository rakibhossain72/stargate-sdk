class StargateError(Exception):
    """Base exception for all Stargate-related errors."""
    pass


class StargateAPIError(StargateError):
    """Exception raised for API-related errors."""
    pass


class StargateTransactionError(StargateError):
    """Exception raised for transaction-related errors."""
    pass


class StargateConfigError(StargateError):
    """Exception raised for configuration-related errors."""
    pass