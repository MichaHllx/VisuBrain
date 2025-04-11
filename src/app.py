import os
import sys
import tempfile

from PyQt6.QtWidgets import QApplication, QFileDialog, QPushButton, QWidget, QVBoxLayout, QSlider, QLabel, QCheckBox, \
    QLineEdit, QHBoxLayout, QTabWidget
from PyQt6.QtCore import Qt

from file_loader import FileLoader
from viewer import PyVistaViewer
from converter import Converter


class WindowApp(QWidget):
    def __init__(self):
        super().__init__()

        self.drop_label = None
        self.download_button = None
        self.load_button = None
        self.slice_controls = None
        self.file_checkboxes = None
        self.viewer = None
        self.load_trk_button = None
        self.load_nifti_button = None

        self.nifti_object = None

        self.loader = FileLoader()

        self.setGeometry(200, 200, 1000, 1000)
        self.main_layout = QVBoxLayout()

        # 2 tabs : viewer and converter
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        self.visualization_tab = QWidget()
        self.converter_tab = QWidget()
        self.tabs.addTab(self.visualization_tab, "Viewer")
        self.tabs.addTab(self.converter_tab, "Converter")

        self.init_visualization_tab()
        self.init_converter_tab()

        self.setLayout(self.main_layout)

    def init_visualization_tab(self):
        self.viz_layout = QVBoxLayout()

        # bouton pour load un fichier NIfTI
        self.load_nifti_button = QPushButton("Load a NIfTI file (.nii, .nii.gz)")
        self.load_nifti_button.clicked.connect(self.load_nifti_button_behavior)
        self.viz_layout.addWidget(self.load_nifti_button)

        # bouton pour load un fichier de tractographie
        self.load_trk_button = QPushButton("Load a tractography file (.trk, .tck)")
        self.load_trk_button.clicked.connect(self.load_trk_button_behavior)
        self.viz_layout.addWidget(self.load_trk_button)

        # intégration du viewer PyVista
        self.viewer = PyVistaViewer(self)
        self.viz_layout.addWidget(self.viewer)

        # checkboxes pour activer/désactiver l'affichage
        self.file_checkboxes = {}

        # contrôle des slices de l'image anatomique
        self.slice_controls = {}
        for orientation in ["Axial", "Coronal", "Sagittal"]:
            h_layout = QHBoxLayout()

            label = QLabel(orientation)
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(100)
            slider.setValue(0)
            slider.valueChanged.connect(lambda value, o=orientation: self.update_slice(value, o))

            input_box = QLineEdit()
            input_box.setFixedWidth(50)
            input_box.returnPressed.connect(lambda o=orientation, box=input_box: self.manual_slice_update(o, box))

            self.slice_controls[orientation] = (slider, input_box)

            h_layout.addWidget(label)
            h_layout.addWidget(slider)
            h_layout.addWidget(input_box)

            self.viz_layout.addLayout(h_layout)

        self.visualization_tab.setLayout(self.viz_layout)

    def load_nifti_button_behavior(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load a NIfTI file", "",
                                                   "NIfTI Files (*.nii *.nii.gz)")
        if file_path:
            self.nifti_object = self.loader.load_nifti(file_path)

            if not self.nifti_object: return

            self._set_sliders_max(self.nifti_object.get_dimensions())

            if self.viewer.show_nifti(self.nifti_object):
                self.add_file_checkbox(file_path, "NIfTI")

    def _set_sliders_max(self, dimensions):
        if len(dimensions) > 3: dimensions = dimensions[:3]
        x, y, z = dimensions
        self.slice_controls["Axial"][0].setMaximum(z - 1)
        self.slice_controls["Coronal"][0].setMaximum(y - 1)
        self.slice_controls["Sagittal"][0].setMaximum(x - 1)

    def load_trk_button_behavior(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load a tractography file", "",
                                                   "Tractography Files (*.trk *.tck)")
        if file_path:
            tracto_obj = self.loader.load_tractography(file_path, nifti_ref=self.nifti_object)

            if not tracto_obj: return

            if self.viewer.show_tractogram(tracto_obj):
                self.add_file_checkbox(file_path, "Tractography")

    def add_file_checkbox(self, file_path, file_type):

        checkbox = QCheckBox(f"{file_type}: {os.path.basename(file_path)}")
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda state, f=file_path: self.toggle_file_visibility(state, f))
        self.viz_layout.addWidget(checkbox)

        self.file_checkboxes[file_path] = checkbox

    def toggle_file_visibility(self, state, file_path):
        visible = state == 2
        self.viewer.set_file_visibility(file_path, visible)

    def update_slice(self, value, orientation):
        self.slice_controls[orientation][1].setText(str(value))

        if self.nifti_object:
            self.viewer.schedule_slice_update(orientation.lower(), value, self.nifti_object)

    def manual_slice_update(self, orientation, input_box):
        try:
            value = int(input_box.text())
            if 0 <= value < self.slice_controls[orientation][0].maximum():
                self.slice_controls[orientation][0].setValue(value)
                self.viewer.update_slice_position(orientation.lower(), value, self.nifti_object)
        except ValueError:
            pass

    def init_converter_tab(self):
        self.converter_layout = QVBoxLayout()

        self.load_button = QPushButton("Load from computer")
        self.load_button.clicked.connect(self.conversion_load_button_behaviour)
        self.converter_layout.addWidget(self.load_button)

        self.drop_label = QLabel("Drag and drop a .trk file here")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("QLabel { border: 2px dashed #aaa; }")
        self.drop_label.setAcceptDrops(True)
        self.drop_label.setFixedHeight(100)
        self.converter_layout.addWidget(self.drop_label)

        self.converter_tab.setLayout(self.converter_layout)

        self.drop_label.installEventFilter(self)

    def eventFilter(self, source, event):
        if event.type() == event.Type.DragEnter and source is self.drop_label:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True
        elif event.type() == event.Type.Drop and source is self.drop_label:
            if event.mimeData().hasUrls():
                file_path = event.mimeData().urls()[0].toLocalFile()
                if file_path.endswith(".trk"):
                    self.handle_dropped_file(file_path)
                return True
        return super().eventFilter(source, event)

    def conversion_load_button_behaviour(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load from computer", "",
                                                   "Tractography Files (*.trk)")
        if file_path:
            self.handle_dropped_file(file_path)

    def handle_dropped_file(self, file_path):
        file_name = os.path.basename(file_path)
        self.drop_label.setText(f"File uploaded: {file_name}")

        temp_dir = tempfile.gettempdir()
        converted_file_path = os.path.join(temp_dir, f'{file_name[:-4]}_converted.fbr')
        trk2fbr_conversion = Converter(file_path, converted_file_path, "trk_to_fbr")
        trk2fbr_conversion.convert()

        self.download_button = QPushButton(f"Download {file_name[:-4]}_converted.fbr")
        self.download_button.clicked.connect(lambda: self.download_file(converted_file_path))
        self.converter_tab.layout().addWidget(self.download_button)

    def download_file(self, file_path):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save file", file_path)
        if save_path:
            with open(file_path, 'rb') as f:
                data = f.read()
            with open(save_path, 'wb') as f:
                f.write(data)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WindowApp()
    window.show()
    sys.exit(app.exec())
