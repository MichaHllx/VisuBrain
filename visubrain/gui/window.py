# visubrain/gui/window.py
import os
import tempfile

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QFileDialog, QPushButton, QLabel,
    QHBoxLayout, QSlider, QLineEdit, QComboBox, QCheckBox, QMenuBar, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from visubrain.gui.viewer import PyVistaViewer
from visubrain.gui.user_folder import UserFolder
from visubrain.core.converter import Converter
from visubrain.io.loader import load_nifti, load_tractography


class WindowApp(QWidget):

    def __init__(self):
        super().__init__()

        # main app layout
        self.setWindowTitle("VisuBrain")
        self.setGeometry(20, 20, 3000, 900)
        self._main_layout = QVBoxLayout()

        self._viewer = PyVistaViewer(self)

        self._build_menu_bar()
        # 2 tabs : viewer and converter
        self._folders = []
        self._current_folder = None
        self._init_tabs()

        self.setLayout(self._main_layout)

    def _build_menu_bar(self):
        menu_bar = QMenuBar(self)
        self._main_layout.setMenuBar(menu_bar)

        # Menu "Fichier"
        file_menu = QMenu("File", self)
        menu_bar.addMenu(file_menu)

            # Action pour load un fichier NIfTI
        load_nifti_action = QAction("Load a volume/anatomical file (.nii, .nii.gz)", self)
        load_nifti_action.triggered.connect(self._on_load_volume)
        file_menu.addAction(load_nifti_action)
            # Action pour load un fichier de tractographie
        load_trk_action = QAction("Load a tractography file (.trk, .tck)", self)
        load_trk_action.triggered.connect(self._on_load_streamlines)
        file_menu.addAction(load_trk_action)
            # action pour prendre un screenshot
        screenshot_action = QAction("Take a screenshot", self)
        screenshot_action.triggered.connect(self.take_screenshot)
        file_menu.addAction(screenshot_action)

        # Menu "Statistiques"
        stat_menu = QMenu("Statistics", self)
        menu_bar.addMenu(stat_menu)

            # action pour voir les stats des tracts load
        view_stats_tract_action = QAction("Tracts statistics", self)
        view_stats_tract_action.triggered.connect(self.view_tracts_statistics)
        stat_menu.addAction(view_stats_tract_action)

    def _init_tabs(self):
        self._tabs = QTabWidget()
        self._main_layout.addWidget(self._tabs)
        self._init_viz_tab()
        self._init_converter_tab()

    def _init_viz_tab(self):
        self._visualization_tab = QWidget()
        self._left_control_panel = QVBoxLayout()
        self._right_control_panel = QVBoxLayout()
        self._opacity_slider = QSlider(Qt.Horizontal)
        self.slice_controls = {}
        self.tracto_checkboxes = {}
        self._user_folders = []
        self._tabs.addTab(self._visualization_tab, "Viewer")
        self._build_viz_tab()

    def _init_converter_tab(self):
        self._converter_tab = QWidget()
        self.converter_layout = None
        self.drop_label = None
        self.load_button = None
        self._tabs.addTab(self._converter_tab, "Converter")
        self._build_converter_tab()

    def _build_viz_tab(self):
        # main layout for viz tab
        viz_layout = QHBoxLayout()

        # folder selector
        folder_selector_layout = QHBoxLayout()
        self.folder_selector = QComboBox()
        self.folder_selector.currentTextChanged.connect(self.switch_folder)
        folder_selector_layout.addWidget(self.folder_selector)
        self.folder_selector.setVisible(False)
        self._left_control_panel.insertLayout(0, folder_selector_layout)

        # paramètre pour renommer le folder
        rename_layout = QHBoxLayout()
        self.rename_lineedit = QLineEdit()
        self.rename_button = QPushButton("Rename folder")
        self.rename_button.clicked.connect(self.rename_current_folder)
        rename_layout.addWidget(self.rename_lineedit)
        rename_layout.addWidget(self.rename_button)
        self.rename_button.setVisible(False)
        self.rename_lineedit.setVisible(False)
        self._left_control_panel.insertLayout(1, rename_layout)

        # Contrôles des sliders
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

            self._left_control_panel.addLayout(h_layout)

        # Paramètre pour changer le background
        bg_layout = QHBoxLayout()
        bg_label = QLabel("Background:")
        bg_combo = QComboBox()
        bg_combo.addItem("White")
        bg_combo.addItem("Black")
        bg_combo.currentTextChanged.connect(self._viewer.change_background)
        bg_layout.addWidget(bg_label)
        bg_layout.addWidget(bg_combo)
        self._left_control_panel.addLayout(bg_layout)

        # Paramètre pour l'opacité des slices
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("Slices opacity:")
        self._opacity_slider.setMinimum(0)
        self._opacity_slider.setMaximum(100)
        self._opacity_slider.setValue(50)  # par défaut à 50%
        self._opacity_slider.valueChanged.connect(self.change_slice_opacity)
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self._opacity_slider)
        self._left_control_panel.addLayout(opacity_layout)

        # paramètre pour le view rendering
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Rendering Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Slices")
        self.mode_combo.addItem("Volume 3D")
        self.mode_combo.currentTextChanged.connect(self.rendering_mode_selection)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        self._left_control_panel.addLayout(mode_layout)

        # contrôle pour le zoom
        zoom_layout = QVBoxLayout()
        self.zoom_slider = QSlider(Qt.Vertical)
        self.zoom_slider.setMinimum(50)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._viewer.set_zoom)
        zoom_layout.addWidget(self.zoom_slider)
        self._right_control_panel.addLayout(zoom_layout)

        # bouton vue reinitialize
        self.reset_view_button = QPushButton("Reset\nzoom")
        self.reset_view_button.setFixedSize(50, 40)
        self.reset_view_button.clicked.connect(self.reset_cam_zoom)
        self._right_control_panel.addWidget(self.reset_view_button)

        viz_layout.addLayout(self._left_control_panel, stretch=1) # 20% de l'espace pour le control panel
        viz_layout.addWidget(self._viewer, stretch=4)  # 80% de l'espace pour le viewer
        viz_layout.addLayout(self._right_control_panel, stretch=1)

        self._visualization_tab.setLayout(viz_layout)

    def _build_converter_tab(self):
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

        self._converter_tab.setLayout(self.converter_layout)

        self.drop_label.installEventFilter(self)

    def rendering_mode_selection(self, mode):
        if mode == "Slices":
            self._viewer.show_nifti_slices()
        elif mode == "Volume 3D":
            self._viewer.show_nifti_volume()

    def change_slice_opacity(self, value):
        self._current_folder.opacity = value / 100.0 # valeur flottante entre 0 et 1
        if self._viewer.working_nifti_obj:
            for orient in ["Axial", "Coronal", "Sagittal"]:
                current_value = self.slice_controls[orient][0].value()
                self._viewer.update_slices(orient.lower(), current_value, opacity=self._current_folder.opacity)

    def reset_cam_zoom(self):
        self.zoom_slider.setValue(100)
        self._viewer.reset_view()

    def take_screenshot(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Save screenshot", "", "PNG Files (*.png)")
        if fileName:
            try:
                self._viewer.screenshot(filename=fileName)
                QMessageBox.information(self, "Screenshot", f"Screenshot saved to: {fileName}")
            except Exception as e:
                QMessageBox.information(self, "Screenshot", f"Error saving screenshot: {e}")

    def view_tracts_statistics(self):
        if not self._current_folder or not self._current_folder.tracts:
            QMessageBox.information(self, "Tractography Statistics", "No tractography data available")
            return

        report_lines = self._current_folder.tract_statistics()
        QMessageBox.information(self, "Tractography Statistics", "\n\n".join(report_lines))

    def _on_load_volume(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load a volume/anatomical file", "", "(*.nii *.nii.gz)")
        if file_path:
            nifti_object = load_nifti(file_path)

            if not nifti_object: return

            filename = os.path.basename(file_path)
            self._create_folder(nifti_object, filename)
            self._viewer.set_working_nifti_obj(nifti_object)
            self._set_sliders_values(nifti_object.get_dimensions())
            self.rendering_mode_selection(self.mode_combo.currentText())

    def _set_sliders_values(self, dimensions):
        if len(dimensions) > 3:
            dimensions = dimensions[:3]

        self._set_sliders_maximum(dimensions)
        x, y, z = dimensions
        self.slice_controls["Axial"][0].setValue((z - 1) // 2)
        self.slice_controls["Coronal"][0].setValue((y - 1) // 2)
        self.slice_controls["Sagittal"][0].setValue((x - 1) // 2)

    def _set_sliders_maximum(self, dimensions):
        x, y, z = dimensions
        self.slice_controls["Axial"][0].setMaximum(z - 1)
        self.slice_controls["Coronal"][0].setMaximum(y - 1)
        self.slice_controls["Sagittal"][0].setMaximum(x - 1)

    def _on_load_streamlines(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load a tractography file", "", "(*.trk *.tck)")
        if file_path:
            tracto_obj = load_tractography(file_path, nifti_ref=self._viewer.working_nifti_obj)

            if not tracto_obj: return

            if self._current_folder:
                self._current_folder.add_tract(tracto_obj)
            else:
                self._create_folder(None, os.path.basename(file_path))
                self._current_folder.add_tract(tracto_obj)

            self._viewer.show_tractogram(tracto_obj)
            self.add_tracto_checkbox(file_path)

    def _create_folder(self, anat_obj, filename):
        nifti_obj = anat_obj
        display_name = f"Folder {len(self._folders) + 1}: " + filename
        folder = UserFolder(display_name, nifti_obj, self._viewer)
        self._folders.append(folder)
        self.folder_selector.addItem(display_name)
        self.folder_selector.setCurrentText(display_name)
        self._current_folder = folder
        self.folder_selector.setVisible(True)
        self.rename_button.setVisible(True)

    def switch_folder(self, selected_label):
        folder = next((f for f in self._folders if f.display_name == selected_label), None)
        if not folder: return

        # stocker l'état du current folder
        if self._current_folder and self._current_folder.volume_obj:
            for ori, (slider, _) in self.slice_controls.items():
                self._current_folder.slice_positions[ori.lower()] = slider.value()
            self._current_folder.opacity = self._opacity_slider.value() / 100.0
            self._current_folder.zoom_factor = self.zoom_slider.value() / 100.0
            self._current_folder.background_color = self._viewer.background_color.name

        self._current_folder = folder
        folder.apply()

        # màj UI avec le nouveau folder
        if folder.volume_obj is not None:
            dims = folder.volume_obj.get_dimensions()
            self._set_sliders_maximum(dims)
            for ori, (slider, _) in self.slice_controls.items():
                slider.setValue(folder.slice_positions[ori.lower()])
            self._opacity_slider.setValue(int(folder.opacity * 100))
            self.zoom_slider.setValue(int(folder.zoom_factor * 100))
            self._viewer.change_background(folder.background_color)

        if self.tracto_checkboxes:
            for file_path, checkbox in self.tracto_checkboxes.items():
                checkbox.setVisible(checkbox.associated_folder == selected_label)
                if checkbox.associated_folder == selected_label:
                    self._viewer.set_file_visibility(file_path, checkbox.isChecked())
                else:
                    self._viewer.set_file_visibility(file_path, False)

    def rename_current_folder(self):
        self.rename_lineedit.setVisible(True)
        if not self._current_folder:
            return
        new_name = self.rename_lineedit.text().strip()
        if not new_name:
            return

        old_name = self._current_folder.display_name
        self._current_folder.display_name = new_name

        index = self.folder_selector.findText(old_name)
        if index != -1:
            self.folder_selector.setItemText(index, new_name)

        for file_path, checkbox in self.tracto_checkboxes.items():
            if checkbox.associated_folder == old_name:
                checkbox.associated_folder = new_name

        self.rename_lineedit.clear()
        self.rename_lineedit.setVisible(False)

    def add_tracto_checkbox(self, file_path):
        checkbox = QCheckBox(f"Tractography: {os.path.basename(file_path)}")
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda state, f=file_path: self._viewer.set_file_visibility(f, state==2))
        self._left_control_panel.addWidget(checkbox)

        checkbox.associated_folder = self.folder_selector.currentText()
        self.tracto_checkboxes[file_path] = checkbox

    def change_slices_position(self, value, orientation):
        self.slice_controls[orientation][1].setText(str(value))

        if self._viewer.working_nifti_obj:
            self._viewer.schedule_slice_update(orientation.lower(), value, self._current_folder.opacity)

    def manual_slice_update(self, orientation, input_box):
        try:
            value = int(input_box.text())
            if 0 <= value < self.slice_controls[orientation][0].maximum():
                self.slice_controls[orientation][0].setValue(value)
                self._viewer.update_slices(orientation.lower(), value, opacity=self._current_folder.opacity)
        except ValueError:
            pass

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
        file_path, _ = QFileDialog.getOpenFileName(self, "Load from computer", "", "(*.trk)")
        if file_path:
            self.handle_dropped_file(file_path)

    def handle_dropped_file(self, file_path):
        file_name = os.path.basename(file_path)
        self.drop_label.setText(f"File uploaded: {file_name}")

        temp_dir = tempfile.gettempdir()
        converted_file_path = os.path.join(temp_dir, f'{file_name[:-4]}_converted.fbr')
        trk2fbr_conversion = Converter(file_path, converted_file_path, "trk_to_fbr")
        trk2fbr_conversion.convert()

        download_button = QPushButton(f"Download {file_name[:-4]}_converted.fbr")
        download_button.clicked.connect(lambda: self.download_file(converted_file_path))
        self._converter_tab.layout().addWidget(download_button)

    def download_file(self, file_path):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save file", file_path)
        if save_path:
            with open(file_path, 'rb') as f:
                data = f.read()
            with open(save_path, 'wb') as f:
                f.write(data)
