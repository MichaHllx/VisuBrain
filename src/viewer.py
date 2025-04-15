import pyvista as pv
import numpy as np

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox
from pyvistaqt import QtInteractor


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

        self.add_axes()
        self.show()

    def set_working_nifti_obj(self, nifti_obj):
        self.working_nifti_obj = nifti_obj

    def schedule_slice_update(self, axis, value, opacity):
        self.pending_update = (axis, value, opacity)
        self.slice_update_timer.start(50)  # en ms

    def perform_slice_update(self):
        if self.pending_update:
            axis, value, opacity = self.pending_update
            self.update_slices(axis, value, opacity)
            self.pending_update = None

    def show_nifti_slices(self):
        data = self.working_nifti_obj.data
        shape = self.working_nifti_obj.get_dimensions()

        if len(shape) != 3:
            QMessageBox.critical(self, "Erreur", "Bad file dimension")
            return

        self.slices_actor = pv.wrap(data)

        if self.volume_actor is not None:
            self.remove_actor(self.volume_actor)
            self.volume_actor = None
        for slice_actor in self.nifti_slice_actors.values():
            if slice_actor is not None:
                self.remove_actor(slice_actor)
        self.nifti_slice_actors = {}

        x, y, z = shape
        slice_axial = self.slices_actor.slice(normal=[0, 0, 1], origin=[0, 0, z // 2])
        slice_coronal = self.slices_actor.slice(normal=[0, 1, 0], origin=[0, y // 2, 0])
        slice_sagittal = self.slices_actor.slice(normal=[1, 0, 0], origin=[x // 2, 0, 0])

        self.nifti_slice_actors[self.working_nifti_obj.file_path + "axial_slice"] = (
            self.add_mesh(slice_axial, opacity=0.5, cmap='gray', show_scalar_bar=False)
        )
        self.nifti_slice_actors[self.working_nifti_obj.file_path + "coronal_slice"] = (
            self.add_mesh(slice_coronal, opacity=0.5, cmap='gray', show_scalar_bar=False)
        )
        self.nifti_slice_actors[self.working_nifti_obj.file_path + "sagittal_slice"] = (
            self.add_mesh(slice_sagittal, opacity=0.5, cmap='gray', show_scalar_bar=False)
        )
        self.render()
        return True

    def show_nifti_volume(self):
        data = self.working_nifti_obj.data
        shape = self.working_nifti_obj.get_dimensions()

        if len(shape) != 3:
            QMessageBox.critical(self, "Erreur", "Bad file dimension")
            return False

        if self.volume_actor is not None:
            self.remove_actor(self.volume_actor)
            self.volume_actor = None
        for slice_actor in self.nifti_slice_actors.values():
            if slice_actor is not None:
                self.remove_actor(slice_actor)
        self.nifti_slice_actors = {}

        self.volume_actor = self.add_volume(pv.wrap(data), opacity="sigmoid", cmap="gray", shade=True,
                                            show_scalar_bar=False)
        self.render()
        return True

    def show_tractogram(self, tracto_obj, show_points=False):
        """
          - Red = axe X
          - Green = axe Y
          - Blue = axe Z
        """
        streamlines = tracto_obj.get_streamlines()

        if len(streamlines) == 0:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Erreur", "No tractography data to display.")
            return

        points_list = []
        colors_list = []
        connectivity = []  # (pour l'affichage des lignes)
        offset = 0

        for streamline in streamlines:
            streamline = np.asarray(streamline)
            n_points = streamline.shape[0]

            if n_points < 2:
                colors = np.tile(np.array([255, 255, 255], dtype=np.uint8), (n_points, 1))
            else:
                diffs = np.diff(streamline, axis=0) # calcul tangente de chaque point (dérivée)
                print(diffs)
                diffs = np.vstack([diffs, diffs[-1]]) # répéter dernière pour garder la mm size
                norms = np.linalg.norm(diffs, axis=1, keepdims=True) # normalise le vecteur (size=1)
                norms[norms == 0] = 1.0
                tangents = diffs / norms
                colors = (np.abs(tangents) * 255).astype(np.uint8)

            points_list.append(streamline)
            colors_list.append(colors)

            # construction de la connectivité pour cette streamline
            if not show_points:
                cell = np.hstack(([n_points], np.arange(offset, offset + n_points)))
                connectivity.append(cell)

            offset += n_points

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
                key = file_path + axis + "_slice"
                if key in self.nifti_slice_actors:
                    self.nifti_slice_actors[key].SetVisibility(visible)
        self.render()

    def update_slices(self, axis, value, opacity=0.5):
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

        #volume = pv.wrap(self.working_nifti_obj.data)
        new_slice = self.slices_actor.slice(normal=normal, origin=origin)

        key = self.working_nifti_obj.file_path + axis + "_slice"
        if key in self.nifti_slice_actors:
            # màj acteur existant
            actor = self.nifti_slice_actors[key]
            actor.mapper.SetInputData(new_slice)
            actor.mapper.Update()
            actor.GetProperty().SetOpacity(opacity)
        else:
            self.nifti_slice_actors[key] = self.add_mesh(new_slice, opacity=opacity, cmap='gray', show_scalar_bar=False)
        self.render()

    def set_zoom(self, new_zoom_factor):
        relative_factor = new_zoom_factor / self.current_zoom_factor
        self.camera.Zoom(relative_factor)
        self.current_zoom_factor = new_zoom_factor
        self.render()

    def reset_view(self):
        self.reset_camera(self.working_nifti_obj)
        self.render()
