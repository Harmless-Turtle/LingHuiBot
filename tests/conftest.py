from pathlib import Path
import sys
import os

import nonebot

# Ensure the project root (containing 'src') is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force working directory to project root to make plugin path resolution stable
try:
    os.chdir(ROOT)
except Exception:
    pass

# Initialize NoneBot for the test session and load local plugins only
try:
    nonebot.get_driver()
except ValueError:
    nonebot.init()

# Prefer loading only local plugins to avoid heavy third-party plugins during tests
plugins_dir = ROOT / "src" / "plugins"
if plugins_dir.is_dir():
    nonebot.load_plugins(str(plugins_dir))
else:
    # Fallback: load from pyproject.toml if available
    pyproject = ROOT / "pyproject.toml"
    if pyproject.is_file():
        nonebot.load_from_toml(str(pyproject))

