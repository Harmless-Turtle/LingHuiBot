from pathlib import Path


def test_nonebot_init_and_load_from_pyproject_toml():
    import nonebot
    from nonebot.plugin import get_loaded_plugins

    # Initialize NoneBot only if not already initialized
    try:
        nonebot.get_driver()
    except ValueError:
        nonebot.init()

    # If plugins already loaded by conftest, skip re-loading
    if not get_loaded_plugins():
        toml_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
        assert toml_path.is_file(), f"pyproject.toml not found at {toml_path}"
        nonebot.load_from_toml(str(toml_path))

    # Basic sanity check: some plugins should be loaded
    assert len(get_loaded_plugins()) > 0, "No plugins were loaded from pyproject.toml"
