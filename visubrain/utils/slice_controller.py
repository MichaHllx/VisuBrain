# visubrain/utils/slice_controller.py

from PyQt6.QtWidgets import QSlider, QLineEdit


class SliceControl:
    def __init__(self, orientation: str, slider: QSlider, line_edit: QLineEdit):
        self.orientation = orientation
        self.slider = slider
        self.line_edit = line_edit

        self.slider.valueChanged.connect(self._sync_line_edit)
        self.line_edit.returnPressed.connect(self._sync_slider)

    def _sync_line_edit(self, value: int):
        self.line_edit.setText(str(value))

    def _sync_slider(self):
        try:
            value = int(self.line_edit.text())
            if 0 <= value <= self.slider.maximum():
                self.slider.setValue(value)
        except ValueError:
            pass

    def set_max(self, max_val: int):
        self.slider.setMaximum(max_val)

    def set_value(self, val: int):
        self.slider.setValue(val)

    def get_value(self) -> int:
        return self.slider.value()

    def connect_slider_callback(self, func):
        self.slider.valueChanged.connect(lambda val: func(val, self.orientation))