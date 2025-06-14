import pyvista as pv

from visubrain.gui.viewer import _slice_actor_key, PyVistaViewer
from visubrain.io.nifti import NiftiFile
from visubrain.io.tractography import Tractography


# --- Unit tests ---

def test_slice_actor_key():
    assert _slice_actor_key("myfile.nii","axial") == "myfile.nii::axial_slice"
    assert _slice_actor_key("a","b") == "a::b_slice"
    assert _slice_actor_key("","z") == "::z_slice"

# --- Integration tests ---

def test_viewer_load_and_render_slices(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    nifti = NiftiFile("data/NT1_RD.nii.gz")
    v.set_working_nifti_obj(nifti)
    assert v.working_nifti_obj == nifti

    ok = v.render_mode("slices", opacity=0.8)
    assert ok
    assert v.volume_sliced_actor
    v.update_slice_opacity(0.5)

def test_viewer_show_tractogram(qtbot):
    from visubrain.io.tractography import Tractography
    v = PyVistaViewer()
    qtbot.addWidget(v)
    tracto = Tractography(file_path="data/NT1_uf_right.trk", session_id=0)
    v.show_tractogram(tracto)
    assert v.tract_actors

def test_set_working_nifti_obj_and_render(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    nifti = NiftiFile("data/NT1_RD.nii.gz")
    v.set_working_nifti_obj(nifti)
    assert v.working_nifti_obj == nifti

def test_render_modes(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    nifti = NiftiFile("data/NT1_RD.nii.gz")
    v.set_working_nifti_obj(nifti)
    assert v.render_mode("slices")
    assert v.render_mode("volume 3d")
    assert not v.render_mode("unsupported_mode")

def test_slice_update(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    nifti = NiftiFile("data/NT1_RD.nii.gz")
    v.set_working_nifti_obj(nifti)
    v.schedule_slice_update("axial", 5, 0.8)
    v.perform_slice_update()

def test_show_tractogram(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    tracto = Tractography(file_path="data/NT1_uf_right.trk", session_id=0)
    v.show_tractogram(tracto)

def test_set_file_visibility(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    tracto = Tractography(file_path="data/NT1_uf_right.trk", session_id=0)
    v.show_tractogram(tracto)
    v.set_file_visibility(tracto.file_path, False, tracto.session_id)
    v.set_file_visibility(tracto.file_path, True, tracto.session_id)

def test_update_slice_position(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    nifti = NiftiFile("data/NT1_RD.nii.gz")
    v.set_working_nifti_obj(nifti)
    v.render_mode("slices")
    v.update_slice_position("axial", 10)
    v.update_slice_position("coronal", 10)
    v.update_slice_position("sagittal", 10)
    v.update_slice_position("foo", 10)  # else clause

def test_update_slice_opacity(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    nifti = NiftiFile("data/NT1_RD.nii.gz")
    v.set_working_nifti_obj(nifti)
    v.render_mode("slices")
    v.update_slice_opacity(0.3)

def test_set_zoom(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    v.set_zoom(200)
    v.set_zoom(50)

def test_set_zoom_updates_zoom_factor(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    v.set_zoom(200)
    assert v.current_zoom_factor == 2.0
    v.set_zoom(50)
    assert v.current_zoom_factor == 0.5

def test_change_background(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    v.change_background("BLUE")

def test_clear_previous_actors_and_hide(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    nifti = NiftiFile("data/NT1_RD.nii.gz")
    v.set_working_nifti_obj(nifti)
    v.render_mode("slices")
    v.clear_previous_actors()
    v.hide_all_actors()
    v.reset_view()

def test_render_mode_changes_mode(qtbot):
    v = PyVistaViewer()
    qtbot.addWidget(v)
    v.working_nifti_obj = NiftiFile("data/someones_anatomy.nii.gz")
    v.pv_data = pv.wrap(v.working_nifti_obj.data)
    v.render_mode("slices")
    assert v.current_mode == "slices"
    v.render_mode("volume 3d")
    assert v.current_mode == "volume 3d"