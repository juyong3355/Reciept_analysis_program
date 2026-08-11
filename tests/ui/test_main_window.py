from receipt_mvp.ui.main_window import MainWindow


def test_main_window_file_list_workflow(qtbot, tmp_path) -> None:
    first = tmp_path / "one.pdf"
    second = tmp_path / "two.png"
    first.write_bytes(b"pdf")
    second.write_bytes(b"png")
    window = MainWindow()
    qtbot.addWidget(window)
    window.add_files([str(first), str(second), str(first)])
    assert len(window.file_paths) == 2
    assert window.analyze_button.isEnabled()
    window.file_list.selectAll()
    window.remove_selected_files()
    assert not window.file_paths
    assert not window.analyze_button.isEnabled()

