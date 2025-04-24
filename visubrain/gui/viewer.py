import pyvista as pv
import numpy as np

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox
from pyvistaqt import QtInteractor


def _slice_actor_key(file_path: str, axis: str) -> str:
    return f"{file_path}::{axis}_slice"


class PyVistaViewer(QtInteractor):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nifti_slice_actors = {}
        self.tract_actors = {}
        self.slices_actor = None
        self.volume_actor = None

        self.working_nifti_obj = None

        self.slice_update_timer = QTimer()
        self.slice_update_timer.setSingleShot(True)
        self.slice_update_timer.timeout.connect(self.perform_slice_update)
        self.pending_update = None

        self.current_zoom_factor = 1.0
        self.current_mode = "Slices"

        self.add_axes()
        self.show()

    def set_working_nifti_obj(self, nifti_obj):
        self.working_nifti_obj = nifti_obj
        self.reset_view()

    def schedule_slice_update(self, axis, value, opacity):
        self.pending_update = (axis, value, opacity)
        self.slice_update_timer.start(50)  # en ms

    def perform_slice_update(self):
        if self.pending_update:
            axis, value, opacity = self.pending_update
            self.update_slices(axis, value, opacity)
            self.pending_update = None

    # def show_nifti_slices(self):
    #     if self.working_nifti_obj is None:
    #         return False
    #     self.current_mode = "Slices"
    #
    #     data = self.working_nifti_obj.data
    #     shape = self.working_nifti_obj.get_dimensions()
    #
    #     if len(shape) != 3:
    #         QMessageBox.critical(self, "Erreur", "Bad file dimension")
    #         return False
    #
    #     self.slices_actor = pv.wrap(data)
    #     self._clear_previous_actors()
    #
    #     x, y, z = shape
    #     self._create_slice_actor([0, 0, 1], [0, 0, z // 2], "axial", update_if_exists=False, opacity=0.5)
    #     self._create_slice_actor([0, 1, 0], [0, y // 2, 0], "coronal", update_if_exists=False, opacity=0.5)
    #     self._create_slice_actor([1, 0, 0], [x // 2, 0, 0], "sagittal", update_if_exists=False, opacity=0.5)
    #
    #     self.render()
    #     return True

    def render_mode(self, mode: str) -> bool:
        if self.working_nifti_obj is None:
            return False

        data = self.working_nifti_obj.data
        shape = self.working_nifti_obj.get_dimensions()

        if len(shape) != 3:
            QMessageBox.critical(self, "Erreur", "Bad file dimension")
            return False

        self._clear_previous_actors()

        if mode.lower() == "slices":
            self.current_mode = "Slices"
            self.slices_actor = pv.wrap(data)

            x, y, z = shape
            self._create_slice_actor([0, 0, 1], [0, 0, z // 2], "axial", update_if_exists=False, opacity=0.5)
            self._create_slice_actor([0, 1, 0], [0, y // 2, 0], "coronal", update_if_exists=False, opacity=0.5)
            self._create_slice_actor([1, 0, 0], [x // 2, 0, 0], "sagittal", update_if_exists=False, opacity=0.5)

        elif mode.lower() == "volume 3d":
            self.current_mode = "Volume 3D"
            self.volume_actor = self._create_volume_actor(data)
        else:
            QMessageBox.warning(self, "Rendering Mode", f"Unsupported mode: {mode}")
            return False

        self.render()
        return True

    def _clear_previous_actors(self):
        if self.volume_actor:
            self.remove_actor(self.volume_actor)
            self.volume_actor = None
        for actor in self.nifti_slice_actors.values():
            if actor:
                self.remove_actor(actor)
        self.nifti_slice_actors.clear()

    def _create_slice_actor(self, normal, origin, axis: str, update_if_exists=False, opacity=0.5):
        if self.slices_actor is None:
            return None

        new_slice = self.slices_actor.slice(normal=normal, origin=origin)
        key = _slice_actor_key(self.working_nifti_obj.file_path, axis)

        if update_if_exists and key in self.nifti_slice_actors:
            actor = self.nifti_slice_actors[key]
            actor.mapper.SetInputData(new_slice)
            actor.mapper.Update()
            actor.GetProperty().SetOpacity(opacity)
        else:
            actor = self.add_mesh(new_slice, opacity=opacity, cmap='gray', show_scalar_bar=False)
            self.nifti_slice_actors[key] = actor

        return actor

    # def show_nifti_volume(self):
    #     if self.working_nifti_obj is None:
    #         return False
    #
    #     self.current_mode = "Volume 3D"
    #     data = self.working_nifti_obj.data
    #     shape = self.working_nifti_obj.get_dimensions()
    #
    #     if len(shape) != 3:
    #         QMessageBox.critical(self, "Erreur", "Bad file dimension")
    #         return False
    #
    #     self._clear_previous_actors()
    #     self.volume_actor = self._create_volume_actor(data)
    #     self.render()
    #     return True

    def _create_volume_actor(self, data):
        return self.add_volume(
            pv.wrap(data),
            opacity="sigmoid",
            cmap="gray",
            shade=True,
            show_scalar_bar=False
        )

    def show_tractogram(self, tracto_obj, show_points=False):
        if tracto_obj is None:
            return

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

        self.tract_actors[tracto_obj.file_path] = actor
        self.render()
        return True

    def set_file_visibility(self, file_path, visible):
        if file_path in self.tract_actors:
            self.tract_actors[file_path].SetVisibility(visible)
        else:
            for axis in ["axial", "coronal", "sagittal"]:
                key = _slice_actor_key(file_path, axis)
                if key in self.nifti_slice_actors:
                    self.nifti_slice_actors[key].SetVisibility(visible)
        self.render()

    def update_slices(self, axis, value, opacity=0.5):
        if self.working_nifti_obj is None:
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

    def clear(self):
        if self.volume_actor:
            self.remove_actor(self.volume_actor)
            self.volume_actor = None
        for actor in self.nifti_slice_actors.values(): self.remove_actor(actor)
        for actor in self.tract_actors.values(): self.remove_actor(actor)

        self.nifti_slice_actors.clear()
        self.tract_actors.clear()
        self.render()
