"""Tests for the retain-descriptions feature in AnonymisePresenter.

Covers:
  - _update_retain_description_visibility (show/hide checkbox based on table data)
  - _AnonymiseWorker receiving retain_descriptions parameter
  - _update_retain_description_status (status label marker)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from openstan.presenters.anonymise_presenter import (
    AlwaysAnonymiseConfig,
    AnonymisePresenter,
    _AnonymiseWorker,
)

# ---------------------------------------------------------------------------
# _AnonymiseWorker — retain_descriptions parameter
# ---------------------------------------------------------------------------


class TestAnonymiseWorkerRetainDescriptions:
    """Verify that _AnonymiseWorker threads retain_descriptions through to bsa."""

    def test_worker_stores_retain_descriptions_false(self, tmp_path: Path) -> None:
        worker = _AnonymiseWorker(
            input_path=tmp_path / "test.pdf",
            retain_descriptions=False,
        )
        assert worker._retain_descriptions is False

    def test_worker_stores_retain_descriptions_true(self, tmp_path: Path) -> None:
        worker = _AnonymiseWorker(
            input_path=tmp_path / "test.pdf",
            retain_descriptions=True,
        )
        assert worker._retain_descriptions is True

    def test_worker_batch_stores_retain_descriptions(self, tmp_path: Path) -> None:
        worker = _AnonymiseWorker(
            input_paths=[tmp_path / "a.pdf", tmp_path / "b.pdf"],
            retain_descriptions=True,
        )
        assert worker._retain_descriptions is True

    @patch("openstan.presenters.anonymise_presenter.bsa")
    def test_worker_passes_retain_descriptions_to_bsa_single(
        self, mock_bsa: MagicMock, tmp_path: Path
    ) -> None:
        """Single-file mode should pass retain_descriptions to bsa.anonymise_pdf."""
        input_pdf = tmp_path / "test.pdf"
        input_pdf.write_text("fake pdf")
        mock_bsa.anonymise_pdf.return_value = tmp_path / "anonymised_test.pdf"

        worker = _AnonymiseWorker(
            input_path=input_pdf,
            always_anonymise_path=tmp_path / "always.toml",
            never_anonymise_path=tmp_path / "never.toml",
            retain_descriptions=True,
        )
        worker.run()

        mock_bsa.anonymise_pdf.assert_called_once_with(
            input_pdf,
            always_anonymise_path=tmp_path / "always.toml",
            never_anonymise_path=tmp_path / "never.toml",
            retain_descriptions=True,
        )

    @patch("openstan.presenters.anonymise_presenter.bsa")
    def test_worker_passes_retain_descriptions_to_bsa_batch(
        self, mock_bsa: MagicMock, tmp_path: Path
    ) -> None:
        """Batch mode should pass retain_descriptions to each bsa.anonymise_pdf call."""
        pdf_a = tmp_path / "a.pdf"
        pdf_b = tmp_path / "b.pdf"
        pdf_a.write_text("fake a")
        pdf_b.write_text("fake b")
        mock_bsa.anonymise_pdf.side_effect = lambda p, **kw: tmp_path / f"anon_{p.name}"

        worker = _AnonymiseWorker(
            input_paths=[pdf_a, pdf_b],
            always_anonymise_path=tmp_path / "always.toml",
            retain_descriptions=True,
        )
        worker.run()

        assert mock_bsa.anonymise_pdf.call_count == 2
        for call in mock_bsa.anonymise_pdf.call_args_list:
            assert call.kwargs.get("retain_descriptions") is True


# ---------------------------------------------------------------------------
# AlwaysAnonymiseConfig — from_toml with replacements
# ---------------------------------------------------------------------------


class TestAlwaysAnonymiseConfig:
    """Verify AlwaysAnonymiseConfig loads correctly from TOML."""

    def test_empty_file_returns_empty_config(self, tmp_path: Path) -> None:
        toml_path = tmp_path / "always_anonymise.toml"
        toml_path.write_text("# No replacements\n")
        config = AlwaysAnonymiseConfig.from_toml(toml_path)
        assert config.replacements == {}

    def test_file_with_replacements(self, tmp_path: Path) -> None:
        toml_path = tmp_path / "always_anonymise.toml"
        toml_path.write_text('"John Smith" = "J. Smith"\n"123456" = "000000"\n')
        config = AlwaysAnonymiseConfig.from_toml(toml_path)
        assert config.replacements == {"John Smith": "J. Smith", "123456": "000000"}

    def test_missing_file_returns_empty_config(self, tmp_path: Path) -> None:
        config = AlwaysAnonymiseConfig.from_toml(tmp_path / "nonexistent.toml")
        assert config.replacements == {}


# ---------------------------------------------------------------------------
# Visibility logic — use a plain-class stand-in with the same attributes
# ---------------------------------------------------------------------------


class _PresenterStub:
    """Minimal stand-in for AnonymisePresenter — holds only the attributes
    needed by the visibility and status methods."""

    def __init__(self, dialog: MagicMock, retain_descriptions: bool = False) -> None:
        self.dialog = dialog
        self._retain_descriptions = retain_descriptions

    # Bind the real methods from the class (type ignore: stub is not AnonymisePresenter)
    _update_retain_description_visibility = (  # type: ignore[assignment]
        AnonymisePresenter._update_retain_description_visibility
    )
    _update_retain_description_status = (  # type: ignore[assignment]
        AnonymisePresenter._update_retain_description_status
    )


class TestRetainDescriptionVisibility:
    """Test _update_retain_description_visibility with a stub presenter."""

    def test_checkbox_hidden_when_table_empty(self) -> None:
        dialog = MagicMock()
        dialog.get_always_table_data.return_value = {}
        stub = _PresenterStub(dialog, retain_descriptions=False)

        stub._update_retain_description_visibility()  # type: ignore[bad-argument-type]

        dialog.checkbox_retain_descriptions.setVisible.assert_called_with(False)
        dialog.help_retain_descriptions.setVisible.assert_called_with(False)

    def test_checkbox_visible_when_table_has_data(self) -> None:
        dialog = MagicMock()
        dialog.get_always_table_data.return_value = {"John": "J. Smith"}
        stub = _PresenterStub(dialog, retain_descriptions=False)

        stub._update_retain_description_visibility()  # type: ignore[bad-argument-type]

        dialog.checkbox_retain_descriptions.setVisible.assert_called_with(True)
        dialog.help_retain_descriptions.setVisible.assert_called_with(True)

    def test_checkbox_unchecked_when_table_cleared(self) -> None:
        dialog = MagicMock()
        dialog.checkbox_retain_descriptions.isChecked.return_value = True
        dialog.get_always_table_data.return_value = {}
        stub = _PresenterStub(dialog, retain_descriptions=True)

        stub._update_retain_description_visibility()  # type: ignore[bad-argument-type]

        dialog.checkbox_retain_descriptions.setChecked.assert_called_with(False)
        assert stub._retain_descriptions is False

    def test_checkbox_not_unchecked_when_still_has_data(self) -> None:
        dialog = MagicMock()
        dialog.get_always_table_data.return_value = {"John": "J. Smith"}
        stub = _PresenterStub(dialog, retain_descriptions=True)

        stub._update_retain_description_visibility()  # type: ignore[bad-argument-type]

        dialog.checkbox_retain_descriptions.setChecked.assert_not_called()
        assert stub._retain_descriptions is True


# ---------------------------------------------------------------------------
# Status label update
# ---------------------------------------------------------------------------


class TestRetainDescriptionStatus:
    """Test _update_retain_description_status appends marker to status label."""

    def test_appends_marker_when_enabled(self) -> None:
        dialog = MagicMock()
        dialog.label_status.text.return_value = "Ready"
        stub = _PresenterStub(dialog, retain_descriptions=True)

        stub._update_retain_description_status()  # type: ignore[bad-argument-type]

        dialog.label_status.setText.assert_called_with(
            "Ready [Retain descriptions: ON]"
        )

    def test_no_marker_when_disabled(self) -> None:
        dialog = MagicMock()
        dialog.label_status.text.return_value = "Ready"
        stub = _PresenterStub(dialog, retain_descriptions=False)

        stub._update_retain_description_status()  # type: ignore[bad-argument-type]

        dialog.label_status.setText.assert_called_with("Ready")

    def test_strips_existing_marker_before_appending(self) -> None:
        dialog = MagicMock()
        dialog.label_status.text.return_value = "Done [Retain descriptions: ON]"
        stub = _PresenterStub(dialog, retain_descriptions=True)

        stub._update_retain_description_status()  # type: ignore[bad-argument-type]

        dialog.label_status.setText.assert_called_with("Done [Retain descriptions: ON]")
