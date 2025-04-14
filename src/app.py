import os
import sys
import tempfile

from PyQt6.QtWidgets import QApplication, QFileDialog, QPushButton, QWidget, QVBoxLayout, QSlider, QLabel, QCheckBox, \
    QLineEdit, QHBoxLayout, QTabWidget, QMenuBar, QMenu, QComboBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from file_loader import FileLoader
from viewer import PyVistaViewer
from converter import Converter


class WindowApp(QWidget):

    def __init__(self):
        super().__init__()

        # main app layout
        self.setWindowTitle("VisuBrain")
        self.setGeometry(20, 20, 3000, 900)
        self.main_layout = QVBoxLayout()
        self.loader = FileLoader()

        # barre du menu
        self.menu_bar = QMenuBar(self)
        self.main_layout.setMenuBar(self.menu_bar)
        # Menu "Fichier"
        file_menu = QMenu("File", self)
        self.menu_bar.addMenu(file_menu)
        # menu "Statistiques"
        stat_menu = QMenu("Statistics", self)
        self.menu_bar.addMenu(stat_menu)

        # Action pour load un fichier NIfTI
        load_nifti_action = QAction("Load a NIfTI file (.nii, .nii.gz)", self)
        load_nifti_action.triggered.connect(self.load_nifti_button_behavior)
        file_menu.addAction(load_nifti_action)

        # Action pour load un fichier de tractographie
        load_trk_action = QAction("Load a tractography file (.trk, .tck)", self)
        load_trk_action.triggered.connect(self.load_trk_button_behavior)
        file_menu.addAction(load_trk_action)

        # action pour voir les stats des tracts load
        view_stats_tract_action = QAction("View tracts statistics", self)
        stat_menu.addAction(view_stats_tract_action)

        # 2 tabs : viewer and converter
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # visualization tab
        self.visualization_tab = QWidget()
        self.viz_layout = None
        self.left_control_panel = None
        self.right_control_panel = None
        self.bg_combo = None
        self.opacity_slider = None
        self.slice_opacity = 0.5
        self.slice_controls = None
        self.tracto_checkboxes = {}
        self.loaded_nifti_map = {}
        self.viewer = PyVistaViewer(self)
        self.tabs.addTab(self.visualization_tab, "Viewer")
        self.init_visualization_tab()

        # converter tab
        self.converter_tab = QWidget()
        self.converter_layout = None
        self.drop_label = None
        self.download_button = None
        self.load_button = None
        self.tabs.addTab(self.converter_tab, "Converter")
        self.init_converter_tab()

        self.setLayout(self.main_layout)

    def init_visualization_tab(self):
        # main layout for viz tab
        self.viz_layout = QHBoxLayout()
        self.left_control_panel = QVBoxLayout()
        self.right_control_panel = QVBoxLayout()

        # Contrôles des sliders
        self.slice_controls = {}
        for orientation in ["Axial", "Coronal", "Sagittal"]:
            h_layout = QHBoxLayout()
            label = QLabel(orientation)
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(100)
            slider.setValue(0)
            slider.valueChanged.connect(lambda value, o=orientation: self.change_slices_position(value, o))

            input_box = QLineEdit()
            input_box.setFixedWidth(50)
            input_box.returnPressed.connect(lambda o=orientation, box=input_box: self.manual_slice_update(o, box))

            self.slice_controls[orientation] = (slider, input_box)

            h_layout.addWidget(label)
            h_layout.addWidget(slider)
            h_layout.addWidget(input_box)

            self.left_control_panel.addLayout(h_layout)

        # Paramètre pour changer le background
        bg_layout = QHBoxLayout()
        bg_label = QLabel("Background:")
        self.bg_combo = QComboBox()
        self.bg_combo.addItem("White")
        self.bg_combo.addItem("Dark")
        self.bg_combo.currentTextChanged.connect(self.change_background_color)
        bg_layout.addWidget(bg_label)
        bg_layout.addWidget(self.bg_combo)
        self.left_control_panel.addLayout(bg_layout)

        # Paramètre pour l'opacité des slices
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("Slices opacity:")
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(50)  # par défaut à 50%
        self.opacity_slider.valueChanged.connect(self.change_slice_opacity)
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        self.left_control_panel.addLayout(opacity_layout)

        # paramètre pour le view rendering
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Rendering Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Slices")
        self.mode_combo.addItem("Volume 3D")
        self.mode_combo.currentTextChanged.connect(self.change_rendering_mode)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        self.left_control_panel.addLayout(mode_layout)

        # sélectionner (un seul) nifti parmi les NIfTI déjà load
        nifti_selector_layout = QHBoxLayout()
        nifti_selector_label = QLabel("Loaded NIfTI:")
        self.nifti_selector = QComboBox()
        self.nifti_selector.currentTextChanged.connect(self.nifti_selection_changed)
        nifti_selector_layout.addWidget(nifti_selector_label)
        nifti_selector_layout.addWidget(self.nifti_selector)
        self.left_control_panel.addLayout(nifti_selector_layout)

        # contrôle pour le zoom
        zoom_layout = QVBoxLayout()
        self.zoom_slider = QSlider(Qt.Vertical)
        self.zoom_slider.setMinimum(50)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.change_zoom)
        zoom_layout.addWidget(self.zoom_slider)
        self.right_control_panel.addLayout(zoom_layout)

        # bouton vue reinitialize
        self.reset_view_button = QPushButton()
        self.reset_view_button.clicked.connect(self.reset_cam_zoom)
        self.right_control_panel.addWidget(self.reset_view_button)

        self.viz_layout.addLayout(self.left_control_panel, stretch=1) # 20% de l'espace pour le control panel
        self.viz_layout.addWidget(self.viewer, stretch=4)  # 80% de l'espace pour le viewer
        self.viz_layout.addLayout(self.right_control_panel, stretch=1)

        self.visualization_tab.setLayout(self.viz_layout)

    def nifti_selection_changed(self, selected_label):
        """Callback quand on change la sélection des NIfTI load."""
        if selected_label in self.loaded_nifti_map:
            nifti_obj = self.loaded_nifti_map[selected_label]
            self.viewer.set_working_nifti_obj(nifti_obj)
            self._set_sliders_values(nifti_obj.get_dimensions())
            self.opacity_slider.setValue(50)

            mode = self.mode_combo.currentText()
            if mode == "Slices":
                self.viewer.show_nifti_slices()
            elif mode == "Volume 3D":
                self.viewer.show_nifti_volume()

        # màj visibilité checkboxes tracto
        for tracto_file, checkbox in self.tracto_checkboxes.items():
            self.viewer.set_file_visibility(tracto_file, False)
            checkbox.setChecked(False)
            # Affiche la checkbox seulement si associated_nifti correspond au working NIfTI
            if hasattr(checkbox, 'associated_nifti'):
                checkbox.setVisible(checkbox.associated_nifti == selected_label)
            else:
                checkbox.setVisible(False)

    def change_rendering_mode(self, mode):
        if self.viewer.working_nifti_obj is None:
            return
        if mode == "Slices":
            self.viewer.show_nifti_slices()
        elif mode == "Volume 3D":
            self.viewer.show_nifti_volume()

    def change_background_color(self, color):
        if self.viewer is not None:
            if color == "White": self.viewer.set_background("white")
            elif color == "Dark": self.viewer.set_background("black")
        self.viewer.render()

    def change_slice_opacity(self, value):
        self.slice_opacity = value / 100.0 # valeur flottante entre 0 et 1
        if self.viewer.working_nifti_obj:
            for orient in ["Axial", "Coronal", "Sagittal"]:
                current_value = self.slice_controls[orient][0].value()
                self.viewer.update_slices(orient.lower(), current_value, opacity=self.slice_opacity)

    def change_zoom(self, value):
        # 100 correspond à 1.0, donc il faut div par 100
        zoom_factor = value / 100.0
        self.viewer.set_zoom(zoom_factor)

    def reset_cam_zoom(self):
        self.zoom_slider.setValue(100)
        self.viewer.reset_view()

    def load_nifti_button_behavior(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load a NIfTI file", "",
                                                   "NIfTI Files (*.nii *.nii.gz)")
        if file_path:
            nifti_object = self.loader.load_nifti(file_path)

            if not nifti_object: return

            display_name = os.path.basename(file_path)
            if display_name not in self.loaded_nifti_map:
                self.loaded_nifti_map[display_name] = nifti_object
                self.nifti_selector.addItem(display_name)
            self.nifti_selector.setCurrentText(display_name)

            self.viewer.set_working_nifti_obj(nifti_object)
            self._set_sliders_values(nifti_object.get_dimensions())

            if self.mode_combo.currentText() == "Slices":
                if self.viewer.show_nifti_slices():
                    pass
            else:
                self.viewer.show_nifti_volume()

    def _set_sliders_values(self, dimensions):
        if len(dimensions) > 3:
            dimensions = dimensions[:3]
        x, y, z = dimensions
        axial_slider = self.slice_controls["Axial"][0]
        coronal_slider = self.slice_controls["Coronal"][0]
        sagittal_slider = self.slice_controls["Sagittal"][0]
        axial_slider.setMaximum(z - 1)
        axial_slider.setValue((z - 1) // 2)
        coronal_slider.setMaximum(y - 1)
        coronal_slider.setValue((y - 1) // 2)
        sagittal_slider.setMaximum(x - 1)
        sagittal_slider.setValue((x - 1) // 2)

    def load_trk_button_behavior(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load a tractography file", "",
                                                   "Tractography Files (*.trk *.tck)")
        if file_path:
            tracto_obj = self.loader.load_tractography(file_path, nifti_ref=self.viewer.working_nifti_obj)

            if not tracto_obj: return

            if self.viewer.show_tractogram(tracto_obj):
                self.add_tracto_checkbox(file_path)

    def add_tracto_checkbox(self, file_path):

        checkbox = QCheckBox(f"Tractography: {os.path.basename(file_path)}")
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda state, f=file_path: self.toggle_file_visibility(state, f))
        self.left_control_panel.addWidget(checkbox)

        checkbox.associated_nifti = self.nifti_selector.currentText()
        self.tracto_checkboxes[file_path] = checkbox

    def toggle_file_visibility(self, state, file_path):
        visible = state == 2
        self.viewer.set_file_visibility(file_path, visible)

    def change_slices_position(self, value, orientation):
        self.slice_controls[orientation][1].setText(str(value))

        if self.viewer.working_nifti_obj:
            self.viewer.schedule_slice_update(orientation.lower(), value, self.slice_opacity)

    def manual_slice_update(self, orientation, input_box):
        try:
            value = int(input_box.text())
            if 0 <= value < self.slice_controls[orientation][0].maximum():
                self.slice_controls[orientation][0].setValue(value)
                self.viewer.update_slices(orientation.lower(), value, opacity=self.slice_opacity)
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
