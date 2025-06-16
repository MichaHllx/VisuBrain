import pytest
import numpy as np
import nibabel as nib

# --- Constructor testing and extension validation ---

def test_validate_extensions_supported():
    c = Converter("my_file.trk", "conv_file.fbr")
    assert c.in_ext == "trk"
    assert c.out_ext == "fbr"

def test_validate_extensions_unsupported():
    with pytest.raises(ValueError):
        Converter("my_file.xyz", "other_file.abc")

def test_all_supported_extensions():
    all_keys = list(Converter._CONVERTERS.keys())
    for in_ext, out_ext in all_keys:
        fname_in = "file." + in_ext
        fname_out = "file." + out_ext
        Converter(fname_in, fname_out)

def test_converter_constructor_with_and_without_ref():
    c1 = Converter("a.trk", "b.fbr", "anat.nii")
    assert c1.anatomical_ref == "anat.nii"
    c2 = Converter("a.trk", "b.fbr")
    assert c2.anatomical_ref is None
    with pytest.raises(ValueError):
        c3 = Converter("a.tck", "b.fbr")

def test_tck_to_trk_requires_anatomical_ref():
    conv = Converter("file.tck", "file.trk")  # no ref
    with pytest.raises(ValueError):
        conv.tck_to_trk()

def test_fbr_to_trk_requires_anatomical_ref():
    conv = Converter("file.fbr", "file.trk")  # no ref
    with pytest.raises(ValueError):
        conv.fbr_to_trk()

# --- Test of the static FBR preparation method ---

def test_prepare_fbr_data_from_trk():
    streamlines = [np.array([[0, 0, 0], [1, 1, 1]])]
    colors = [np.array([[255, 0, 0], [0, 255, 0]])]
    header, fibers = Converter._prepare_fbr_data_from_trk(streamlines, colors)
    assert isinstance(header, dict)
    assert isinstance(fibers, list)
    assert len(fibers) == 1
    assert fibers[0]['NrOfPoints'] == 2
    assert fibers[0]['Points'][0][3:] == [255, 0, 0]

def test_prepare_fbr_data_from_trk_empty():
    streamlines = []
    colors = []
    header, fibers = Converter._prepare_fbr_data_from_trk(streamlines, colors)
    assert isinstance(header, dict)
    assert isinstance(fibers, list)
    assert len(fibers) == 0
    assert header['Groups'][0]['NrOfFibers'] == 0

def test_prepare_fbr_data_from_trk_regular():
    streamlines = [np.array([[0,0,0],[1,1,1]])]
    colors = [np.array([[10,20,30],[40,50,60]])]
    header, fibers = Converter._prepare_fbr_data_from_trk(streamlines, colors)
    assert fibers[0]['NrOfPoints'] == 2


# --- Test of correction and filtering functions (without IO) ---

def test_correct_fbr_to_nifti_and_filter_valid():
    class DummyImg:
        shape = (10, 10, 10)
        affine = np.eye(4)
    img = DummyImg()
    streamlines = [np.array([[0.5, 1.0, 1.5], [2.0, 2.5, 3.0]])]
    conv = Converter("a.fbr", "b.trk", "ref.nii")
    corrected = conv._correct_fbr_to_nifti(streamlines, img)

    assert isinstance(corrected, list)
    assert np.allclose(corrected[0][0], np.array([0.5, 1.0, 1.5]) + 5)  # le centre de l'image

    valid = conv._filter_valid_streamlines(corrected, img)
    assert len(valid) == 1

    out_streamlines = [np.array([[100, 100, 100], [200, 200, 200]])]
    corrected_out = conv._correct_fbr_to_nifti(out_streamlines, img)
    valid_out = conv._filter_valid_streamlines(corrected_out, img)
    assert len(valid_out) == 0

def test_filter_valid_streamlines_mixed():
    class DummyImg:
        shape = (10, 10, 10)
        affine = np.eye(4)
    img = DummyImg()
    # a valid and invalid streamlines
    valid_stream = np.array([[5, 5, 5], [6, 6, 6]])
    invalid_stream = np.array([[15, 15, 15], [16, 16, 16]])
    conv = Converter("a.fbr", "b.trk", "ref.nii")
    valid = conv._filter_valid_streamlines([valid_stream, invalid_stream], img)
    assert len(valid) == 1
    assert np.allclose(valid[0], valid_stream)

def test_correct_fbr_to_nifti_with_affine():
    class DummyImg:
        shape = (4, 4, 4)
        affine = np.array([
        [2, 0, 0, 10],
        [0, 2, 0, 20],
        [0, 0, 2, 30],
        [0, 0, 0, 1]])
    img = DummyImg()
    streamlines = [np.array([[1, 1, 1]])]
    conv = Converter("a.fbr", "b.trk", "ref.nii")
    corrected = conv._correct_fbr_to_nifti(streamlines, img)
    assert corrected[0].shape == (1, 3)


