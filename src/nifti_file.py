import nibabel as nib
import numpy as np


class NiftiFile:

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.image = nib.load(file_path)
        self.data = self.image.get_fdata()  # Les données de l'image en espace RAS+mm
        self.affine = self.image.affine
        self.shape = self.data.shape

    def get_slice(self, orientation: str, index: int) -> np.ndarray:
        orientation = orientation.lower()
        if orientation == 'axial':
            if index < 0 or index >= self.shape[2]:
                raise ValueError(f"Axial index should be between 0 and {self.shape[2] - 1}")
            return self.data[:, :, index]
        elif orientation == 'coronal':
            if index < 0 or index >= self.shape[1]:
                raise ValueError(f"Coronal index should be between 0 and {self.shape[1] - 1}")
            return self.data[:, index, :]
        elif orientation == 'sagittal':
            if index < 0 or index >= self.shape[0]:
                raise ValueError(f"Sagittal index should be between 0 and {self.shape[0] - 1}")
            return self.data[index, :, :]
        else:
            raise ValueError("Unknown orientation. Use 'axial', 'coronal' or 'sagittal'.")

    def get_affine(self):
        return self.affine

    def get_dimensions(self):
        return self.shape
