import pytest
from visubrain.utils.slice_controller import SliceControl

class DummySignal:
    def __init__(self):
        self._callbacks = []
    def connect(self, cb):
        self._callbacks.append(cb)
    def emit(self, *args, **kwargs):
        for cb in self._callbacks:
            cb(*args, **kwargs)

class DummySlider:
    def __init__(self):
        self._value = 0
        self._max = 0
        self.valueChanged = DummySignal()
    def setValue(self, v):
        self._value = v
        self.valueChanged.emit(v)
    def value(self):
        return self._value
    def setMaximum(self, m):
        self._max = m
    def maximum(self):
        return self._max

class DummyLineEdit:
    def __init__(self):
        self._text = "0"
        self.returnPressed = DummySignal()
    def setText(self, txt):
        self._text = str(txt)
    def text(self):
        return self._text
    def set_return_value(self, val):
        self._text = str(val)
    def emit_return(self):
        self.returnPressed.emit()

def test_sync_line_edit_and_slider():
    slider = DummySlider()
    line_edit = DummyLineEdit()
    sc = SliceControl("Axial", slider, line_edit)
    # Test slider -> line_edit
    slider.setValue(5)
    assert line_edit.text() == "5"
    line_edit.set_return_value(7)
    line_edit.emit_return()
    assert slider.value() == 5
    slider.setMaximum(10)
    line_edit.set_return_value(15)
    line_edit.emit_return()
    assert slider.value() == 5  # inchangé
    line_edit.set_return_value("abc")
    line_edit.emit_return()
    assert slider.value() == 5  # inchangé

def test_set_and_get_max():
    slider = DummySlider()
    line_edit = DummyLineEdit()
    sc = SliceControl("Coronal", slider, line_edit)
    sc.set_max(42)
    assert sc.get_max() == 42
    assert slider.maximum() == 42

def test_set_and_get_value():
    slider = DummySlider()
    line_edit = DummyLineEdit()
    sc = SliceControl("Sagittal", slider, line_edit)
    sc.set_value(3)
    assert sc.get_value() == 3

def test_connect_slider_callback():
    slider = DummySlider()
    line_edit = DummyLineEdit()
    sc = SliceControl("Axial", slider, line_edit)
    called = {}
    def cb(val, orient):
        called['val'] = val
        called['orient'] = orient
    sc.connect_slider_callback(cb)
    slider.setValue(9)
    assert called['val'] == 9
    assert called['orient'] == "Axial"

def test_set_max_negative_and_zero():
    slider = DummySlider()
    line_edit = DummyLineEdit()
    sc = SliceControl("Axial", slider, line_edit)
    sc.set_max(0)
    assert sc.get_max() == 0
    assert slider.maximum() == 0
    sc.set_max(-5)
    assert sc.get_max() == -5
    assert slider.maximum() == -5

def test_multiple_slider_callbacks():
    slider = DummySlider()
    line_edit = DummyLineEdit()
    sc = SliceControl("Coronal", slider, line_edit)
    called = []
    sc.connect_slider_callback(lambda v, o: called.append((v, o, 1)))
    sc.connect_slider_callback(lambda v, o: called.append((v, o, 2)))
    slider.setValue(3)
    assert len(called) == 2
    assert all(c[0] == 3 and c[1] == "Coronal" for c in called)

def test_slider_max_zero_sync():
    slider = DummySlider()
    line_edit = DummyLineEdit()
    sc = SliceControl("Sagittal", slider, line_edit)
    sc.set_max(0)
    line_edit.set_return_value(0)
    line_edit.emit_return()
    assert slider.value() == 0
    line_edit.set_return_value(1)
    line_edit.emit_return()
    assert slider.value() == 0  # reste à 0 car max=0

def test_orientation_storage():
    slider = DummySlider()
    line_edit = DummyLineEdit()
    sc = SliceControl("Oblique", slider, line_edit)
    assert sc.orientation == "Oblique"

def test_init_with_none_widgets():
    # On vérifie que l'init échoue proprement si widgets manquants
    with pytest.raises(AttributeError):
        SliceControl("Axial", None, DummyLineEdit())
    with pytest.raises(AttributeError):
        SliceControl("Axial", DummySlider(), None)

def test_direct_max_modification():
    slider = DummySlider()
    line_edit = DummyLineEdit()
    sc = SliceControl("Axial", slider, line_edit)
    sc.max = 123
    assert sc.get_max() == 123