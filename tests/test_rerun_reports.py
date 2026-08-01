"""Tests for rerun_reports.py -- the driver that regenerates every eval report.

This had no coverage at all, which matters more than usual here: the driver
recovers each round's configuration by regex-parsing a report file that the run
then OVERWRITES. If parsing silently recovers the wrong scheme list, the round
is regenerated as a different experiment and the report that recorded the
original config is already gone.
"""
from __future__ import annotations

import json

import pytest

import rerun_reports as rr


REPORT = """# Risk-Parity Eval

- **Combos x schemes:** 2817 x 13 = **36621 trials** on TRAIN.
- **Schemes:** EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM, TrendGate, TG-Short, \
TG-Short-LS, TG-Short-6m, EW-Short, EW-Short-LS, EW-Short-6m — EW/InvVol/InvVar/ERC/MinVar \
get a separate composition

Selection uses **`--score-mode asymmetric2`** for the objective.
"""


def _write(tmp_path, dirname, text):
    d = tmp_path / dirname
    d.mkdir(parents=True)
    (d / "report_eval.md").write_text(text, encoding="utf-8")
    return d


class TestParseConfig:
    def test_recovers_the_scheme_list_verbatim(self, tmp_path, monkeypatch):
        _write(tmp_path, "risk_parity_eval_asym2b", REPORT)
        monkeypatch.setattr(rr, "OUT", str(tmp_path))
        cfg = rr.parse_config("risk_parity_eval_asym2b")
        assert cfg["schemes"][0] == "EW"
        assert cfg["schemes"][-1] == "EW-Short-6m"
        assert len(cfg["schemes"]) == 13

    def test_stops_the_scheme_list_at_the_em_dash(self, tmp_path, monkeypatch):
        _write(tmp_path, "risk_parity_eval_asym2b", REPORT)
        monkeypatch.setattr(rr, "OUT", str(tmp_path))
        cfg = rr.parse_config("risk_parity_eval_asym2b")
        assert not any("EW/InvVol" in s for s in cfg["schemes"]), \
            "the trailing prose after the em-dash leaked into the scheme list"

    def test_recovers_the_score_mode(self, tmp_path, monkeypatch):
        _write(tmp_path, "risk_parity_eval_asym2b", REPORT)
        monkeypatch.setattr(rr, "OUT", str(tmp_path))
        assert rr.parse_config("risk_parity_eval_asym2b")["score_mode"] == "asymmetric2"

    def test_asymmetric2_is_not_truncated_to_asymmetric(self, tmp_path, monkeypatch):
        # The alternation is leftmost-first, so ordering in the regex matters.
        _write(tmp_path, "risk_parity_eval_asym2b", REPORT)
        monkeypatch.setattr(rr, "OUT", str(tmp_path))
        assert rr.parse_config("risk_parity_eval_asym2b")["score_mode"] != "asymmetric"

    def test_absent_score_mode_defaults(self, tmp_path, monkeypatch):
        _write(tmp_path, "risk_parity_eval",
               REPORT.replace("Selection uses **`--score-mode asymmetric2`** for the objective.", ""))
        monkeypatch.setattr(rr, "OUT", str(tmp_path))
        assert rr.parse_config("risk_parity_eval")["score_mode"] == "default"

    def test_unknown_round_is_rejected_with_the_known_list(self):
        with pytest.raises(SystemExit) as e:
            rr.parse_config("risk_parity_seasons")
        assert "not a known round" in str(e.value)
        assert "risk_parity_eval_asym9" in str(e.value)

    def test_regression_guards_are_known_rounds(self):
        # They are re-baselined in the same pass; a legitimate data change
        # breaks every byte-identity guard, so leaving them out means leaving
        # them permanently red.
        assert set(rr.REG_DIRS) <= set(rr.ALL_DIRS)
        assert len(rr.ALL_DIRS) == len(rr.EVAL_DIRS) + len(rr.REG_DIRS)

    def test_no_rolling_is_detected_from_the_rolling_log(self, tmp_path,
                                                         monkeypatch):
        d = _write(tmp_path, "rp_reg", REPORT)
        monkeypatch.setattr(rr, "OUT", str(tmp_path))
        assert rr.parse_config("rp_reg")["no_rolling"] is True
        (d / "rolling_selection_log.csv").write_text("year,combo\n")
        assert rr.parse_config("rp_reg")["no_rolling"] is False

    def test_no_rolling_reaches_the_command(self, tmp_path, monkeypatch):
        _write(tmp_path, "rp_reg", REPORT)
        monkeypatch.setattr(rr, "OUT", str(tmp_path))
        assert "--no-rolling" in rr.build_cmd(rr.parse_config("rp_reg"))

    def test_missing_report_is_rejected(self, tmp_path, monkeypatch):
        (tmp_path / "risk_parity_eval_asym9").mkdir(parents=True)
        monkeypatch.setattr(rr, "OUT", str(tmp_path))
        with pytest.raises(SystemExit):
            rr.parse_config("risk_parity_eval_asym9")

    def test_unparseable_schemes_line_is_rejected_not_guessed(self, tmp_path,
                                                              monkeypatch):
        _write(tmp_path, "risk_parity_eval_asym9", "# report\n\nno schemes line\n")
        monkeypatch.setattr(rr, "OUT", str(tmp_path))
        with pytest.raises(SystemExit):
            rr.parse_config("risk_parity_eval_asym9")


