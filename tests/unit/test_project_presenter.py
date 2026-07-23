from PySide6.QtCore import QObject

from openstan.presenters.project_presenter import ProjectPresenter


def test_existing_project_name_change_emits_path_signal() -> None:
    """Changing an imported project's name must not pass its text to a no-arg signal."""
    presenter = ProjectPresenter.__new__(ProjectPresenter)
    QObject.__init__(presenter)
    emissions: list[None] = []
    presenter.path_or_name_changed.connect(lambda: emissions.append(None))

    presenter.on_existing_project_name_changed("Renamed project")

    assert emissions == [None]
