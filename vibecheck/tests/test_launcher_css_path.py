from __future__ import annotations

import importlib
from pathlib import Path

from vibecheck import launcher


def test_vibecheck_app_reuses_base_css_path() -> None:
    base_css_path = getattr(launcher._BaseVibeApp, "CSS_PATH", None)
    if not isinstance(base_css_path, str):
        assert launcher.VibeCheckApp.CSS_PATH is None
        return

    base_module = importlib.import_module(launcher._BaseVibeApp.__module__)
    module_file = Path(base_module.__file__).resolve()
    expected = str(module_file.with_name(base_css_path))
    assert launcher.VibeCheckApp.CSS_PATH == expected
