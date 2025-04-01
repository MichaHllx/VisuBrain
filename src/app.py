import os
import sys
import tempfile

from PyQt6.QtWidgets import QApplication, QFileDialog, QPushButton, QWidget, QVBoxLayout, QSlider, QLabel, QCheckBox, \
    QLineEdit, QHBoxLayout, QTabWidget
from PyQt6.QtCore import Qt

from file_loader import load_nifti, load_trk
from viewer import PyVistaViewer
from converter import Converter


class WindowApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(200, 200, 800, 800)

        self.layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        self.visualization_tab = QWidget()
        self.converter_tab = QWidget()

        self.tabs.addTab(self.visualization_tab, "Visualisation")
        self.tabs.addTab(self.converter_tab, "Convertisseur")

        self.init_visualization_tab()
        self.init_converter_tab()

        self.setLayout(self.layout)

    def init_visualization_tab(self):
        layout = QVBoxLayout()

        self.load_nifti_button = QPushButton("Charger un fichier NIfTI (.nii, .nii.gz)")
        self.load_nifti_button.clicked.connect(self.load_nifti_button_behavior)
        layout.addWidget(self.load_nifti_button)

        self.load_trk_button = QPushButton("Charger un fichier de tractographie (.trk, .tck)")
        self.load_trk_button.clicked.connect(self.load_trk_button_behavior)
        layout.addWidget(self.load_trk_button)

        self.viewer = PyVistaViewer(self)
        layout.addWidget(self.viewer)

        self.file_checkboxes = {}
        self.loaded_files = {}

        self.slice_controls = {}
        for orientation in ["Axial", "Coronal", "Sagittal"]:
            h_layout = QHBoxLayout()
            label = QLabel(orientation)
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(1)
            slider.setMaximum(100)
            slider.setValue(1)
            slider.valueChanged.connect(lambda value, o=orientation: self.update_slice(value, o))

            input_box = QLineEdit()
            input_box.setFixedWidth(50)
            input_box.returnPressed.connect(lambda o=orientation, box=input_box: self.manual_slice_update(o, box))

            self.slice_controls[orientation] = (slider, input_box)
            h_layout.addWidget(label)
            h_layout.addWidget(slider)
            h_layout.addWidget(input_box)
            layout.addLayout(h_layout)

        self.visualization_tab.setLayout(layout)

    def load_nifti_button_behavior(self):
        global data
        file_path, _ = QFileDialog.getOpenFileName(self, "Charger un fichier NIfTI", "", "NIfTI Files (*.nii *.nii.gz)")
        if file_path:
            data, affine = load_nifti(file_path)
            self.update_sliders_max(data.shape)
            self.viewer.show_nifti(file_path, data)
            self.add_file_checkbox(file_path, "NIfTI")
            self.loaded_files[file_path] = "NIfTI"

    def update_sliders_max(self, dimensions):
        x, y, z = dimensions
        self.slice_controls["Axial"][0].setMaximum(z - 1)  # Z    |
        self.slice_controls["Coronal"][0].setMaximum(y - 1)  # Y  |---> RAS+mm
        self.slice_controls["Sagittal"][0].setMaximum(x - 1)  # X |

    def load_trk_button_behavior(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Charger un fichier Tractographie", "", "Tractography Files (*.trk *.tck)")
        if file_path:
            streamlines, trk = load_trk(file_path)
            self.viewer.show_tractogram(file_path, streamlines, trk)
            self.add_file_checkbox(file_path, "Tractographie")
            self.loaded_files[file_path] = "Tractographie"

    def add_file_checkbox(self, file_path, file_type):
        checkbox = QCheckBox(f"{file_type}: {file_path.split('/')[-1]}")
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda state, f=file_path: self.toggle_file_visibility(state, f))
        self.layout.addWidget(checkbox)
        self.file_checkboxes[file_path] = checkbox

    def toggle_file_visibility(self, state, file_path):
        visible = False
        if state == 2:
            visible = True
        self.viewer.set_file_visibility(file_path, visible)

    def update_slice(self, value, orientation):
        self.slice_controls[orientation][1].setText(str(value))
        self.viewer.update_slice_position(orientation.lower(), value, data)

    def manual_slice_update(self, orientation, input_box):
        try:
            value = int(input_box.text())
            if 0 < value < self.slice_controls[orientation][0].maximum():
                self.slice_controls[orientation][0].setValue(value)
                self.viewer.update_slice_position(orientation.lower(), value, data)
        except ValueError:
            pass

    def init_converter_tab(self):
        layout = QVBoxLayout()

        self.load_button = QPushButton("Charger depuis l'ordinateur")
        self.load_button.clicked.connect(self.handle_button_load)
        layout.addWidget(self.load_button)

        self.drop_label = QLabel("Glissez un fichier .trk ici")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("QLabel { border: 2px dashed #aaa; }")
        self.drop_label.setAcceptDrops(True)
        self.drop_label.setFixedHeight(100)
        layout.addWidget(self.drop_label)

        self.converter_tab.setLayout(layout)

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

    def handle_button_load(self, ):
        file_path, _ = QFileDialog.getOpenFileName(self, "Charger depuis l'ordinateur", "", "Tractography Files (*.trk)")
        if file_path:
            self.handle_dropped_file(file_path)

    def handle_dropped_file(self, file_path):
        # gestion du fichier trk déposé
        file_name = file_path.split('/')[-1]
        self.drop_label.setText(f"Fichier déposé : {file_name}")

        # Créer un fichier temporaire pour le fichier converti
        temp_dir = tempfile.gettempdir()
        converted_file_path = os.path.join(temp_dir, f'{file_name[:-4]}_converted.fbr')

        # Convertir le fichier .trk en .fbr
        trk2fbr_conversion = Converter(file_path, converted_file_path, "trk_to_fbr")
        trk2fbr_conversion.convert()

        # Ajouter un bouton de téléchargement
        self.download_button = QPushButton(f"Télécharger {file_name[:-4]}_converted.fbr")
        self.download_button.clicked.connect(lambda: self.download_file(converted_file_path))
        self.converter_tab.layout().addWidget(self.download_button)

    def download_file(self, file_path):
        save_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le fichier", file_path)
        if save_path:
            with open(file_path, 'rb') as f:
                data = f.read()
            with open(save_path, 'wb') as f:
                f.write(data)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WindowApp()
    window.show()
    sys.exit(app.exec_())
