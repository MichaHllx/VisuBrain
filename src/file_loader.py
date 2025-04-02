import nibabel as nib
import numpy as np

from dipy.io.stateful_tractogram import Space, StatefulTractogram
from dipy.io.streamline import load_tractogram
from dipy.tracking.streamline import transform_streamlines


class FileLoader:

    def __init__(self):
        self.nifti_affine = None
        self.img = None
        self.nifti_path = None

    def load_nifti(self, file_path):
        """Charge un fichier NIfTI (.nii, .nii.gz)"""

        self.nifti_path = file_path
        self.img = nib.load(file_path)
        data = self.img.get_fdata() # dans le RAS+mm space
        self.nifti_affine = self.img.affine

        return data, self.nifti_affine

    def load_trk(self, file_path):
        """Charge un fichier tractographie .trk"""
        if self.nifti_path is not None:
            if file_path.endswith(".tck"):
                trk = load_tractogram(file_path, self.nifti_path)
            else:
                trk = load_tractogram(file_path, 'same') # voxel space (dimensions i,j,k exprimées en unité de voxel) ??
            # TODO : info sur la correspondance des axes du voxel space par rapport aux axes anatomiques !

            stream_reg = transform_streamlines(trk.streamlines, np.linalg.inv(self.nifti_affine))
            sft_reg = StatefulTractogram(stream_reg, self.img, Space.RASMM)
            streamlines = sft_reg.streamlines
        else:
            trk = load_tractogram(file_path, 'same')
            streamlines = trk.streamlines

        return streamlines, trk
