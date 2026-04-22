"""Tests for scripts/export_reward_plot.py (no network)."""

import json
from pathlib import Path

import pytest

from scripts.export_reward_plot import (
    build_figure,
    export_plot,
    load_rewards_from_file,
)


def test_load_rewards_from_file_list(tmp_path: Path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps([0.2, 0.3, 0.5]))
    rewards, rolling, baseline = load_rewards_from_file(p)
    assert rewards == [0.2, 0.3, 0.5]
    assert len(rolling) == len(rewards)
    assert baseline == 0.265


def test_load_rewards_from_file_missing(tmp_path: Path):
    rewards, rolling, baseline = load_rewards_from_file(tmp_path / "nope.json")
    assert rewards == []
    assert rolling == []


def test_load_rewards_from_file_invalid_json(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("not-json")
    rewards, rolling, _ = load_rewards_from_file(p)
    assert rewards == []
    assert rolling == []


def test_export_plot_writes_png(tmp_path: Path):
    out = tmp_path / "out.png"
    export_plot([0.1, 0.4, 0.6], [0.1, 0.25, 0.37], 0.265, out)
    assert out.exists()
    assert out.stat().st_size > 1000


def test_build_figure_empty_no_crash(tmp_path: Path):
    fig = build_figure([], [], 0.265)
    p = tmp_path / "empty.png"
    fig.savefig(p)
    assert p.stat().st_size > 500
    import matplotlib.pyplot as plt

    plt.close(fig)
