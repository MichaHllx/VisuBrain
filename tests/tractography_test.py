import numpy as np
import pytest

from visubrain.io.tractography import Tractography

class DummyNifti:
    def __init__(self, affine=None, file_path="ref.nii"):
        self.affine = affine if affine is not None else np.eye(4)
        self.file_path = file_path

class DummyTractogram:
    def __init__(self, streamlines):
        self.streamlines = streamlines

def dummy_load_tractogram(filename, reference):
    if filename.endswith(".tck") and reference == "missing":
        raise Exception("Missing reference")
    if filename.endswith(".tck"):
        return DummyTractogram([np.array([[1,2,3],[4,5,6]])])
    return DummyTractogram([np.array([[0,0,0],[1,0,0],[1,1,0]])])

def dummy_transform_streamlines(streamlines, affine):
    return [s + 1 for s in streamlines]

def test_trk_load(monkeypatch):
    monkeypatch.setattr("visubrain.io.tractography.load_tractogram", dummy_load_tractogram)
    t = Tractography("foo.trk", session_id=42)
    assert t.file_path == "foo.trk"
    assert t.reference_nifti is None
    assert isinstance(t.streamlines, list)
    assert isinstance(t.raw_data, DummyTractogram)
    assert t.session_id == 42

def test_tck_load_with_reference(monkeypatch):
    monkeypatch.setattr("visubrain.io.tractography.load_tractogram", dummy_load_tractogram)
    monkeypatch.setattr("visubrain.io.tractography.transform_streamlines", dummy_transform_streamlines)
    ref = DummyNifti()
    t = Tractography("foo.tck", session_id="sess", reference_nifti=ref)
    assert t.reference_nifti is ref
    assert all(np.allclose(s, np.array([[2,3,4],[5,6,7]])) for s in t.streamlines)

def test_tck_load_without_reference(monkeypatch):
    monkeypatch.setattr("visubrain.io.tractography.load_tractogram", dummy_load_tractogram)
    with pytest.raises(ValueError) as e:
        Tractography("foo.tck", session_id=1, reference_nifti=None)
    assert "anatomical reference" in str(e.value)

def test_load_streamlines_error(monkeypatch):
    def fail_load(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr("visubrain.io.tractography.load_tractogram", fail_load)
    with pytest.raises(ValueError) as e:
        Tractography("foo.trk", session_id=1)
    assert "Error while loading streamlines" in str(e.value)

def test_get_streamlines(monkeypatch):
    monkeypatch.setattr("visubrain.io.tractography.load_tractogram", dummy_load_tractogram)
    t = Tractography("foo.trk", session_id=1)
    assert t.get_streamlines() == t.streamlines

def test_get_color_points_lines(monkeypatch):
    monkeypatch.setattr("visubrain.io.tractography.load_tractogram", dummy_load_tractogram)
    t = Tractography("foo.trk", session_id=1)
    # Un streamline de 3 points
    pts, colors, conn = t.get_color_points(show_points=False)
    assert len(pts) == 1
    assert colors[0].shape == (3,3)
    assert len(conn) == 1
    assert conn[0][0] == 3  # nombre de points

def test_get_color_points_points(monkeypatch):
    monkeypatch.setattr("visubrain.io.tractography.load_tractogram", dummy_load_tractogram)
    t = Tractography("foo.trk", session_id=1)
    pts, colors, conn = t.get_color_points(show_points=True)
    assert len(conn) == 0  # pas de connectivité

def test_get_color_points_single_point(monkeypatch):
    def single_point_loader(filename, reference):
        return DummyTractogram([np.array([[1,2,3]])])
    monkeypatch.setattr("visubrain.io.tractography.load_tractogram", single_point_loader)
    t = Tractography("foo.trk", session_id=1)
    pts, colors, conn = t.get_color_points(show_points=False)
    assert (colors[0] == np.array([[255,255,255]], dtype=np.uint8)).all()
    assert conn[0][0] == 1

def test_get_color_points_zero_norm(monkeypatch):
    # avec deux points identiques (norme nulle)
    def zero_norm_loader(filename, reference):
        return DummyTractogram([np.array([[1,1,1],[1,1,1]])])
    monkeypatch.setattr("visubrain.io.tractography.load_tractogram", zero_norm_loader)
    t = Tractography("foo.trk", session_id=1)
    pts, colors, conn = t.get_color_points(show_points=False)
    assert (colors[0][0] == [0,0,0]).all()
    assert (colors[0][1] == [0,0,0]).all()