import nibabel as nib
import numpy as np

from dipy.io.stateful_tractogram import Space, StatefulTractogram
from dipy.io.streamline import load_tractogram
from dipy.tracking.streamline import transform_streamlines

nifti_affine = None
img = None
nifti_path = None

def load_nifti(file_path):
    """Charge un fichier NIfTI (.nii, .nii.gz)"""
    global nifti_affine, img, nifti_path

    nifti_path = file_path
    img = nib.load(file_path)
    data = img.get_fdata() # dans le RAS+mm space
    nifti_affine = img.affine

    return data, nifti_affine

def load_trk(file_path):
    """Charge un fichier tractographie .trk"""
    if (nifti_path is not None):
        if file_path.endswith(".tck"):
            trk = load_tractogram(file_path, nifti_path)
        else:
            trk = load_tractogram(file_path, 'same') # voxel space (dimensions i,j,k exprimées en unité de voxel) ??
        # TODO : info sur la correspondance des axes du voxel space par rapport aux axes anatomiques !

        stream_reg = transform_streamlines(trk.streamlines, np.linalg.inv(nifti_affine))
        sft_reg = StatefulTractogram(stream_reg, img, Space.RASMM)
        streamlines = sft_reg.streamlines
    else:
        trk = load_tractogram(file_path, 'same')
        streamlines = trk.streamlines

    return streamlines, trk