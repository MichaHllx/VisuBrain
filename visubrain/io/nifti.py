"""
visubrain/io/nifti.py

Module for loading and handling NIfTI anatomical files in the VisuBrain application.

Provides the NiftiFile class for reading NIfTI images (.nii, .nii.gz), extracting data arrays,
affine transformations, orientation codes, and supporting both 3D and 4D volumes. Integrates
with VisuBrain's visualization, session management, and tractography workflows.

Classes:
    NiftiFile: Class for loading, querying, and extracting information from NIfTI files.
"""


import nibabel as nib


class NiftiFile:
    """
    Class for handling NIfTI files, reading data, affine and orientation.

    Attributes:
        file_path (str): Path to the NIfTI file.
        image (nibabel.Nifti1Image): Nibabel image object.
        data (ndarray): Image data array.
        affine (ndarray): Affine matrix.
        shape (tuple): Shape of the data array.
        orient (tuple): Orientation codes (RAS, LAS, etc).
    """

    def __init__(self, file_path: str):
        """
        Load a NIfTI file and extract its properties.

        Args:
            file_path (str): Path to the NIfTI file.
        """
        self.file_path = file_path
        self.image = nib.as_closest_canonical(nib.load(file_path))
        self.data = self.image.get_fdata()
        self.affine = self.image.affine
        self.shape = self.data.shape
        self.orient = nib.aff2axcodes(self.affine)

    def get_affine(self):
        """
        Get the affine transformation matrix.

        Returns:
            ndarray: 4x4 affine matrix.
        """
        return self.affine

    def get_dimensions(self):
        """
        Get the dimensions of the data array.

        Returns:
            tuple: Shape of the NIfTI data.
        """
        return self.shape

    def get_header(self):
        """
        Get the NIfTI header object.

        Returns:
            nibabel.Nifti1Header: Header of the NIfTI image.
        """
        return self.image.header

    def get_orientation(self):
        """
        Get the orientation codes of the image axes.

        Returns:
            tuple: Orientation codes (e.g., RAS).
        """
        return self.orient

    def get_data(self):
        """
        Get the image data array.

        Returns:
            ndarray: Image data.
        """
        return self.data

    def is_4d(self):
        """
        Check if the NIfTI file contains 4D data.

        Returns:
            bool: True if 4D, False otherwise.
        """
        return len(self.shape) == 4

    def get_3d_frame(self, t):
        """
        Extract a single 3D frame from a 4D NIfTI image.

        Args:
            t (int): Time/frame index to extract.

        Returns:
            ndarray: 3D frame data.

        Raises:
            ValueError: If the NIfTI is not 4D.
        """
        if not self.is_4d():
            raise ValueError("NIfTI file is not 4D")
        return self.data[..., t]
