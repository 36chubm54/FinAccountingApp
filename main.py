import logging
import sys
from pathlib import Path

# Ensure project package root is on sys.path so imports work regardless of CWD
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from gui.tkinter_gui import main

if __name__ == "__main__":
    # Basic logging configuration for the application
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    main()
