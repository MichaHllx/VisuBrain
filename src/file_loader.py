import nibabel as nib
import numpy as np

from PyQt6.QtWidgets import QMessageBox

from dipy.io.stateful_tractogram import Space, StatefulTractogram
from dipy.io.streamline import load_tractogram
from dipy.tracking.streamline import transform_streamlines


class FileLoader:

    def __init__(self):
        self.nifti_affine = None
        self.img = None
        self.nifti_path = None

    def load_nifti(self, nifti_path):
        """Charge un fichier NIfTI (.nii, .nii.gz)"""

        self.nifti_path = nifti_path
        self.img = nib.load(nifti_path)
        data = self.img.get_fdata() # dans le RAS+mm space
        self.nifti_affine = self.img.affine

        return data, self.nifti_affine

    def load_trk(self, trk_path):
        """Charge un fichier tractographie .trk ou .tck"""

        if self.nifti_path is None and trk_path.endswith(".tck"):
            QMessageBox.critical(None, "Error", "A tck file needs an anatomical reference image beforehand.")
            return None, None

        if trk_path.endswith(".tck"):
            tracto = load_tractogram(trk_path, self.nifti_path)
        else:
            tracto = load_tractogram(trk_path, 'same')

        if self.nifti_path is not None:
            stream_reg = transform_streamlines(tracto.streamlines, np.linalg.inv(self.nifti_affine))
            sft_reg = StatefulTractogram(stream_reg, self.img, Space.RASMM)
            streamlines = sft_reg.streamlines
        else:
            streamlines = tracto.streamlines

        return streamlines, tracto
