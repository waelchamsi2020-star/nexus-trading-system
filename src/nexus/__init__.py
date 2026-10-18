"""Quant Trading AI local demo trading research and execution system."""
from importlib import import_module as _import_module

__version__ = "0.7.0"

# Establish shared primitives before callers can import a specialist first.
_import_module('.strategies', __name__)
