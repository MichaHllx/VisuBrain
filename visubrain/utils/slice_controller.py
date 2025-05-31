"""
visubrain/utils/slice_controller.py

Module for slice navigation controls in the VisuBrain application.

Defines the SliceControl class to manage and synchronize slice navigation widgets
(QSlider and QLineEdit) for different anatomical orientations. Enables interactive
and synchronized control of slice position, supporting both manual input and slider movement.

Classes:
    SliceControl: Manages slice position widgets and synchronization for anatomical viewing.
"""


from PyQt6.QtWidgets import QSlider, QLineEdit


class SliceControl:
    """
    Class to manage the synchronization and control of a slice slider and input field.

    Handles synchronization between a QSlider and QLineEdit to control slice positions
    in different orientations (Axial, Coronal, Sagittal) in a medical imaging viewer.
    """

    def __init__(self, orientation: str, slider: QSlider, line_edit: QLineEdit):
        """
        Initialize the SliceControl with a given orientation, slider, and line edit.

        Args:
            orientation (str): The orientation ("Axial", "Coronal", "Sagittal").
            slider (QSlider): The slider widget to control slice index.
            line_edit (QLineEdit): The text input for direct slice index entry.
        """
        self.orientation = orientation
        self.max = 0
        self.slider = slider
        self.line_edit = line_edit

        self.slider.valueChanged.connect(self._sync_line_edit)
        self.line_edit.returnPressed.connect(self._sync_slider)

    def _sync_line_edit(self, value: int):
        """
        Update the line edit value when the slider is moved.

        Args:
            value (int): Current value of the slider.
        """
        self.line_edit.setText(str(value))

    def _sync_slider(self):
        """
        Update the slider value when the line edit value is changed by the user.
        """
        try:
            value = int(self.line_edit.text())
            if 0 <= value <= self.slider.maximum():
                self.slider.setValue(value)
        except ValueError:
            pass

    def set_max(self, max_val: int):
        """
        Set the maximum value for the slider and store it locally.

        Args:
            max_val (int): Maximum allowed value for the slider.
        """
        self.max = max_val
        self.slider.setMaximum(max_val)

    def get_max(self) -> int:
        """
        Get the maximum value currently set for the slider.

        Returns:
            int: Maximum value.
        """
        return self.max

    def set_value(self, val: int):
        """
        Set the slider value.

        Args:
            val (int): Value to set.
        """
        self.slider.setValue(val)

    def get_value(self) -> int:
        """
        Get the current value of the slider.

        Returns:
            int: Slider value.
        """
        return self.slider.value()

    def connect_slider_callback(self, func):
        """
        Connect a callback function to the slider's valueChanged signal.

        Args:
            func (callable): Function to call on slider value change. Should accept
            (value, orientation).
        """
        self.slider.valueChanged.connect(lambda val: func(val, self.orientation))
