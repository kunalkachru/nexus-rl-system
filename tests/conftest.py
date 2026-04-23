"""Pytest fixtures — isolate adaptive curriculum state between tests."""

import pytest


@pytest.fixture(autouse=True)
def _reset_global_curriculum():
    from server import global_curriculum

    global_curriculum.reset()
    yield
    global_curriculum.reset()