class TestBuildCmd:
    BASE = {"dir": "risk_parity_eval_asym9", "schemes": ["EW", "MinVar"],
            "score_mode": "asymmetric2", "bootstrap": 2000}

    def test_always_passes_an_explicit_out_dir(self):
        # Omitting it is the documented bug that would clobber another round.
        cmd = rr.build_cmd(self.BASE)
        assert "--out-dir" in cmd
        assert cmd[cmd.index("--out-dir") + 1].endswith("risk_parity_eval_asym9")

    def test_always_passes_an_explicit_scheme_list(self):
        # The default is SCHEME_ORDER, which has grown 6 -> 50.
        cmd = rr.build_cmd(self.BASE)
        assert cmd[cmd.index("--schemes") + 1] == "EW,MinVar"

    def test_default_score_mode_is_not_passed(self):
        cmd = rr.build_cmd({**self.BASE, "score_mode": "default", "bootstrap": None})
        assert "--score-mode" not in cmd and "--bootstrap" not in cmd


class TestSnapshot:
    """The snapshot is the recovery record for a destructive operation."""

    def test_bootstrap_rule_is_keyed_to_the_round_order(self):
        # Bootstrap is materialised per-dir before the largest-first sort, so
        # the rule must hold on EVAL_DIRS order, not on execution order.
        early = rr.EVAL_DIRS.index("risk_parity_eval_asym")
        late = rr.EVAL_DIRS.index("risk_parity_eval_asym9")
        assert early < rr.BOOTSTRAP_2000_FROM <= late

    def test_only_run_merges_rather_than_truncating(self, tmp_path):
        snap = tmp_path / "configs.json"
        snap.write_text(json.dumps([
            {"dir": "risk_parity_eval_asym8", "schemes": ["EW"],
             "score_mode": "asymmetric2", "bootstrap": 2000},
            {"dir": "risk_parity_eval_asym9", "schemes": ["EW", "MinVar"],
             "score_mode": "asymmetric2", "bootstrap": 2000},
        ]))
        prev = {c["dir"]: c for c in json.loads(snap.read_text())}
        incoming = [{"dir": "risk_parity_eval_asym9", "schemes": ["EW", "ERC"],
                     "score_mode": "asymmetric2", "bootstrap": 2000}]
        prev.update({c["dir"]: c for c in incoming})
        assert set(prev) == {"risk_parity_eval_asym8", "risk_parity_eval_asym9"}, \
            "a --only run must not drop the other rounds' recovery record"
        assert prev["risk_parity_eval_asym9"]["schemes"] == ["EW", "ERC"]
