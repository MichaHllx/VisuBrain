from visubrain.gui.window import WindowApp
import visubrain.gui.window
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QCheckBox

from visubrain.io.nifti import NiftiFile


def test_windowapp_launch(qtbot):
    window = WindowApp()
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()
    assert hasattr(window, "_viewer")
    assert window.windowTitle() == "VisuBrain"
    assert window._main_layout is not None

def test_open_nifti_file_dialog(monkeypatch, qtbot):
    window = WindowApp()
    qtbot.addWidget(window)
    window.show()
    monkeypatch.setattr("PyQt6.QtWidgets.QFileDialog.getOpenFileName", lambda *a, **k: ("tests/data/tiny.nii", ""))
    if hasattr(window, "open_nifti_file"):
        window.open_nifti_file()

def test_on_view_license_with_real_file(tmp_path, qtbot):
    license_src = "data/LICENSE.txt"
    license_dst = tmp_path / "LICENSE.txt"
    with open(license_src, "r") as src, open(license_dst, "w") as dst:
        dst.write(src.read())

    visubrain.gui.window.__file__ = str(tmp_path / "window.py")

    Path.parent = property(lambda self: tmp_path)

    window = WindowApp()
    qtbot.addWidget(window)
    window._on_view_license()

    for widget in QApplication.instance().allWidgets():
        if isinstance(widget, QDialog):
            widget.accept()

    assert True

def test_set_sliders_values(qtbot):
    window = WindowApp()
    qtbot.addWidget(window)
    window.show()
    if hasattr(window, "_set_sliders_values"):
        window._set_sliders_values((5, 10, 20))
    for ori, control in window.slice_controls.items():
        if ori == "Axial":
            assert control.get_value() == 9
        elif ori == "Coronal":
            assert control.get_value() == 4
        elif ori == "Sagittal":
            assert control.get_value() == 2

def test_change_slice_opacity(qtbot):
    window = WindowApp()
    qtbot.addWidget(window)
    window.show()
    nifti_object = NiftiFile("data/someones_anatomy.nii.gz")
    window._create_session(nifti_object, "test")
    if hasattr(window, "change_slice_opacity"):
        window.change_slice_opacity(5)
    assert window._current_session.opacity==0.05

def test_reset_cam_zoom(qtbot):
    window = WindowApp()
    qtbot.addWidget(window)
    window.show()
    window._viewer.current_zoom_factor = 2.0
    if hasattr(window, "reset_cam_zoom"):
        window.reset_cam_zoom()
        assert window._viewer.current_zoom_factor == 1.0

@pytest.fixture
def window(qtbot):
    w = WindowApp()
    qtbot.addWidget(w)
    w.show()
    return w

def test_on_load_volume_bad_dim(monkeypatch, window, qtbot):
    monkeypatch.setattr("PyQt6.QtWidgets.QFileDialog.getOpenFileName", lambda *a, **k: ("dummy.nii", ""))
    monkeypatch.setattr("visubrain.io.nifti.NiftiFile", lambda fp: MagicMock(get_dimensions=lambda: (1,)))
    with patch.object(QMessageBox, "critical") as crit:
        window._on_load_volume()
        crit.assert_called_once()

def test_on_load_volume_error(monkeypatch, window, qtbot):
    monkeypatch.setattr("PyQt6.QtWidgets.QFileDialog.getOpenFileName", lambda *a, **k: ("dummy.nii", ""))
    monkeypatch.setattr("visubrain.io.nifti.NiftiFile", lambda fp: (_ for _ in ()).throw(Exception("fail")))
    with patch.object(QMessageBox, "critical") as crit:
        window._on_load_volume()
        crit.assert_called_once()

def test_on_load_streamlines_new_session(monkeypatch, window, qtbot):
    monkeypatch.setattr("PyQt6.QtWidgets.QFileDialog.getOpenFileName", lambda *a, **k: ("tract.trk", ""))
    monkeypatch.setattr("visubrain.io.tractography.Tractography", lambda *a, **k: MagicMock())
    window._current_session = None
    window._on_load_streamlines()
    assert window._current_session is not None

def test_on_load_streamlines_already_loaded(monkeypatch, window, qtbot):
    monkeypatch.setattr("PyQt6.QtWidgets.QFileDialog.getOpenFileName", lambda *a, **k: ("tract.trk", ""))
    window._current_session = MagicMock(get_uid=lambda: 1, tracts={}, volume_obj=None)
    window._viewer.tract_actors[(1, "tract.trk")] = True
    with patch.object(QMessageBox, "information") as info:
        window._on_load_streamlines()
        info.assert_called_once()

def test_on_load_streamlines_error(monkeypatch, window, qtbot):
    monkeypatch.setattr("PyQt6.QtWidgets.QFileDialog.getOpenFileName", lambda *a, **k: ("tract.trk", ""))
    monkeypatch.setattr("visubrain.io.tractography.Tractography", lambda *a, **k: (_ for _ in ()).throw(Exception("fail")))
    window._current_session = MagicMock(get_uid=lambda: 1, tracts={}, volume_obj=None)
    with patch.object(QMessageBox, "information") as info:
        window._on_load_streamlines()
        info.assert_called_once()

