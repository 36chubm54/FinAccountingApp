import logging
import os
import subprocess
import platform
from typing import Optional

logger = logging.getLogger(__name__)


def open_in_file_manager(path: Optional[str]) -> None:
    """Open folder in OS file manager in a cross-platform way."""
    try:
        if not path:
            return
        if os.name == "nt":
            os.startfile(path)
            return
        system = platform.system()
        if system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            # Assume Linux/Unix
            subprocess.Popen(["xdg-open", path])
    except Exception:
        logger.exception("Failed to open file manager for %s", path)


def safe_destroy(window) -> None:
    try:
        if window is not None:
            window.destroy()
    except Exception:
        logger.debug("Ignored window destroy exception", exc_info=True)


def safe_focus(window) -> None:
    try:
        if window is not None and window.winfo_exists():
            window.deiconify()
            window.lift()
            window.focus_force()
    except Exception:
        logger.debug("Ignored GUI focus exception", exc_info=True)