# --- Integration tests ---

def test_trk_to_tck_conversion(tmp_path):
    trk_file = "data/NT1_uf_right.trk"
    tck_file = tmp_path / "mini.tck"
    ref_file = "data/NT1_RD.nii.gz"

    conv = Converter(trk_file, str(tck_file), anatomical_ref=ref_file)
    conv.convert()

    assert tck_file.exists()
    try:
        img = nib.streamlines.load(str(tck_file))
        assert img.streamlines is not None
    except Exception as e:
        pytest.fail(e)

def test_voi_to_nii_gz(tmp_path):
    voi_file = "data/temp.voi"
    nii_gz_file = tmp_path / "mini.nii.gz"
    conv = Converter(voi_file, str(nii_gz_file))
    conv.convert()
    assert nii_gz_file.exists()

def test_converter_init_nifti_to_trk(tmp_path):
    """Test basic instantiation for a NIfTI to TRK conversion."""
    input_path = str(tmp_path / "test.nii.gz")
    output_path = str(tmp_path / "test.trk")
    with open(input_path, "wb") as f:
        f.write(b"dummy")
    with pytest.raises(ValueError):
        converter = Converter(input_path, output_path)
        assert converter.input_path == input_path
        assert converter.output_path == output_path

def test_converter_bad_input_raises(tmp_path):
    """Test error raised if input file does not exist."""
    bad_input = str(tmp_path / "doesnotexist.nii")
    output = str(tmp_path / "out.trk")
    with pytest.raises(Exception):
        Converter(bad_input, output).convert()

def test_converter_missing_reference_warns(tmp_path):
    """Test warning or error when anatomical_ref is needed but missing."""
    input_path = str(tmp_path / "test.tck")
    output_path = str(tmp_path / "test.trk")
    with open(input_path, "wb") as f:
        f.write(b"dummy")
    converter = Converter(input_path, output_path)
    try:
        converter.convert()
    except Exception as e:
        assert "reference" in str(e).lower()

def test_converter_detects_supported_formats(tmp_path):
    """Test that Converter lists supported output formats."""
    input_path = str(tmp_path / "dummy.nii.gz")
    with open(input_path, "wb") as f:
        f.write(b"dummy")
    combos = [o for (i, o) in Converter._CONVERTERS if i == "nii.gz"]
    assert "voi" in combos or "vmr" in combos

def test_converter_supported_conversions():
    """Test that Converter supports all expected input/output combinations."""
    for ext, target in Converter._CONVERTERS:
        assert ext
        assert target

def test_vmr_to_nii_integration(tmp_path):
    """Test integration of _vmr_to_nii: real VMR file to NIfTI file"""
    vmr_input = "data/NT1_b0_aff.vmr"
    nii_output = tmp_path / "converted.nii.gz"

    assert os.path.exists(vmr_input), "Fichier VMR de test absent !"

    conv = Converter(vmr_input, str(nii_output))
    conv.vmr_to_nii()

    assert nii_output.exists(), "La conversion n'a pas créé de fichier NIfTI"

    img = nib.load(str(nii_output))
    assert img.get_fdata().size > 0

import os
from visubrain.core.converter import Converter

def test_fbr_to_trk_integration(tmp_path):
    """Test FBR to TRK conversion (real I/O)."""
    fbr_input = "data/TRACT_test.fbr"
    trk_output = tmp_path / "converted.trk"

    assert os.path.exists(fbr_input), "Test FBR file is missing!"

    conv = Converter(fbr_input, str(trk_output), anatomical_ref="data/NT1_RD.nii.gz")
    conv.fbr_to_trk()
    conv.fbr_to_trk()

    assert trk_output.exists(), "TRK file was not created"

def test_validate_extensions_raises():
    with pytest.raises(ValueError):
        Converter("a.foo", "b.bar")

def test_convert_dispatch_and_error(monkeypatch):
    c = Converter("a.trk", "b.fbr")
    called = {}
    def fake_trk_to_fbr(self): called['ok'] = True
    monkeypatch.setattr(Converter, "trk_to_fbr", fake_trk_to_fbr)
    c.convert()
    assert called['ok']

    def fail(self): raise RuntimeError("fail")
    monkeypatch.setattr(Converter, "trk_to_fbr", fail)
    with pytest.raises(ValueError) as e:
        c.convert()
    assert "Conversion trk to fbr" in str(e.value)