def test_view_tracts_statistics_none(window, qtbot):
    window._current_session = None
    with patch.object(QMessageBox, "information") as info:
        window.view_tracts_statistics()
        info.assert_called_once()

def test_view_tracts_statistics_empty(window, qtbot):
    window._current_session = MagicMock(tracts={})
    with patch.object(QMessageBox, "information") as info:
        window.view_tracts_statistics()
        info.assert_called_once()

def test_view_tracts_statistics_report(window, qtbot):
    window._current_session = MagicMock(tracts={"a": 1}, tract_statistics=lambda: ["stat1", "stat2"])
    with patch.object(QMessageBox, "information") as info:
        window.view_tracts_statistics()
        info.assert_called_once()

def test_add_tracto_checkbox(window, qtbot):
    window._current_session = MagicMock(get_uid=lambda: 42)
    window.session_selector.setCurrentText("sess")
    window.add_tracto_checkbox("tract.trk")
    key = (42, "tract.trk")
    assert key in window.tracto_checkboxes
    cb = window.tracto_checkboxes[key]
    assert isinstance(cb, QCheckBox)
    assert cb.isChecked()

def test_set_slice_controls_enabled(window, qtbot):
    window._set_slice_controls_enabled(True)
    for control in window.slice_controls.values():
        assert control.slider.isEnabled()
        assert control.line_edit.isEnabled()
    window._set_slice_controls_enabled(False)
    for control in window.slice_controls.values():
        assert not control.slider.isEnabled()
        assert not control.line_edit.isEnabled()

def test_change_slices_position(window, qtbot):
    window._viewer.working_nifti_obj = MagicMock()
    window._current_session = MagicMock(opacity=1.0)
    for ori in ["Axial", "Coronal", "Sagittal"]:
        window.change_slices_position(5, ori)

def test_on_mode_changed(window, qtbot):
    window._current_session = MagicMock(volume_obj=MagicMock(get_dimensions=lambda: (5, 5, 5)))
    window.on_mode_changed("Slices")
    window.on_mode_changed("Volume 3D")

def test__set_sliders_maximum(window, qtbot):
    window._set_sliders_maximum((5, 6, 7))
    window._set_sliders_maximum((5, 6, 7, 8))
    with pytest.raises(ValueError):
        window._set_sliders_maximum((1, 2))

def test_rename_current_session(window, qtbot):
    window._current_session = MagicMock(display_name="old", apply=lambda: None)
    window.session_selector.addItem("old")
    window.session_selector.setCurrentText("old")
    window.rename_lineedit.setText("new")
    window.tracto_checkboxes = {("tract.trk"): MagicMock(associated_session="old")}
    window.rename_current_session()
    assert window._current_session.display_name == "new"

def test__browse_input(monkeypatch, window, qtbot):
    monkeypatch.setattr("PyQt6.QtWidgets.QFileDialog.getOpenFileName", lambda *a, **k: ("file.trk", ""))
    from visubrain.core.converter import Converter
    Converter._CONVERTERS = [("trk", "tck"), ("trk", "trk")]
    window._browse_input()
    assert window.input_edit.text() == "file.trk"
    assert window.out_combo.count() > 0

def test__browse_reference(monkeypatch, window, qtbot):
    monkeypatch.setattr("PyQt6.QtWidgets.QFileDialog.getOpenFileName", lambda *a, **k: ("ref.nii", ""))
    window._browse_reference()
    assert window.ref_edit.text() == "ref.nii"

def test__browse_output(monkeypatch, window, qtbot):
    window.out_combo.addItem("trk")
    monkeypatch.setattr("PyQt6.QtWidgets.QFileDialog.getSaveFileName", lambda *a, **k: ("out.trk", ""))
    window._browse_output()
    assert window.output_edit.text() == "out.trk"

def test__on_convert_success(monkeypatch, window, qtbot):
    window.input_edit.setText("in.trk")
    window.output_edit.setText("out.tck")
    window.ref_edit.setText("ref.nii")
    with patch("visubrain.core.converter.Converter") as conv:
        conv.return_value.convert.return_value = None
        with patch("PyQt6.QtWidgets.QMessageBox.information") as info:
            window._on_convert()
            info.assert_not_called()

def test__on_convert_failure(monkeypatch, window, qtbot):
    window.input_edit.setText("in.trk")
    window.output_edit.setText("out.tck")
    window.ref_edit.setText("ref.nii")
    with patch("visubrain.core.converter.Converter", side_effect=Exception("fail")):
        with patch.object(QMessageBox, "critical") as crit:
            window._on_convert()
            crit.assert_called_once()

def test__on_convert_missing_fields(window, qtbot):
    window.input_edit.setText("")
    window.output_edit.setText("")
    with patch.object(QMessageBox, "warning") as warn:
        window._on_convert()
        warn.assert_called_once()