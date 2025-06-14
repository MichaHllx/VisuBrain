import os
import struct
import tempfile
import pytest

from visubrain.io.fbr import BinaryFbrFile

def make_fbr_file(path):
    with open(path, "wb") as f:
        f.write(b'\xa4\xd3\xc2\xb1')  # magic
        f.write(struct.pack('<I', 1))  # FileVersion
        f.write(struct.pack('<I', 0))  # CoordsType
        f.write(struct.pack('<3f', 0.0, 0.0, 0.0))  # FibersOrigin
        f.write(struct.pack('<I', 1))  # NrOfGroups

        # group
        f.write(b'TestGroup\x00')
        f.write(struct.pack('<I', 1))  # Visible
        f.write(struct.pack('<i', 0))  # Animate
        f.write(struct.pack('<f', 1.5))  # Thickness
        f.write(struct.pack('<3B', 10, 20, 30))  # Color
        f.write(struct.pack('<I', 1))  # NrOfFibers

        # fiber
        f.write(struct.pack('<I', 2))  # NrOfPoints
        f.write(struct.pack('<2f', 1.0, 2.0))  # X
        f.write(struct.pack('<2f', 3.0, 4.0))  # Y
        f.write(struct.pack('<2f', 5.0, 6.0))  # Z
        f.write(struct.pack('<2B', 100, 110))  # R
        f.write(struct.pack('<2B', 120, 130))  # G
        f.write(struct.pack('<2B', 140, 150))  # B

def test_read_valid_fbr():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        make_fbr_file(tmp.name)
        fbr = BinaryFbrFile(tmp.name)
        assert fbr._magic == b'\xa4\xd3\xc2\xb1'
        assert fbr._file_version == 1
        assert fbr._coords_type == 0
        assert fbr.fibers_origin == (0.0, 0.0, 0.0)
        assert fbr._num_groups == 1
        assert fbr.num_fibers == 1
        assert len(fbr.groups) == 1
        group = fbr.groups[0]
        assert group['name'] == "TestGroup"
        assert group['visible'] == 1
        assert group['animate'] == 0
        assert group['thickness'] == 1.5
        assert group['color'] == (10, 20, 30)
        assert len(group['fibers']) == 1
        fiber = group['fibers'][0]
        assert fiber['points'] == [(1.0, 3.0, 5.0), (2.0, 4.0, 6.0)]
        assert fiber['colors'] == [(100, 120, 140), (110, 130, 150)]
    os.remove(tmp.name)

def test_read_invalid_magic():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b'BAD!')  # bad magic nbr
        tmp.flush()
        with pytest.raises(ValueError):
            BinaryFbrFile(tmp.name)
    os.remove(tmp.name)

def test_get_fiber_coordinates():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        make_fbr_file(tmp.name)
        fbr = BinaryFbrFile(tmp.name)
        coords = fbr.get_fiber_coordinates()
        assert coords == [[(1.0, 3.0, 5.0), (2.0, 4.0, 6.0)]]
    os.remove(tmp.name)

def test_get_header():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        make_fbr_file(tmp.name)
        fbr = BinaryFbrFile(tmp.name)
        header = fbr.get_header()
        assert header['FBRFile'] == tmp.name
        assert header['Name'] == "TestGroup"
        assert header['NrOfGroups'] == 1
        assert header['NrOfFibers'] == "1"
    os.remove(tmp.name)

def test_write_fbr_and_readback():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        header = {
            'FileVersion': 1,
            'CoordsType': 0,
            'FibersOrigin': (0.0, 0.0, 0.0),
            'NrOfGroups': 1,
            'Groups': [{
                'Name': 'G1',
                'Visible': 1,
                'Animate': 0,
                'Thickness': 1.0,
                'Color': (1, 2, 3),
                'NrOfFibers': 1
            }]
        }
        fibers = [{
            'NrOfPoints': 2,
            'Points': [
                (1.0, 2.0, 3.0, 10, 20, 30),
                (4.0, 5.0, 6.0, 40, 50, 60)
            ]
        }]
        BinaryFbrFile.write_fbr(tmp.name, header, fibers)
        fbr = BinaryFbrFile(tmp.name)
        assert fbr.groups[0]['name'] == 'G1'
        assert len(fbr.groups[0]['fibers']) == 1
        pts = fbr.groups[0]['fibers'][0]['points']
        assert pts[0] == (1.0, 2.0, 3.0)
        assert pts[1] == (4.0, 5.0, 6.0)
    os.remove(tmp.name)

def test_init_without_file():
    fbr = BinaryFbrFile()
    assert fbr._fbr_file is None
    assert fbr.groups == []