import numpy as np

from PyQt6.QtWidgets import QMessageBox
from dipy.io.streamline import load_tractogram
from dipy.tracking.streamline import transform_streamlines


class TractographyFile:

    def __init__(self, file_path: str, reference_nifti=None):
        self.file_path = file_path
        self.reference_nifti = reference_nifti  # objet "NiftiFile"
        self.streamlines, self.raw_data = self._load_streamlines()

    def _load_streamlines(self):
        if self.file_path.endswith(".tck"):
            if not self.reference_nifti:
                QMessageBox.critical(None, "Error", "A tck file needs an anatomical reference image beforehand.")
                return None, None
            tracto = load_tractogram(self.file_path, self.reference_nifti.file_path)
        else:
            tracto = load_tractogram(self.file_path, 'same')

        if self.reference_nifti is not None:
            # passage de l'espace image à RASmm du fichier anat
            affine = self.reference_nifti.affine
            stream_reg = transform_streamlines(tracto.streamlines, np.linalg.inv(affine))
            return stream_reg, tracto

        return tracto.streamlines, tracto

    def get_streamlines(self):
        return self.streamlines
