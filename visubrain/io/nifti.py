# visubrain/io/nifti.py
import nibabel as nib


class NiftiFile:

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.image = nib.as_closest_canonical(nib.load(file_path))
        self.data = self.image.get_fdata()
        self.affine = self.image.affine
        self.shape = self.data.shape
        self.orient = nib.aff2axcodes(self.affine)

    def get_affine(self):
        return self.affine

    def get_dimensions(self):
        return self.shape

    def get_header(self):
        return self.image.header

    def get_orientation(self):
        return self.orient

    def get_data(self):
        return self.data
