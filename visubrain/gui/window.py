# visubrain/gui/window.py

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QFileDialog, QPushButton, QLabel,
    QHBoxLayout, QSlider, QLineEdit, QComboBox, QCheckBox, QMenuBar, QMenu, QMessageBox, QDialog, QTextEdit,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from visubrain.gui.viewer import PyVistaViewer
from visubrain.gui.session import Session
from visubrain.gui.slice_controller import SliceControl
from visubrain.core.converter import Converter
from visubrain.io.nifti import NiftiFile
from visubrain.io.tractography import Tractography


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

        # Menu "About"
        about_menu = QMenu("About", self)
        menu_bar.addMenu(about_menu)

            # action pour voir la license
        view_license_action = QAction("View License", self)
        view_license_action.triggered.connect(self._on_view_license)
        about_menu.addAction(view_license_action)

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

    def _on_view_license(self):
        try:
            license_path = Path(__file__).parent.parent.parent / "LICENSE.txt"
            with open(license_path, 'r') as file:
                license_text = file.read()
        except Exception as e:
            license_text = f"Error reading license file: {e}"
        dialog = QDialog(self)
        dialog.setWindowTitle("License")
        dialog.resize(600, 400)
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setPlainText(license_text)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        dialog.setLayout(layout)
        dialog.exec()

    def _on_load_volume(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Add a volume/anatomical file", "", "(*.nii *.nii.gz)")
        if file_path:
            nifti_object = NiftiFile(file_path)

            if not nifti_object: return

            if len(nifti_object.get_dimensions()) != 3:
                QMessageBox.critical(self, "Erreur", "Bad file dimension (only 3D)")
                return

            tracto_path_list = []
            if self._current_session and self._current_session.volume_obj is None:
                index = self.session_selector.currentIndex()
                for tp in self._current_session.tracts.keys():
                    tracto_path_list.append(tp)
                self._sessions.remove(self._current_session)
                self.session_selector.removeItem(index)

            self._viewer.clear_previous_actors()
            filename = Path(file_path).name
            self._create_session(nifti_object, filename)
            self._viewer.set_working_nifti_obj(nifti_object)
            self._set_sliders_values(nifti_object.get_dimensions())
            self._viewer.render_mode(self.mode_button.currentText())
            self._set_slice_controls_enabled(self.mode_button.currentText().lower() == "slices")

            for tp in tracto_path_list:
                to = Tractography(tp, self._current_session.get_uid(), reference_nifti=nifti_object)
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

            key = (self._current_session.get_uid(), file_path)
            if key in self._viewer.tract_actors:
                QMessageBox.information(self,
                                        "Tracto déjà chargé",
                                        f"Le fichier « {Path(file_path).name} » est déjà chargé dans cette session.")
                return

            try:
                tracto_obj = Tractography(file_path, self._current_session.get_uid(), reference_nifti=self._viewer.working_nifti_obj)
            except Exception as e:
                QMessageBox.information(self, "Error loading tractography file", f"{e}")
                return

            if not tracto_obj: return

            if self._current_session:
                self._current_session.add_tract(tracto_obj)
            else:
                self._create_session(None, Path(file_path).name)
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
        self._viewer.clear_previous_actors()

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
            for (sid, file_path), checkbox in self.tracto_checkboxes.items():
                visible = (checkbox.associated_session == selected_label) and checkbox.isChecked()
                self._viewer.set_file_visibility(file_path, visible, session_id=sid)
                checkbox.setVisible(checkbox.associated_session == selected_label)

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
        if self._current_session.volume_obj:
            self._set_sliders_values(self._current_session.volume_obj.get_dimensions())

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
        sid = self._current_session.get_uid()
        checkbox = QCheckBox(f"Tractography: {Path(file_path).name}")
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(
            lambda state, f=file_path, s=sid:
            self._viewer.set_file_visibility(f, state == 2, session_id=s)
        )
        checkbox.associated_session = self.session_selector.currentText()
        checkbox.associated_session_id = sid
        # on stocke avec clé (session_id, path)
        self.tracto_checkboxes[(sid, file_path)] = checkbox
        self._left_control_panel.addWidget(checkbox)

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

        # Entry file
        h_in = QHBoxLayout()
        self.input_edit = QLineEdit()
        btn_in = QPushButton("Browse…")
        btn_in.clicked.connect(self._browse_input)
        h_in.addWidget(QLabel("Source file"))
        h_in.addWidget(self.input_edit)
        h_in.addWidget(btn_in)
        converter_layout.addLayout(h_in)

        # anat ref
        h_ref = QHBoxLayout()
        self.ref_edit = QLineEdit()
        btn_ref = QPushButton("Anatomical reference")
        btn_ref.clicked.connect(self._browse_reference)
        h_ref.addWidget(QLabel("Anatomical reference (for *.tck/*.fbr files)"))
        h_ref.addWidget(self.ref_edit)
        h_ref.addWidget(btn_ref)
        converter_layout.addLayout(h_ref)

        #output format selection
        h_format = QHBoxLayout()
        self.out_combo = QComboBox()
        h_format.addWidget(QLabel("Target format"))
        h_format.addWidget(self.out_combo)
        converter_layout.addLayout(h_format)

        # output path
        h_out = QHBoxLayout()
        self.output_edit = QLineEdit()
        btn_out = QPushButton("Save as…")
        btn_out.clicked.connect(self._browse_output)
        h_out.addWidget(QLabel("Target file"))
        h_out.addWidget(self.output_edit)
        h_out.addWidget(btn_out)
        converter_layout.addLayout(h_out)

        # convert button
        convert_btn = QPushButton("Convert")
        convert_btn.clicked.connect(self._on_convert)
        converter_layout.addWidget(convert_btn)

        self._converter_tab.setLayout(converter_layout)

    def _browse_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "", "All Files (*)")
        if not path: return
        self.input_edit.setText(path)
        ext = ''.join(Path(path).suffixes).lower().lstrip('.')
        combos = [o for (i, o) in Converter._CONVERTERS if i == ext]
        self.out_combo.clear()
        self.out_combo.addItems(combos)

    def _browse_reference(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose an anatomical reference", "", "(*.nii *.nii.gz)")
        if path:
            self.ref_edit.setText(path)

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save as", "", f"*.{self.out_combo.currentText()}")
        if path:
            self.output_edit.setText(path)

    def _on_convert(self):
        inp = self.input_edit.text().strip()
        out = self.output_edit.text().strip()
        ref = self.ref_edit.text().strip() or None
        if not inp or not out:
            QMessageBox.warning(self, "Error", "Please specify the two routes.")
            return
        try:
            conv = Converter(inp, out, anatomical_ref=ref)
            conv.convert()
            QMessageBox.information(self, "Success", "Conversion successful.")
        except Exception as e:
            QMessageBox.critical(self, "Failure", f"Conversion failed: {str(e)}")
