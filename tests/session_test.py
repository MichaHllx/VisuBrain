import pytest
import numpy as np
from visubrain.utils.session import Session

class DummyVolume:
    def __init__(self, shape=(10, 20, 30)):
        self._shape = shape
    def get_dimensions(self):
        return self._shape

class DummyViewer:
    def __init__(self):
        self.calls = []
    def set_working_nifti_obj(self, vol):
        self.calls.append(('set_working_nifti_obj', vol))
    def render_mode(self, mode, opacity):
        self.calls.append(('render_mode', mode, opacity))
    def show_tractogram(self, tract, show_points):
        self.calls.append(('show_tractogram', tract, show_points))

class DummyTracto:
    def __init__(self, file_path, streamlines):
        self.file_path = file_path
        self._streamlines = streamlines
    def get_streamlines(self):
        return self._streamlines

def test_session_init_and_uid():
    vol = DummyVolume()
    viewer = DummyViewer()
    s1 = Session("sess1", vol, viewer)
    s2 = Session("sess2", None, viewer)
    assert s1.display_name == "sess1"
    assert s2.display_name == "sess2"
    assert s1.get_uid() != s2.get_uid()
    assert s1.volume_obj is vol
    assert s2.volume_obj is None
    assert s1.opacity == 0.5
    assert s1.zoom_factor == 1.0
    assert s1.background_color == "white"
    assert s1.rendering_mode == "Slices"

def test_add_tract_and_apply(monkeypatch):
    vol = DummyVolume()
    viewer = DummyViewer()
    s = Session("sess", vol, viewer)
    tract = DummyTracto("tract1.trk", [np.array([[0,0,0],[1,1,1]])])
    s.add_tract(tract)
    assert "tract1.trk" in s.tracts
    s.apply()
    assert any(c[0] == "set_working_nifti_obj" for c in viewer.calls)
    assert any(c[0] == "render_mode" for c in viewer.calls)
    assert any(c[0] == "show_tractogram" for c in viewer.calls)

def test_apply_without_volume():
    viewer = DummyViewer()
    s = Session("sess", None, viewer)
    tract = DummyTracto("tract2.trk", [np.array([[0,0,0],[1,1,1]])])
    s.add_tract(tract)
    s.apply()
    # Ne doit pas appeler set_working_nifti_obj ni render_mode
    assert not any(c[0] == "set_working_nifti_obj" for c in viewer.calls)
    assert not any(c[0] == "render_mode" for c in viewer.calls)
    assert any(c[0] == "show_tractogram" for c in viewer.calls)

def test_tract_statistics_empty():
    s = Session("sess", None, DummyViewer())
    stats = s.tract_statistics()
    assert stats == []

def test_tract_statistics_various():
    s = Session("sess", None, DummyViewer())
    tract = DummyTracto("toto.trk", [
        np.array([[0,0,0],[3,4,0]]),  # longueur 5
        np.array([[0,0,0]])           # ignorée (moins de 2 points)
    ])
    s.add_tract(tract)
    stats = s.tract_statistics()
    assert "toto.trk" in stats[0]
    assert "Number of streamlines: 2" in stats[0]
    assert "Mean length: 5.0mm" in stats[0]
    assert "Total length: 5.0mm" in stats[0]