import pytest


def pytest_collection_modifyitems(config, items):
    """每个测试必须标记为 unit 或 integration，避免分类遗漏。"""
    unmarked = [
        item.nodeid for item in items
        if not any(item.get_closest_marker(m) for m in ("unit", "integration"))
    ]
    if unmarked:
        raise pytest.UsageError(
            "Tests must be marked 'unit' or 'integration':\n  " + "\n  ".join(unmarked)
        )
