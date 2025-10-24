"""Compatibility shim exposing the ``src/chart_mcp`` package without installation."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

_SRC_PACKAGE = Path(__file__).resolve().parent.parent / "src" / "chart_mcp"

if not _SRC_PACKAGE.exists():  # pragma: no cover - defensive guard for corrupted checkouts
    raise ModuleNotFoundError("Expected 'src/chart_mcp' package alongside shim")

_LOADER = importlib.machinery.SourceFileLoader(
    __name__, str(_SRC_PACKAGE / "__init__.py")
)
_SPEC = importlib.util.spec_from_loader(
    __name__, _LOADER, origin=str(_SRC_PACKAGE / "__init__.py"), is_package=True
)

if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - should never happen
    raise ImportError("Unable to create import spec for chart_mcp package")

_MODULE = importlib.util.module_from_spec(_SPEC)
_MODULE.__path__ = [str(_SRC_PACKAGE)]
sys.modules[__name__] = _MODULE
_SPEC.loader.exec_module(_MODULE)

# Mirror the loaded module's namespace so imports referencing this shim behave identically.
globals().update(_MODULE.__dict__)

