"""Domain-level errors shared across services (not tied to any one entity)."""


class NotFoundError(Exception):
    """Raised when a requested entity (meter, reading, ...) does not exist."""


class EmailAlreadyRegisteredError(Exception):
    """Raised on signup when the email is already tied to an account."""


class InvalidCredentialsError(Exception):
    """Raised on login when the email/password combination doesn't match."""


class TariffConfigurationError(Exception):
    """Raised when tariff/subsidy configuration is missing or incomplete -
    e.g. no subsidy rule covers a given consumption level, or a rule
    group's slabs don't fully cover the chargeable-units range. This is a
    configuration problem (something an admin must fix), not a user input
    mistake.
    """
