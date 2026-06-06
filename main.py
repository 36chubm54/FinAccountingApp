import logging
import os

from app_single_instance import acquire_single_instance

APP_LANGUAGE = "ru"
APP_THEME = "light"


def _read_runtime_env(primary: str, legacy: str, default: str) -> str:
    return str(os.getenv(primary) or os.getenv(legacy) or default)


def run_app() -> bool:
    single_instance = acquire_single_instance()
    if single_instance is None:
        logging.info("[startup] Existing Ledgera instance activated")
        return False

    from gui.i18n import set_language
    from gui.initial_setup import ensure_initial_setup
    from gui.shell.windowing.window import enable_windows_dpi_awareness
    from gui.tkinter_gui import main
    from gui.ui_theme import set_theme

    with single_instance:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
        enable_windows_dpi_awareness(logging.getLogger("gui.shell.windowing.window"))
        set_language(_read_runtime_env("LEDGERA_LANG", "FIN_ACCOUNTING_LANG", APP_LANGUAGE))
        set_theme(_read_runtime_env("LEDGERA_THEME", "FIN_ACCOUNTING_THEME", APP_THEME))
        setup_outcome = ensure_initial_setup()
        if not setup_outcome.should_launch:
            logging.info("[startup] Initial setup cancelled by user")
            return False
        main(
            initial_base_currency=setup_outcome.initial_base_currency,
            single_instance=single_instance,
        )
        return True


if __name__ == "__main__":
    run_app()
