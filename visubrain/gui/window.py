"""
visubrain/gui/window.py

Main GUI module for the VisuBrain application.

This module defines the WindowApp class, which implements the main application window
for VisuBrain. It manages all user interface elements, session handling, data loading
(anatomical volumes and tractography), as well as the integration of the main viewer and
converter. The window supports multiple sessions, advanced visualization controls,
and user workflows for neuroimaging data exploration and file format conversion.

Classes:
    WindowApp: Main application window for VisuBrain, managing GUI logic and workflow.
"""


from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QFileDialog, QPushButton, QLabel,
    QHBoxLayout, QSlider, QLineEdit, QComboBox, QCheckBox, QMenuBar, QMenu,
    QMessageBox, QDialog, QTextEdit, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from visubrain.gui.viewer import PyVistaViewer
from visubrain.utils.session import Session
from visubrain.utils.slice_controller import SliceControl
from visubrain.core.converter import Converter
from visubrain.io.nifti import NiftiFile
from visubrain.io.tractography import Tractography


class WindowApp(QWidget):
    """
    Main application window for VisuBrain, orchestrating all GUI logic.

    This window coordinates the interaction between user actions (file loading, visualization mode
     changes, etc.), the anatomical and tractography data (NiftiFile, Tractography), and the 3D
      viewer (PyVistaViewer).
    It allows for multi-session support, synchronized GUI controls (slice, zoom, mode), and provides
     entry points for all main VisuBrain workflows: viewing, converting, and reporting on data.

    Attributes:
        _main_layout (QVBoxLayout): The main vertical layout.
        _viewer (PyVistaViewer): 3D/2D anatomical and tractography viewer widget.
        _sessions (list of Session): All user-created sessions, each holding a unique dataset and
         state.
        _current_session (Session or None): Currently selected session.
        _tabs (QTabWidget): Main tab container (Viewer, Converter, etc.).
        _visualization_tab (QWidget): Main tab for the viewer.
        _left_control_panel (QVBoxLayout): Panel for viewer controls (slice, mode, opacity).
        _right_control_panel (QVBoxLayout): Panel for viewer controls (zoom, reset).
        slice_controls (dict): Orientation to SliceControl mapping for slice navigation.
        tracto_checkboxes (dict): Mapping of (session, file_path) to tractography visibility
        checkbox.
    """

    def __init__(self):
        """
        Initialize the main application window, layouts, and all interactive GUI controls.
        """
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
        """
        Build the main menu bar (File, Statistics, About), connecting to all application actions.

        The menu enables file loading (NIfTI, tractography), screenshots, statistics, and license
        view.
        """
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
        """
        Create and add all main application tabs, such as the Viewer and Converter.
        """
        self._tabs = QTabWidget()
        self._main_layout.addWidget(self._tabs)
        self._init_viz_tab()
        self._init_converter_tab()

    def _init_viz_tab(self):
        """
        Initialize the Viewer tab with its control panels, slice controls, and viewer widget.

        This includes all anatomical and tractography navigation tools.
        """
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
        """
        Build the layout and all interactive controls for the Viewer tab.

        Controls include session switching, renaming, slice navigation, background, opacity,
        render mode, time/frame (for 4D), and zoom.
        """
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
            slider = QSlider(Qt.Horizontal)
            input_box = QLineEdit()
            input_box.setFixedWidth(50)

            control = SliceControl(orientation, slider, input_box)
            control.connect_slider_callback(self.change_slices_position)
            self.slice_controls[orientation] = control

            h_layout.addWidget(QLabel(orientation))
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

        # contrôle des séries temporelles (fichier 4D)
        time_layout = QHBoxLayout()
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setVisible(False)  # On l'affiche seulement pour les volumes 4D
        self.time_slider.valueChanged.connect(self.on_time_slider_changed)
        self.label_time_slider = QLabel("Time/frame:")
        self.label_time_slider.setVisible(False)
        time_layout.addWidget(self.label_time_slider)
        time_layout.addWidget(self.time_slider)
        self._left_control_panel.addLayout(time_layout)

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

        # 20% de l'espace pour le control panel
        viz_layout.addLayout(self._left_control_panel, stretch=1)
        # 80% de l'espace pour le viewer
        viz_layout.addWidget(self._viewer, stretch=4)
        viz_layout.addLayout(self._right_control_panel, stretch=1)

        self._visualization_tab.setLayout(viz_layout)

    def on_time_slider_changed(self, value):
        """
        Callback to update the viewer's displayed frame for 4D NIfTI data.

        Args:
            value (int): New time frame index selected by the user.
        """
        if self._viewer.working_nifti_obj and hasattr(self._viewer.working_nifti_obj, "is_4d"):
            if self._viewer.working_nifti_obj.is_4d():
                self._viewer.set_time_frame(value)

    def _on_view_license(self):
        """
        Display the VisuBrain license in a modal dialog.
        """
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
        """
        Open a file dialog to load a NIfTI anatomical volume, creating a new Session.

        On successful loading, resets or creates a new session, updates all GUI controls,
        and synchronizes the 3D viewer.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Add a volume/anatomical file", "",
                                                   "(*.nii *.nii.gz)")
        if file_path:
            try:
                nifti_object = NiftiFile(file_path)

                if not nifti_object:
                    return

                if len(nifti_object.get_dimensions()) not in (3, 4):
                    QMessageBox.critical(self, "Erreur", "Bad file dimension (only 3D/4D)")
                    return
                if len(nifti_object.get_dimensions()) == 4:
                    tmax = nifti_object.get_dimensions()[3]
                    self.time_slider.setMaximum(tmax - 1)
                    self.time_slider.setValue(0)
                    self.time_slider.setVisible(True)
                    self.label_time_slider.setVisible(True)
                else:
                    self.time_slider.setVisible(False)
                    self.label_time_slider.setVisible(False)

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
                self._set_slice_controls_enabled(self.mode_button.currentText().lower()=="slices")

                for tp in tracto_path_list:
                    to = Tractography(tp,
                                      self._current_session.get_uid(),
                                      reference_nifti=nifti_object)
                    self._current_session.add_tract(to)
                    self._viewer.show_tractogram(to)
                    self.add_tracto_checkbox(tp)
                self._current_session.apply()
            except:
                QMessageBox.critical(self, "Erreur", "Error loading volume file")
                return

    def _set_sliders_values(self, dimensions):
        """
        Set the position and maximum values of all anatomical slice controls based on volume
        dimensions.

        Args:
            dimensions (tuple): Shape of the loaded NIfTI data.
        """
        if len(dimensions) > 3:
            dimensions = dimensions[:3]

        self._set_sliders_maximum(dimensions)
        x, y, z = dimensions
        for ori, control in self.slice_controls.items():
            if ori == "Axial":
                control.set_value((z - 1) // 2)
            elif ori == "Coronal":
                control.set_value((y - 1) // 2)
            elif ori == "Sagittal":
                control.set_value((x - 1) // 2)

    def change_slice_opacity(self, value):
        """
        Update slice opacity for the current session and all displayed slices.

        Args:
            value (int): Opacity value from 0 to 100.
        """
        self._current_session.opacity = value / 100.0 # valeur flottante entre 0 et 1
        if self._viewer.working_nifti_obj:
            self._viewer.update_slice_opacity(self._current_session.opacity)

    def reset_cam_zoom(self):
        """
        Reset the viewer's camera zoom to default (100%).
        """
        self.zoom_slider.setValue(100)
        self._viewer.reset_view()

    def take_screenshot(self):
        """
        Save a screenshot of the current viewer display to a PNG file.
        """
        filename, _ = QFileDialog.getSaveFileName(self, "Save screenshot", "", "PNG Files (*.png)")
        if filename:
            try:
                self._viewer.screenshot(filename=filename)
                QMessageBox.information(self, "Screenshot", f"Screenshot saved to: {filename}")
            except Exception as e:
                QMessageBox.information(self, "Screenshot", f"Error saving screenshot: {e}")

    def _on_load_streamlines(self):
        """
        Open a file dialog to load a tractography file (TRK or TCK) into the current session.

        Will create a session if necessary and handle multiple tractographies per session.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Add a tractography file", "",
                                                   "(*.trk *.tck)")
        if file_path:

            if self._current_session is None:
                self._create_session(None, Path(file_path).name)

            key = (self._current_session.get_uid(), file_path)
            if key in self._viewer.tract_actors:
                QMessageBox.information(self,
                                        "Tracto déjà chargé",
                                        f"Le fichier « {Path(file_path).name} » est déjà chargé"
                                        f" dans cette session.")
                return

            try:
                tracto_obj = Tractography(file_path,
                                          self._current_session.get_uid(),
                                          reference_nifti=self._viewer.working_nifti_obj)
            except Exception as e:
                QMessageBox.information(self, "Error loading tractography file", f"{e}")
                return

            if not tracto_obj:
                return

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
        """
        Show statistics report (number and length) for all tractographies in the current session.

        This is aggregated using Session.tract_statistics().
        """
        if not self._current_session or not self._current_session.tracts:
            QMessageBox.information(self,
                                    "Tractography Statistics",
                                    "No tractography data available")
            return

        report_lines = self._current_session.tract_statistics()
        QMessageBox.information(self, "Tractography Statistics", "\n\n".join(report_lines))

    def _create_session(self, volume_obj, filename):
        """
        Create and add a new session, initialize GUI and set as current.

        Args:
            volume_obj (NiftiFile or None): Anatomical NIfTI file for the session.
            filename (str): Display name for the session.
        """
        display_name = f"Session {len(self._sessions) + 1}: " + filename
        session = Session(display_name, volume_obj, self._viewer)
        self._sessions.append(session)
        self.session_selector.addItem(display_name)
        self.session_selector.setCurrentText(display_name)
        self._current_session = session
        self.session_selector.setVisible(True)
        self.rename_button.setVisible(True)

    def switch_session(self, selected_label):
        """
        Switch to a different user session and update the GUI and viewer state.

        Args:
            selected_label (str): Display label of the session to activate.
        """
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
        """
        Save all relevant display and navigation parameters for the current session.

        This includes slice positions, opacity, zoom, background color, and rendering mode.
        """
        if self._current_session and self._current_session.volume_obj:
            for ori, control in self.slice_controls.items():
                self._current_session.slice_positions[ori.lower()] = control.get_value()
            self._current_session.opacity = self._opacity_slider.value() / 100.0
            self._current_session.zoom_factor = self.zoom_slider.value() / 100.0
            self._current_session.background_color = self._viewer.background_color.name
            self._current_session.rendering_mode = self.mode_button.currentText()

    def on_mode_changed(self, mode):
        """
        Callback for when the user changes the rendering mode ("Slices", "Volume 3D").

        Args:
            mode (str): The new rendering mode selected by the user.
        """
        self._viewer.render_mode(mode)
        self._set_slice_controls_enabled(mode.lower() == "slices")
        if self._current_session.volume_obj:
            self._set_sliders_values(self._current_session.volume_obj.get_dimensions())

    def _set_sliders_maximum(self, dimensions):
        """
        Set the maximum allowed value for all anatomical slice controls, based on data dimensions.

        Args:
            dimensions (tuple): Shape of the loaded volume.
        """
        if len(dimensions) == 3:
            x, y, z = dimensions
        elif len(dimensions) == 4:
            x, y, z, t = dimensions
            self.time_slider.setMaximum(t - 1)
            self.time_slider.setValue(0)
            self.time_slider.setVisible(True)
            self.label_time_slider.setVisible(True)
        else:
            raise ValueError("Volume must be 3D or 4D.")

        for ori, control in self.slice_controls.items():
            if ori == "Axial":
                control.set_max(z - 1)
            elif ori == "Coronal":
                control.set_max(y - 1)
            elif ori == "Sagittal":
                control.set_max(x - 1)


    def rename_current_session(self):
        """
        Rename the current session with the name entered in the rename_lineedit.
        Updates the session selector and all associated tractography checkboxes.
        """
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
        """
        Add a checkbox to toggle visibility of a loaded tractography file in the current session.

        Args:
            file_path (str): Path to the tractography file.
        """
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
        """
        Enable or disable all slice controls and opacity slider.

        Args:
            enabled (bool): If True, controls are enabled; otherwise, disabled.
        """
        for control in self.slice_controls.values():
            control.slider.setEnabled(enabled)
            control.line_edit.setEnabled(enabled)
        self._opacity_slider.setEnabled(enabled)

    def change_slices_position(self, value, orientation):
        """
        Callback to change the slice position in the viewer for a given orientation.

        Args:
            value (int): New position value.
            orientation (str): Slice orientation ("Axial", "Coronal", "Sagittal").
        """
        if self._viewer.working_nifti_obj:
            if orientation.lower() == "sagittal":
                control = self.slice_controls[orientation]
                value = control.get_max() - int(value)
            self._viewer.schedule_slice_update(orientation.lower(),
                                               value,
                                               self._current_session.opacity)

    def _init_converter_tab(self):
        """
        Initialize the converter tab for file format conversion.
        """
        self._converter_tab = QWidget()
        self._tabs.addTab(self._converter_tab, "Converter")
        self._build_converter_tab()

    def _build_converter_tab(self):
        """
        Build and layout all controls of the converter tab
        (input, reference, output, format selection).
        """
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
        """
        Open a file dialog to select the input file for conversion.
        Updates the input_edit field and available output formats.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "", "All Files (*)")
        if not path: return
        self.input_edit.setText(path)
        ext = ''.join(Path(path).suffixes).lower().lstrip('.')
        combos = [o for (i, o) in Converter._CONVERTERS if i == ext]
        self.out_combo.clear()
        self.out_combo.addItems(combos)

    def _browse_reference(self):
        """
        Open a file dialog to select an anatomical reference file for conversion.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Choose an anatomical reference", "",
                                              "(*.nii *.nii.gz)")
        if path:
            self.ref_edit.setText(path)

    def _browse_output(self):
        """
        Open a file dialog to specify the output path and filename for the converted file.
        """
        path, _ = QFileDialog.getSaveFileName(self, "Save as", "",
                                              f"*.{self.out_combo.currentText()}")
        if path:
            self.output_edit.setText(path)

    def _on_convert(self):
        """
        Perform the conversion using the selected input, output, and optional reference file.
        Shows a message box indicating success or failure.
        """
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