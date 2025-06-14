import numpy as np
import pytest

import visubrain.io.nifti as nifti_mod

class DummyHeader:
    pass

class DummyImage:
    def __init__(self, data, affine):
        self._data = data
        self.affine = affine
        self.header = DummyHeader()
    def get_fdata(self):
        return self._data

def test_nifti_file_all_methods(monkeypatch):
    # Prépare un faux volume 3D
    data3d = np.ones((10, 20, 30))
    affine = np.eye(4)
    # Patch nibabel
    monkeypatch.setattr(nifti_mod.nib, "load", lambda fp: DummyImage(data3d, affine))
    monkeypatch.setattr(nifti_mod.nib, "as_closest_canonical", lambda img: img)
    monkeypatch.setattr(nifti_mod.nib, "aff2axcodes", lambda aff: ("R", "A", "S"))

    nf = nifti_mod.NiftiFile("dummy.nii")
    assert nf.file_path == "dummy.nii"
    assert np.allclose(nf.get_affine(), affine)
    assert nf.get_dimensions() == (10, 20, 30)
    assert nf.get_header() is nf.image.header
    assert nf.get_orientation() == ("R", "A", "S")
    assert np.allclose(nf.get_data(), data3d)
    assert nf.is_4d() is False
    # get_3d_frame doit lever une erreur sur un 3D
    with pytest.raises(ValueError):
        nf.get_3d_frame(0)

def test_nifti_file_4d(monkeypatch):
    # Prépare un faux volume 4D
    data4d = np.arange(2*3*4*5).reshape((2,3,4,5))
    affine = np.eye(4)
    monkeypatch.setattr(nifti_mod.nib, "load", lambda fp: DummyImage(data4d, affine))
    monkeypatch.setattr(nifti_mod.nib, "as_closest_canonical", lambda img: img)
    monkeypatch.setattr(nifti_mod.nib, "aff2axcodes", lambda aff: ("L", "P", "S"))

    nf = nifti_mod.NiftiFile("dummy4d.nii")
    assert nf.is_4d() is True
    frame = nf.get_3d_frame(2)
    assert np.allclose(frame, data4d[...,2])