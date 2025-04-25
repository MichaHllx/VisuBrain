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
from visubrain.gui.session import Session
from visubrain.gui.slice_controller import SliceControl
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
        self._sessions = []
        self._current_session = None

        self._build_menu_bar()
        # 2 tabs : viewer and converter
        self._init_tabs()

        self.setLayout(self._main_layout)

    def _build_menu_bar(self):
        menu_bar = QMenuBar(self)
        self._main_layout.setMenuBar(menu_bar)

        # Menu "Fichier"
        file_menu = QMenu("File", self)
        menu_bar.addMenu(file_menu)

            # Action pour load un fichier NIfTI
        load_nifti_action = QAction("Add a volume/anatomical file (.nii, .nii.gz)", self)
        load_nifti_action.triggered.connect(self._on_load_volume)
        file_menu.addAction(load_nifti_action)
            # Action pour load un fichier de tractographie
        load_trk_action = QAction("Add a tractography file (.trk, .tck)", self)
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
        self._user_sessions = []
        self._tabs.addTab(self._visualization_tab, "Viewer")
        self._build_viz_tab()

    def _build_viz_tab(self):
        # main layout for viz tab
        viz_layout = QHBoxLayout()

        # session selector
        session_selector_layout = QHBoxLayout()
        self.session_selector = QComboBox()
        self.session_selector.currentTextChanged.connect(self.switch_session)
        session_selector_layout.addWidget(self.session_selector)
        self.session_selector.setVisible(False)
        self._left_control_panel.insertLayout(0, session_selector_layout)

        # paramètre pour renommer la session
        rename_layout = QHBoxLayout()
        self.rename_lineedit = QLineEdit()
        self.rename_button = QPushButton("New session name")
        self.rename_button.clicked.connect(self.rename_current_session)
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
            input_box = QLineEdit()
            input_box.setFixedWidth(50)

            control = SliceControl(orientation, slider, input_box)
            control.connect_slider_callback(self.change_slices_position)
            self.slice_controls[orientation] = control

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
        self._opacity_slider.setSingleStep(1)
        self._opacity_slider.setValue(50)  # par défaut : 0.5
        self._opacity_slider.valueChanged.connect(self.change_slice_opacity)
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self._opacity_slider)
        self._left_control_panel.addLayout(opacity_layout)

        # paramètre pour le view rendering
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Rendering Mode:")
        self.mode_button = QComboBox()
        self.mode_button.addItem("Slices")
        self.mode_button.addItem("Volume 3D")
        self.mode_button.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_button)
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

    def _on_load_volume(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Add a volume/anatomical file", "", "(*.nii *.nii.gz)")
        if file_path:
            nifti_object = load_nifti(file_path)

            if not nifti_object: return

            tracto_path_list = []
            if self._current_session and self._current_session.volume_obj is None:
                index = self.session_selector.currentIndex()
                for tp in self._current_session.tracts.keys():
                    tracto_path_list.append(tp)
                self._sessions.remove(self._current_session)
                self.session_selector.removeItem(index)

            filename = os.path.basename(file_path)
            self._create_session(nifti_object, filename)
            self._viewer.set_working_nifti_obj(nifti_object)
            self._set_sliders_values(nifti_object.get_dimensions())
            self._viewer.render_mode(self.mode_button.currentText())
            self._set_slice_controls_enabled(self.mode_button.currentText().lower() == "slices")

            for tp in tracto_path_list:
                to = load_tractography(tp, nifti_ref=nifti_object)
                self._current_session.add_tract(to)
                self._viewer.show_tractogram(to)
                self.add_tracto_checkbox(tp)
            self._current_session.apply()

    def _set_sliders_values(self, dimensions):
        if len(dimensions) > 3:
            dimensions = dimensions[:3]

        self._set_sliders_maximum(dimensions)
        x, y, z = dimensions
        for ori, control in self.slice_controls.items():
            if ori == "Axial": control.set_value((z - 1) // 2)
            elif ori == "Coronal": control.set_value((y - 1) // 2)
            elif ori == "Sagittal": control.set_value((x - 1) // 2)

    def change_slice_opacity(self, value):
        self._current_session.opacity = value / 100.0 # valeur flottante entre 0 et 1
        if self._viewer.working_nifti_obj:
            self._viewer.update_slice_opacity(self._current_session.opacity)

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

    def _on_load_streamlines(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Add a tractography file", "", "(*.trk *.tck)")
        if file_path:
            tracto_obj = load_tractography(file_path, nifti_ref=self._viewer.working_nifti_obj)

            if not tracto_obj: return

            if self._current_session:
                self._current_session.add_tract(tracto_obj)
            else:
                self._create_session(None, os.path.basename(file_path))
                self._current_session.add_tract(tracto_obj)
                self._set_slice_controls_enabled(False)
                self.mode_button.setEnabled(False)

            self._viewer.show_tractogram(tracto_obj)
            self.add_tracto_checkbox(file_path)

    def view_tracts_statistics(self):
        if not self._current_session or not self._current_session.tracts:
            QMessageBox.information(self, "Tractography Statistics", "No tractography data available")
            return

        report_lines = self._current_session.tract_statistics()
        QMessageBox.information(self, "Tractography Statistics", "\n\n".join(report_lines))

    def _create_session(self, volume_obj, filename):
        display_name = f"Session {len(self._sessions) + 1}: " + filename
        session = Session(display_name, volume_obj, self._viewer)
        self._sessions.append(session)
        self.session_selector.addItem(display_name)
        self.session_selector.setCurrentText(display_name)
        self._current_session = session
        self.session_selector.setVisible(True)
        self.rename_button.setVisible(True)

    def switch_session(self, selected_label):
        # on save l'état de la current sess
        self._save_current_session_state()

        session = next((f for f in self._sessions if f.display_name == selected_label), None)
        if not session: return
        self._current_session = session
        # màj viewer avec session
        session.apply()

        # màj UI avec session
        if session.volume_obj is not None:
            self._set_sliders_maximum(session.volume_obj.get_dimensions())
            for ori, control in self.slice_controls.items():
                control.set_value(session.slice_positions[ori.lower()])
            self._opacity_slider.setValue(int(session.opacity * 100))
            self.zoom_slider.setValue(int(session.zoom_factor * 100))
            self._viewer.change_background(session.background_color)
            self.mode_button.setCurrentText(session.rendering_mode)
            self._set_slice_controls_enabled(session.rendering_mode.lower() == "slices")

        if self.tracto_checkboxes:
            for file_path, checkbox in self.tracto_checkboxes.items():
                checkbox.setVisible(checkbox.associated_session == selected_label)
                if checkbox.associated_session == selected_label:
                    self._viewer.set_file_visibility(file_path, checkbox.isChecked())
                else:
                    self._viewer.set_file_visibility(file_path, False)

    def _save_current_session_state(self):
        if self._current_session and self._current_session.volume_obj:
            for ori, control in self.slice_controls.items():
                self._current_session.slice_positions[ori.lower()] = control.get_value()
            self._current_session.opacity = self._opacity_slider.value() / 100.0
            self._current_session.zoom_factor = self.zoom_slider.value() / 100.0
            self._current_session.background_color = self._viewer.background_color.name
            self._current_session.rendering_mode = self.mode_button.currentText()

    def on_mode_changed(self, mode):
        self._viewer.render_mode(mode)
        self._set_slice_controls_enabled(mode.lower() == "slices")

    def _set_sliders_maximum(self, dimensions):
        x, y, z = dimensions
        for ori, control in self.slice_controls.items():
            if ori == "Axial": control.set_max(z - 1)
            elif ori == "Coronal": control.set_max(y - 1)
            elif ori == "Sagittal": control.set_max(x - 1)

    def rename_current_session(self):
        self.rename_lineedit.setVisible(True)
        self.rename_button.setText("Rename")
        if not self._current_session:
            return
        new_name = self.rename_lineedit.text().strip()
        if not new_name:
            return

        old_name = self._current_session.display_name
        self._current_session.display_name = new_name

        index = self.session_selector.findText(old_name)
        if index != -1:
            self.session_selector.setItemText(index, new_name)

        for file_path, checkbox in self.tracto_checkboxes.items():
            if checkbox.associated_session == old_name:
                checkbox.associated_session = new_name
                checkbox.setVisible(True)

        self._current_session.apply()
        self.rename_lineedit.clear()
        self.rename_lineedit.setVisible(False)
        self.rename_button.setText("New session name")

    def add_tracto_checkbox(self, file_path):
        checkbox = QCheckBox(f"Tractography: {os.path.basename(file_path)}")
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda state, f=file_path: self._viewer.set_file_visibility(f, state==2))
        self._left_control_panel.addWidget(checkbox)

        checkbox.associated_session = self.session_selector.currentText()
        self.tracto_checkboxes[file_path] = checkbox

    def _set_slice_controls_enabled(self, enabled: bool):
        for control in self.slice_controls.values():
            control.slider.setEnabled(enabled)
            control.line_edit.setEnabled(enabled)
        self._opacity_slider.setEnabled(enabled)

    def change_slices_position(self, value, orientation):
        if self._viewer.working_nifti_obj:
            self._viewer.schedule_slice_update(orientation.lower(), value, self._current_session.opacity)

    def _init_converter_tab(self):
        self._converter_tab = QWidget()
        self._tabs.addTab(self._converter_tab, "Converter")
        self._build_converter_tab()

    def _build_converter_tab(self):
        converter_layout = QVBoxLayout()

        load_button = QPushButton("Load from computer")
        load_button.clicked.connect(self.conversion_load_button_behaviour)
        converter_layout.addWidget(load_button)

        self.drop_label = QLabel("Drag and drop a .trk file here")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("QLabel { border: 2px dashed #aaa; }")
        self.drop_label.setAcceptDrops(True)
        self.drop_label.setFixedHeight(100)
        converter_layout.addWidget(self.drop_label)

        self._converter_tab.setLayout(converter_layout)

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
