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

        self.add_axes()
        self.show()

    def set_working_nifti_obj(self, working_nifti_obj):
        self.working_nifti_obj = working_nifti_obj

    def schedule_slice_update(self, axis, value, opacity):
        self.pending_update = (axis, value, opacity)
        self.slice_update_timer.start(50)  # en ms

    def perform_slice_update(self):
        if self.pending_update:
            axis, value, opacity = self.pending_update
            self.update_slice_position(axis, value, opacity)
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

    def show_tractogram(self, tracto_obj):
        streamlines = tracto_obj.get_streamlines()
        try:
            points = np.vstack([s for s in streamlines])
        except Exception:
            points = np.array([])

        if points.size == 0:
            QMessageBox.warning(self, "Erreur", "No tractography data to display.")
            return

        poly = pv.PolyData(points)
        self.tract_actors[tracto_obj.file_path] = self.add_mesh(poly)
        self.render()
        return True

    def set_file_visibility(self, file_path, visible):
        for axis in ["axial", "coronal", "sagittal"]:
            key = file_path + axis + "_slice"
            if key in self.nifti_slice_actors:
                self.nifti_slice_actors[key].SetVisibility(visible)
        if file_path in self.tract_actors:
            self.tract_actors[file_path].SetVisibility(visible)
        self.render()
        self.reset_camera()

    def update_slice_position(self, axis, value, opacity=0.5):
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

        volume = pv.wrap(self.working_nifti_obj.data)
        new_slice = volume.slice(normal=normal, origin=origin)
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

