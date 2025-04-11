# import pyvista as pv
# from pyvistaqt import QtInteractor
# import numpy as np
# from PyQt6.QtWidgets import QMessageBox
#
#
# class PyVistaViewer(QtInteractor):
#
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.nifti_slice_actors = {}
#         self.tract_actors = {}
#         self.volume_data = {}
#         self.plotter = self
#         self.add_axes()
#         self.show()
#
#     def show_nifti(self, file_path, data):
#
#         if data.ndim != 3:
#             QMessageBox.critical(self, "Error", "The file dimensions are incompatible.")
#             return
#
#         self.volume_data[file_path] = data.shape
#         volume = pv.wrap(data)
#         x, y, z = data.shape
#
#         slice_axial = volume.slice(normal=[0, 0, 1], origin=[0, 0, z//2]) # -> inferior to superior du sujet
#         slice_coronal = volume.slice(normal=[0, 1, 0], origin=[0, y//2, 0]) # -> posterior to anterior du sujet
#         slice_sagittal = volume.slice(normal=[1, 0, 0], origin=[x//2, 0, 0]) # -> left to right du sujet
#
#         self.nifti_slice_actors[file_path + "axial_slice"] = self.add_mesh(slice_axial,
#                                                                      opacity=0.5,
#                                                                      cmap='gray',
#                                                                      show_scalar_bar=False)
#         self.nifti_slice_actors[file_path + "coronal_slice"] = self.add_mesh(slice_coronal,
#                                                                        opacity=0.5,
#                                                                        cmap='gray',
#                                                                        show_scalar_bar=False)
#         self.nifti_slice_actors[file_path + "sagittal_slice"] = self.add_mesh(slice_sagittal,
#                                                                         opacity=0.5,
#                                                                         cmap='gray',
#                                                                         show_scalar_bar=False)
#         self.render()
#
#     def show_tractogram(self, file_path, streamlines, trk):
#         points = np.vstack([s for s in streamlines])
#         poly = pv.PolyData(points)
#
#         self.tract_actors[file_path] = self.add_mesh(poly)
#         self.render()
#
#     def set_file_visibility(self, file_path, visible):
#         for axis in ["axial", "coronal", "sagittal"]:
#             key = file_path + axis + "_slice"
#             if key in self.nifti_slice_actors:
#                 self.nifti_slice_actors[key].SetVisibility(visible)
#         if file_path in self.tract_actors:
#             self.tract_actors[file_path].SetVisibility(visible)
#         self.render()
#
#     def update_slice_position(self, axis, value, data):
#         for file_path, dimensions in self.volume_data.items():
#             if axis == "axial":
#                 slice_idx = int(value)
#                 normal = [0, 0, 1]
#                 origin = [0, 0, slice_idx]
#             elif axis == "coronal":
#                 slice_idx = int(value)
#                 normal = [0, 1, 0]
#                 origin = [0, slice_idx, 0]
#             elif axis == "sagittal":
#                 slice_idx = int(value)
#                 normal = [1, 0, 0]
#                 origin = [slice_idx, 0, 0]
#             else:
#                 return
#
#             volume = pv.wrap(data)
#             sliced = volume.slice(normal=normal, origin=origin)
#
#             self.nifti_slice_actors[file_path + axis + "_slice"].SetVisibility(False)
#             self.nifti_slice_actors[file_path + axis + "_slice"] = self.add_mesh(sliced,
#                                                                            opacity=0.5,
#                                                                            cmap='gray',
#                                                                            show_scalar_bar=False)
#         self.render()

import pyvista as pv
from PyQt6.QtCore import QTimer
from pyvistaqt import QtInteractor
import numpy as np
from PyQt6.QtWidgets import QMessageBox

class PyVistaViewer(QtInteractor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nifti_slice_actors = {}
        self.tract_actors = {}
        self.volume_obj = None

        self.slice_update_timer = QTimer()
        self.slice_update_timer.setSingleShot(True)
        self.slice_update_timer.timeout.connect(self.perform_slice_update)
        self.pending_update = None

        self.add_axes()
        self.show()

    def schedule_slice_update(self, axis, value, nifti_obj):
        self.pending_update = (axis, value, nifti_obj)
        self.slice_update_timer.start(50)  # en ms

    def perform_slice_update(self):
        if self.pending_update:
            axis, value, nifti_obj = self.pending_update
            self.update_slice_position(axis, value, nifti_obj)
            self.pending_update = None

    def show_nifti(self, nifti_obj):
        data = nifti_obj.data
        shape = nifti_obj.get_dimensions()

        if len(shape) != 3:
            QMessageBox.critical(self, "Erreur", "Bad file dimension")
            return

        self.volume_obj = pv.wrap(data)

        x, y, z = shape
        slice_axial = self.volume_obj.slice(normal=[0, 0, 1], origin=[0, 0, z//2])
        slice_coronal = self.volume_obj.slice(normal=[0, 1, 0], origin=[0, y//2, 0])
        slice_sagittal = self.volume_obj.slice(normal=[1, 0, 0], origin=[x//2, 0, 0])
        self.nifti_slice_actors[nifti_obj.file_path + "axial_slice"] = (
            self.add_mesh(slice_axial, opacity=0.5, cmap='gray', show_scalar_bar=False)
        )
        self.nifti_slice_actors[nifti_obj.file_path + "coronal_slice"] = (
            self.add_mesh(slice_coronal, opacity=0.5, cmap='gray', show_scalar_bar=False)
        )
        self.nifti_slice_actors[nifti_obj.file_path + "sagittal_slice"] = (
            self.add_mesh(slice_sagittal, opacity=0.5, cmap='gray', show_scalar_bar=False)
        )
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

    def update_slice_position(self, axis, value, nifti_obj):
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

        new_slice = self.volume_obj.slice(normal=normal, origin=origin)
        key = nifti_obj.file_path + axis + "_slice"
        if key in self.nifti_slice_actors:
            # Màj acteur existant
            actor = self.nifti_slice_actors[key]
            actor.mapper.SetInputData(new_slice)
            actor.mapper.Update()
        else:
            actor = self.add_mesh(new_slice, opacity=0.5, cmap='gray', show_scalar_bar=False)
            self.nifti_slice_actors[key] = actor

        self.render()
