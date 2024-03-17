import os

COMMAND_NOT_FOUND_ERROR = """Command not found."""
CURRENCY_NOT_FOUND_ERROR = """{} Currency is not found, please try again."""
EMPTY_LIST_PROVIDED_ERROR = """Data provided is empty."""

DEFAULT_GST_RATE = os.environ.get("GST_RATE", 0.09)
DEFAULT_SVC_CHARGE_RATE = os.environ.get("SVC_CHARGE", 0.1)
