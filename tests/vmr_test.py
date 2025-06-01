import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from visubrain.io.vmr import VMRFile

# ---------- TESTS UNITAIRES ----------- #

def make_fake_nii(shape=(256,256,256)):
    class FakeHeader(dict):
        def __getitem__(self, key):
            if key == "pixdim":
                return [0, 1, 1, 1]  # [0, x, y, z]
            if key == "dim":
                return [3] + list(shape)  # [ndims, x, y, z]
            return super().__getitem__(key)
        def get(self, key, default=None):
            return self[key] if key in self else default

    fake_header = FakeHeader()
    fake_affine = np.eye(4)
    data = np.random.rand(*shape)

    class FakeNifti:
        header = fake_header
        affine = fake_affine
        def get_fdata(self):
            return data

    return FakeNifti()

def test_get_pos_from_nifti_shapes():
    fake_nii = make_fake_nii()
    row_dir, col_dir, slice_1, slice_n = VMRFile._get_pos_from_nifti(fake_nii)
    assert len(row_dir) == 3
    assert len(col_dir) == 3
    assert len(slice_1) == 3
    assert len(slice_n) == 3

# ---------- TESTS D'INTEGRATION ----------- #

@patch("visubrain.io.vmr.nib")
@patch("visubrain.io.vmr.create_vmr")
@patch("visubrain.io.vmr.write_vmr")
def test_write_from_nifti(m_write_vmr, m_create_vmr, m_nib):
    fake_nii = make_fake_nii()
    m_nib.load.return_value = fake_nii
    m_nib.as_closest_canonical.return_value = fake_nii
    m_create_vmr.return_value = ({}, np.zeros((256,256,256), dtype=np.ubyte))

    v = VMRFile()
    v.write_from_nifti("input.nii", "output.vmr")

    m_nib.load.assert_called_once_with("input.nii")
    m_create_vmr.assert_called_once()
    m_write_vmr.assert_called_once()

def test_error_if_wrong_nifti(monkeypatch):
    v = VMRFile()
    class BadNifti:
        def get_fdata(self):
            raise ValueError("corrupt data")
        header = {"pixdim": [0,1,1,1], "dim": [3,256,256,256]}
        affine = np.eye(4)

    with patch("visubrain.io.vmr.nib") as m_nib, patch("visubrain.io.vmr.create_vmr"), patch("visubrain.io.vmr.write_vmr"):
        m_nib.load.return_value = BadNifti()
        m_nib.as_closest_canonical.return_value = BadNifti()
        with pytest.raises(ValueError):
            v.write_from_nifti("corrupt.nii", "out.vmr")

def test_voxel_size_extraction():
    fake_nii = make_fake_nii((64, 128, 32))
    v = VMRFile()
    with patch("visubrain.io.vmr.create_vmr") as m_create_vmr, \
         patch("visubrain.io.vmr.write_vmr") as m_write_vmr, \
         patch("visubrain.io.vmr.nib") as m_nib:
        m_nib.load.return_value = fake_nii
        m_nib.as_closest_canonical.return_value = fake_nii
        m_create_vmr.return_value = ({}, np.zeros((64,128,32), dtype=np.ubyte))
        v.write_from_nifti("input.nii", "out.vmr")

