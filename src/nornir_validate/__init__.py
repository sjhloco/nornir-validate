from importlib.metadata import PackageNotFoundError, version

from nornir_validate.core import (
    generate_val_file,
    print_result_gvf,
    print_val_result,
    validate,
)

try:
    __version__ = version("nornir-validate")
except PackageNotFoundError:
    # Package isn't installed yet (dev mode)
    __version__ = "0.0.0"

__all__ = ["validate", "print_val_result", "generate_val_file", "print_result_gvf"]
