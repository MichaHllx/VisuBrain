"""
visubrain/gui/viewer.py

Main module for anatomical and tractography visualization in the VisuBrain application.

This module provides the PyVistaViewer class, a 2D/3D visualization widget
for displaying medical imaging data (NIfTI volumes) and tractography files (TRK, TCK).
Integrates with the VisuBrain application, offering interactive controls for rendering modes,
slice navigation, opacity, zoom, tractogram display and session-based workflows.

Classes:
    PyVistaViewer: Main visualization widget for NIfTI volumes and tractography.
"""



import pyvista as pv
import numpy as np

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox
from pyvistaqt import QtInteractor


def _slice_actor_key(file_path: str, axis: str) -> str:
    """
    Generate a unique key for a 2D slice actor based on the file path and axis.

    Args:
        file_path (str): Path to the NIfTI file being visualized.
        axis (str): Slice orientation ("axial", "coronal", "sagittal").

    Returns:
        str: Unique key for accessing slice actors in the viewer.
    """
    return f"{file_path}::{axis}_slice"


class PyVistaViewer(QtInteractor):
    """
    3D and slice viewer for medical imaging and tractography, integrated with the VisuBrain
     application.

    This widget is responsible for visualizing anatomical data (NIfTI volumes, 3D or multi-slice)
     and tractography
    (streamlines from TRK/TCK/FBR files), and is aware of the VisuBrain data structures (NiftiFile,
     Tractography, Session).

    Attributes:
        pv_data (pyvista.DataSet): Wrapped image data for visualization.
        volume_sliced_actor (dict): PyVista actors for 2D slices, keyed by slice orientation.
        volume_3d_actor: PyVista actor for the 3D volumetric rendering.
        working_nifti_obj (NiftiFile): Currently visualized anatomical volume.
        tract_actors (dict): Displayed tractography actors, keyed by (session_id, file_path).
        align_streamlines (bool): (Reserved) Enable streamline alignment in display.
        slice_update_timer (QTimer): Timer for debouncing slice updates.
        pending_update: Temporary storage for scheduled slice updates.
        current_zoom_factor (float): Current camera zoom applied to the view.
        current_mode (str): Visualization mode ("slices" or "volume 3d").
    """

    def __init__(self, parent=None):
        """
        Initialize the 3D viewer, configure state and connect controls.

        Args:
            parent: Optional parent widget (for Qt integration).
        """
        super().__init__(parent)
        self.pv_data = None
        self.volume_sliced_actor = {}
        self.volume_3d_actor = None
        self.working_nifti_obj = None
        self.tract_actors = {}
        self.align_streamlines = False
        self.slice_update_timer = QTimer()
        self.slice_update_timer.setSingleShot(True)
        self.slice_update_timer.timeout.connect(self.perform_slice_update)
        self.pending_update = None
        self.current_zoom_factor = 1.0
        self.current_mode = "slices"
        self.add_axes()
        self.show()

    def set_working_nifti_obj(self, nifti_obj):
        """
        Set and display a new anatomical reference (NiftiFile), and reset all previous visual state.

        Args:
            nifti_obj (NiftiFile): Instance of NiftiFile to visualize.
        """
        self.working_nifti_obj = nifti_obj
        if hasattr(nifti_obj, "is_4d") and nifti_obj.is_4d():
            # Use first time frame for 4D images
            self.pv_data = pv.wrap(nifti_obj.get_3d_frame(0))
        else:
            self.pv_data = pv.wrap(nifti_obj.data)
        self.clear_previous_actors()
        self.render_mode(self.current_mode)

    def set_time_frame(self, t):
        """
        Update displayed data for a specific time/frame index in a 4D NIfTI.

        Args:
            t (int): Index of the time/frame to display.
        """
        if hasattr(self.working_nifti_obj, "is_4d") and self.working_nifti_obj.is_4d():
            frame_3d = self.working_nifti_obj.get_3d_frame(t)
            self.pv_data = pv.wrap(frame_3d)
            self.clear_previous_actors()
            self.render_mode(self.current_mode)

    def schedule_slice_update(self, axis, value, opacity):
        """
        Schedule a slice position update for smoother user experience (debouncing).

        Args:
            axis (str): Orientation of the slice ("axial", "coronal", "sagittal").
            value (float): Position of the slice.
            opacity (float): Opacity to set for the updated slice.
        """
        self.pending_update = (axis, value, opacity)
        if self.slice_update_timer.isActive():
            self.slice_update_timer.stop()
        self.slice_update_timer.start(5)

    def perform_slice_update(self):
        """
        Perform the pending update for slice position, if scheduled.
        """
        if self.pending_update:
            axis, value, opacity = self.pending_update
            self.update_slice_position(axis, value, opacity)
            self.pending_update = None

    def render_mode(self, mode: str, opacity=0.5) -> bool:
        """
        Display the anatomical data in either 'slices' (2D orthogonal views) or 'volume 3d'
         (3D rendering) mode.

        Args:
            mode (str): "slices" or "volume 3d".
            opacity (float): Slice opacity (used only in 'slices' mode).

        Returns:
            bool: True if the mode was successfully set, False otherwise.
        """
        if self.working_nifti_obj is None:
            return False

        shape = self.working_nifti_obj.get_dimensions()
        if len(shape) == 3:
            x, y, z = shape
        elif len(shape) == 4:
            x, y, z, _ = shape
        else:
            raise ValueError("Data must be 3D or 4D")

        mode_lower = mode.lower()
        self.current_mode = mode_lower
        if mode_lower == "slices":
            if not self.volume_sliced_actor:
                self._create_slice_actor([0, 0, 1], [0, 0, z // 2], "axial", opacity=opacity)
                self._create_slice_actor([0, 1, 0], [0, y // 2, 0], "coronal", opacity=opacity)
                self._create_slice_actor([1, 0, 0], [x // 2, 0, 0], "sagittal", opacity=opacity)
            else:
                self.update_slice_opacity(opacity)
            for actor in self.volume_sliced_actor.values():
                actor.SetVisibility(True)
            if self.volume_3d_actor:
                self.volume_3d_actor.SetVisibility(False)

        elif mode_lower == "volume 3d":
            if self.volume_3d_actor is None:
                self.volume_3d_actor = self._create_volume_actor()
            self.volume_3d_actor.SetVisibility(True)
            for actor in self.volume_sliced_actor.values():
                actor.SetVisibility(False)
        else:
            QMessageBox.warning(self, "Rendering Mode", f"Unsupported mode: {mode}")
            return False

        self.render()
        return True

    def clear_previous_actors(self):
        """
        Remove all actors currently displayed in the scene (slices, 3D volume, tractographies).
        """
        if self.volume_3d_actor:
            self.remove_actor(self.volume_3d_actor)
            self.volume_3d_actor = None

        for actor in self.volume_sliced_actor.values():
            self.remove_actor(actor)
        self.volume_sliced_actor.clear()

        for actor in self.tract_actors.values():
            self.remove_actor(actor)
        self.tract_actors.clear()

        self.render()

    def hide_all_actors(self):
        """
        Hide all visual actors in the viewer, without deleting them from memory.
        """
        if self.volume_3d_actor:
            self.volume_3d_actor.SetVisibility(False)

        for actor in self.volume_sliced_actor.values():
            actor.SetVisibility(False)

        for actor in self.tract_actors.values():
            actor.SetVisibility(False)

        self.render()

    def _create_slice_actor(self, normal, origin, axis: str, update_if_exists=False, opacity=0.5):
        """
        Create or update a 2D slice actor for an anatomical volume in the viewer.

        Args:
            normal (list): Normal vector of the slice plane (world space).
            origin (list): Origin of the slice (voxel index).
            axis (str): Orientation name ("axial", "coronal", "sagittal").
            update_if_exists (bool): If True, update the slice if it already exists.
            opacity (float): Opacity value for the slice.

        Returns:
            PyVista actor: Actor representing the 2D slice.
        """
        if self.pv_data is None:
            return None

        new_slice = self.pv_data.slice(normal=normal, origin=origin)
        key = _slice_actor_key(self.working_nifti_obj.file_path, axis)

        if update_if_exists and key in self.volume_sliced_actor:
            actor = self.volume_sliced_actor[key]
            actor.mapper.SetInputData(new_slice)
            actor.mapper.Update()
            actor.GetProperty().SetOpacity(opacity)
        else:
            actor = self.add_mesh(new_slice, opacity=opacity, cmap='gray', show_scalar_bar=False)
            self.volume_sliced_actor[key] = actor

        return actor

    def _create_volume_actor(self):
        """
        Create a 3D volume rendering actor for the currently loaded NIfTI data.

        Returns:
            PyVista actor: Actor for 3D volume rendering.
        """
        return self.add_volume(
            self.pv_data,
            opacity=[0.0,0.045],
            cmap="gray",
            shade=True,
            show_scalar_bar=False
        )

    def show_tractogram(self, tracto_obj, show_points=False):
        """
        Display a Tractography object (bundle of streamlines) in the 3D viewer.

        Args:
            tracto_obj (Tractography): Tractography object containing streamlines.
            show_points (bool): If True, displays as points instead of lines/tubes.

        Returns:
            bool: True if displayed, False otherwise.
        """
        if tracto_obj is None:
            return False

        sid = tracto_obj.session_id
        key = (sid, tracto_obj.file_path)
        if key not in self.tract_actors:
            points_list, colors_list, connectivity = tracto_obj.get_color_points(show_points)
            points = np.vstack(points_list)
            colors = np.vstack(colors_list)
            poly = pv.PolyData(points)
            poly["Colors"] = colors

            if not show_points:
                connectivity_flat = np.hstack(connectivity)
                poly.lines = connectivity_flat
                point_size = 0
                ambient = 0.3
            else:
                point_size = 2
                ambient = 0

            actor = self.add_mesh(
                poly,
                scalars="Colors",
                rgb=True,
                render_lines_as_tubes=not show_points,
                line_width=2,
                point_size=point_size,
                ambient=ambient
            )
            self.tract_actors[key] = actor

        self.tract_actors[key].SetVisibility(True)
        self.render()
        return True

    def set_file_visibility(self, file_path, visible, session_id):
        """
        Show or hide a specific tractography actor by file path and session.

        Args:
            file_path (str): Path to the tractography file (TRK/TCK/FBR).
            visible (bool): Whether the actor should be visible.
            session_id (int): Identifier for the session in which the tract is loaded.
        """
        key = (session_id, file_path)
        actor = self.tract_actors.get(key)
        if actor:
            actor.SetVisibility(visible)
            self.render()

    def update_slice_position(self, axis, value, opacity=0.5):
        """
        Change the position of a displayed anatomical slice.

        Args:
            axis (str): Orientation of the slice ("axial", "coronal", "sagittal").
            value (float): New position for the slice (voxel index).
            opacity (float): Opacity value for the slice.
        """
        if self.working_nifti_obj is None:
            return

        if self.current_mode != "slices":
            return

        if axis == "axial":
            normal = [0, 0, 1]
            origin = [0, 0, int(value)]
        elif axis == "coronal":
            normal = [0, 1, 0]
            origin = [0, int(value), 0]
        elif axis == "sagittal":
            normal = [1, 0, 0]
            origin = [int(value), 0, 0]
        else:
            return

        self._create_slice_actor(normal, origin, axis, update_if_exists=True, opacity=opacity)
        self.render()

    def update_slice_opacity(self, opacity: float):
        """
        Set the opacity of all visible 2D slice actors.

        Args:
            opacity (float): New opacity value to apply.
        """
        for actor in self.volume_sliced_actor.values():
            if actor:
                actor.GetProperty().SetOpacity(opacity)
        self.render()

    def set_zoom(self, zoom_factor):
        """
        Change the camera zoom factor in the viewer.

        Args:
            zoom_factor (float): Zoom percentage (100 = default, >100 = zoom in).
        """
        new_zoom_factor = zoom_factor / 100.0
        relative_factor = new_zoom_factor / self.current_zoom_factor
        self.camera.Zoom(relative_factor)
        self.current_zoom_factor = new_zoom_factor
        self.render()

    def change_background(self, color):
        """
        Change the background color of the PyVista scene.

        Args:
            color (str): Background color (e.g., "white", "black", "#RRGGBB").
        """
        normalized_color = color.lower()
        try:
            self.set_background(normalized_color)
        except AttributeError:
            return
        self.render()

    def reset_view(self):
        """
        Reset the camera to isometric view and default zoom.
        """
        self.view_isometric()
        self.reset_camera()
        self.current_zoom_factor = 1.0
        self.render()
