# visubrain/io/nifti.py
import nibabel as nib


class NiftiFile:

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.image = nib.load(file_path)
        self.data = self.image.get_fdata()
        self.affine = self.image.affine
        self.shape = self.data.shape

    def get_affine(self):
        return self.affine

    def get_dimensions(self):
        return self.shape
