# visubrain/gui/viewer.py
from typing import Dict

import pyvista as pv
import numpy as np

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox
from pyvistaqt import QtInteractor
from vtkmodules.vtkRenderingCore import vtkActor


def _slice_actor_key(file_path: str, axis: str) -> str:
    return f"{file_path}::{axis}_slice"


class PyVistaViewer(QtInteractor):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.pv_data = None

        self.volume_sliced_actor = {}
        self.volume_3d_actor = None
        self.working_nifti_obj = None

        self.tract_actors: Dict[tuple[int,str], vtkActor] = {}
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
        self.pv_data = pv.wrap(nifti_obj.data)
        self.working_nifti_obj = nifti_obj
        self.reset_view()

    def schedule_slice_update(self, axis, value, opacity):
        self.pending_update = (axis, value, opacity)
        if self.slice_update_timer.isActive():
            self.slice_update_timer.stop()
        self.slice_update_timer.start(5)

    def perform_slice_update(self):
        if self.pending_update:
            axis, value, opacity = self.pending_update
            self.update_slice_position(axis, value, opacity)
            self.pending_update = None

    def render_mode(self, mode: str, opacity=0.5) -> bool:
        if self.working_nifti_obj is None:
            return False

        shape = self.working_nifti_obj.get_dimensions()
        if len(shape) != 3:
            QMessageBox.critical(self, "Erreur", "Bad file dimension (only 3D)")
            return False

        mode_lower = mode.lower()
        self.current_mode = mode_lower
        if mode_lower == "slices":
            if not self.volume_sliced_actor:
                x, y, z = shape
                self._create_slice_actor([0, 0, 1], [0, 0, z // 2], "axial", opacity=opacity)
                self._create_slice_actor([0, 1, 0], [0, y // 2, 0], "coronal", opacity=opacity)
                self._create_slice_actor([1, 0, 0], [x // 2, 0, 0], "sagittal", opacity=opacity)
            else:
                self.update_slice_opacity(opacity)
            for actor in self.volume_sliced_actor.values():
                actor.SetVisibility(True)
            if self.volume_3d_actor:
                self.volume_3d_actor.SetVisibility(False)
            for actor in self.tract_actors.values():
                actor.SetVisibility(False)

        elif mode_lower == "volume 3d":
            if self.volume_3d_actor is None:
                self.volume_3d_actor = self._create_volume_actor()
            self.volume_3d_actor.SetVisibility(True)
            for actor in self.volume_sliced_actor.values():
                actor.SetVisibility(False)
            for actor in self.tract_actors.values():
                actor.SetVisibility(False)

        else:
            QMessageBox.warning(self, "Rendering Mode", f"Unsupported mode: {mode}")
            return False

        self.render()
        return True

    def clear_previous_actors(self):
        if self.volume_3d_actor:
            self.remove_actor(self.volume_3d_actor)
            self.volume_3d_actor = None

        for actor in self.volume_sliced_actor.values(): self.remove_actor(actor)
        self.volume_sliced_actor.clear()

        for actor in self.tract_actors.values(): self.remove_actor(actor)
        self.tract_actors.clear()

        self.render()

    def hide_all_actors(self):
        if self.volume_3d_actor:
            self.volume_3d_actor.SetVisibility(False)

        for actor in self.volume_sliced_actor.values():
            actor.SetVisibility(False)

        for actor in self.tract_actors.values():
            actor.SetVisibility(False)

        self.render()

    def _create_slice_actor(self, normal, origin, axis: str, update_if_exists=False, opacity=0.5):
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
        return self.add_volume(
            self.pv_data,
            opacity=[0.0,0.045],
            cmap="gray",
            shade=True,
            show_scalar_bar=False
        )

    def show_tractogram(self, tracto_obj, show_points=False):
        if tracto_obj is None:
            return

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

            actor = self.add_mesh(poly,
                                  scalars="Colors",
                                  rgb=True,
                                  render_lines_as_tubes=not show_points,
                                  line_width=2,
                                  point_size=point_size,
                                  ambient=ambient)
            self.tract_actors[key] = actor

        self.tract_actors[key].SetVisibility(True)
        self.render()
        return True

    def set_file_visibility(self, file_path, visible, session_id):
        key = (session_id, file_path)
        actor = self.tract_actors.get(key)
        if actor:
            actor.SetVisibility(visible)
            self.render()

    def update_slice_position(self, axis, value, opacity=0.5):
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
        for actor in self.volume_sliced_actor.values():
            if actor: actor.GetProperty().SetOpacity(opacity)
        self.render()

    def set_zoom(self, zoom_factor):
        # 100 correspond à 1.0, donc il faut div par 100
        new_zoom_factor = zoom_factor / 100.0
        relative_factor = new_zoom_factor / self.current_zoom_factor
        self.camera.Zoom(relative_factor)
        self.current_zoom_factor = new_zoom_factor
        self.render()

    def change_background(self, color):
        normalized_color = color.lower()
        try:
            self.set_background(normalized_color)
        except AttributeError:
            return
        self.render()

    def reset_view(self):
        self.view_isometric()
        self.reset_camera()
        self.current_zoom_factor = 1.0
        self.render()