def test_trk_to_tck_and_tck_to_trk(monkeypatch):
    c = Converter("data/NT1_uf_right.trk", "b.tck")
    monkeypatch.setattr("dipy.io.streamline.load_tractogram", lambda *a, **k: "sft")
    monkeypatch.setattr("dipy.io.streamline.save_tractogram", lambda sft, out: None)
    c.trk_to_tck()

    c2 = Converter("data/NT1_uf_left.tck", "b.trk", "data/someones_anatomy.nii.gz")
    monkeypatch.setattr("dipy.io.streamline.load_tractogram", lambda *a, **k: "sft")
    monkeypatch.setattr("dipy.io.streamline.save_tractogram", lambda sft, out: None)
    c2.tck_to_trk()

    # Sans référence anatomique
    c3 = Converter("data/NT1_uf_left.tck", "b.trk")
    with pytest.raises(ValueError):
        c3.tck_to_trk()

import gzip

def test_voi_to_nii_and_nii_to_voi(tmp_path):
    voi = tmp_path / "a.voi"
    with gzip.open(voi, "wb") as f:
        f.write(b"abc")
    nii = tmp_path / "a.nii"
    gz = tmp_path / "a.nii.gz"

    c = Converter(str(voi), str(nii))
    c.voi_to_nii()
    assert nii.exists()

    c2 = Converter(str(gz), str(voi))
    with gzip.open(gz, "wb") as f:
        f.write(b"def")
    c2.nii_to_voi()
    assert voi.exists()

def test_voi_to_nii_gz_and_nii_gz_to_voi(tmp_path):
    f1 = tmp_path / "a.voi"
    f2 = tmp_path / "a.nii.gz"
    with open(f1, "wb") as f: f.write(b"abc")
    c = Converter(str(f1), str(f2))
    c.voi_to_nii_gz()
    assert f2.exists()

    c2 = Converter(str(f2), str(f1))
    c2.nii_gz_to_voi()
    assert f1.exists()

def test_nii_to_vmr_error(monkeypatch):
    c = Converter("a.nii", "b.vmr")
    class DummyVMR:
        def write_from_nifti(self, i, o): raise Exception("fail")
    monkeypatch.setattr("visubrain.io.vmr.VMRFile", lambda: DummyVMR())
    with pytest.raises(ValueError):
        c.nii_to_vmr()

def test_vmr_to_nii_error(monkeypatch):
    c = Converter("a.vmr", "b.nii")
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr("bvbabel.vmr.read_vmr", fail)
    with pytest.raises(ValueError):
        c.vmr_to_nii()

def test_trk_to_fbr(monkeypatch):
    c = Converter("data/NT1_uf_right.trk", "b.fbr")
    class DummyTracto:
        d = []
        def get_color_points(self, show_points, d): return None, [[[1,2,3]]], None
        def get_streamlines(self): return [[[0,0,0],[1,1,1]]]
    monkeypatch.setattr("visubrain.io.tractography.Tractography", lambda a, b: DummyTracto())
    class DummyFbr:
        def write_fbr(self, out, header, fibers): self.called = True
    monkeypatch.setattr("visubrain.io.fbr.BinaryFbrFile", lambda: DummyFbr())
    c.trk_to_fbr()

def test_fbr_to_trk(monkeypatch, tmp_path):
    from visubrain.core.converter import Converter

    c = Converter("data/TRACT_test.fbr", "b.trk", "data/someones_anatomy.nii.gz")
    class DummyFbr:
        groups = [{'fibers': [
            {'points': np.array([[1,2,3],[4,5,6]]), 'colors': np.array([[1,2,3],[4,5,6]])}
        ]}]
    monkeypatch.setattr("visubrain.io.fbr.BinaryFbrFile", lambda f: DummyFbr())
    img = nib.Nifti1Image(np.zeros((10,10,10)), np.eye(4))
    monkeypatch.setattr("nibabel.load", lambda f: img)
    monkeypatch.setattr("dipy.io.stateful_tractogram.StatefulTractogram", lambda s, reference, space: s)
    monkeypatch.setattr("dipy.io.streamline.save_tractogram", lambda s, o: None)
    c.fbr_to_trk()

    c2 = Converter("a.fbr", "b.trk")
    with pytest.raises(ValueError):
        c2.fbr_to_trk()

def test_prepare_trk_data_from_fbr_and_correction(monkeypatch):
    c = Converter("a.fbr", "b.trk", "ref.nii")
    class DummyFbr:
        groups = [{'fibers': [{'points': np.array([[1,2,3],[4,5,6]]), 'colors': np.array([[1,2,3],[4,5,6]])}]}]
    class DummyImg:
        shape = (10,10,10)
        affine = np.eye(4)
    fbr = DummyFbr()
    img = DummyImg()
    out = c._prepare_trk_data_from_fbr(fbr, img)
    assert isinstance(out, list)