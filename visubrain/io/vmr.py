"""
visubrain/io/vmr.py

Module for handling BrainVoyager VMR (Volumetric MRI) files in the VisuBrain application.

Provides the VMRFile class for creating and exporting VMR files from NIfTI volumes,
including necessary data conversions and header construction for BrainVoyager compatibility.
Supports workflows where BrainVoyager file formats are required alongside NIfTI data.

Classes:
    VMRFile: Class for generating VMR files from NIfTI anatomical volumes.
"""


import nibabel as nib
import numpy as np

from bvbabel.vmr import write_vmr, create_vmr


class VMRFile:
    """
    Class to handle VMR file creation and manipulation.

    Provides methods to write a VMR file from a NIfTI file using the bvbabel library.
    """

    def __init__(self):
        pass

    def write_from_nifti(self, nifti_path, output):
        """
        Write a VMR file from a NIfTI file.

        This method converts a NIfTI file into a BrainVoyager VMR file format (.vmr),
        with headers and intensity normalization as needed for compatibility.
        Code structure is adapted from bvbabel's example.

        Args:
            nifti_path (str): Path to the input NIfTI file.
            output (str): Output path for the VMR file.
        """
        nii = nib.load(nifti_path)
        nii_ras = nib.as_closest_canonical(nii)
        nii_ras_data = np.nan_to_num(nii_ras.get_fdata(), nan=0.)

        row_dir, col_dir, slice_1_center, slice_n_center = self._get_pos_from_nifti(nii_ras)

        row_dir_x, row_dir_y, row_dir_z = row_dir
        col_dir_x, col_dir_y, col_dir_z = col_dir
        slice_1_center_x, slice_1_center_y, slice_1_center_z = slice_1_center
        slice_n_center_x, slice_n_center_y, slice_n_center_z = slice_n_center

        v16_data = np.copy(nii_ras_data)
        thr_min, thr_max = np.percentile(v16_data[v16_data != 0], [0, 100])
        v16_data[v16_data > thr_max] = thr_max
        v16_data[v16_data < thr_min] = thr_min
        v16_data = v16_data - thr_min
        v16_data = v16_data / (thr_max - thr_min) * 65535
        v16_data = np.asarray(v16_data, dtype=np.ushort)

        dims = nii_ras_data.shape
        voxdims = [nii_ras.header["pixdim"][1],
                   nii_ras.header["pixdim"][2],
                   nii_ras.header["pixdim"][3]]
        # Create VMR
        vmr_header, vmr_data = create_vmr()

        # Update VMR data (type cast nifti data to uint8 after range normalization)
        vmr_data = np.copy(nii_ras_data)
        thr_min, thr_max = np.percentile(vmr_data[vmr_data != 0], [1, 99])
        vmr_data[vmr_data > thr_max] = thr_max
        vmr_data[vmr_data < thr_min] = thr_min
        vmr_data = vmr_data - thr_min
        vmr_data = vmr_data / (thr_max - thr_min) * 225  # Special BV range
        vmr_data = np.asarray(vmr_data, dtype=np.ubyte)

        # Update VMR headers
        vmr_header["ColDirX"] = col_dir_x
        vmr_header["ColDirY"] = col_dir_y
        vmr_header["ColDirZ"] = col_dir_z
        vmr_header["CoordinateSystem"] = 0
        vmr_header["DimX"] = dims[1]  # nii_ras.header["dim"][2] y
        vmr_header["DimY"] = dims[2]  # nii_ras.header["dim"][3] z
        vmr_header["DimZ"] = dims[0]  # nii_ras.header["dim"][1] x
        vmr_header["File version"] = 4
        vmr_header["FoVCols"] = 0.0
        vmr_header["FoVRows"] = 0.0
        vmr_header["FramingCubeDim"] = np.max(nii_ras_data.shape)
        vmr_header["GapThickness"] = 0.0
        vmr_header["LeftRightConvention"] = 1 # radiological(1) LAS+, neurological(0) RAS+
        vmr_header["NCols"] = 0
        vmr_header["NRows"] = 0
        vmr_header["NrOfPastSpatialTransformations"] = 0  # List here is for affine
        vmr_header["OffsetX"] = 0
        vmr_header["OffsetY"] = 0
        vmr_header["OffsetZ"] = 0
        vmr_header["PosInfosVerified"] = 1
        vmr_header["ReferenceSpaceVMR"] = 0
        vmr_header["RowDirX"] = row_dir_x
        vmr_header["RowDirY"] = row_dir_y
        vmr_header["RowDirZ"] = row_dir_z
        vmr_header["Slice1CenterX"] = slice_1_center_x
        vmr_header["Slice1CenterY"] = slice_1_center_y
        vmr_header["Slice1CenterZ"] = slice_1_center_z
        vmr_header["SliceNCenterX"] = slice_n_center_x
        vmr_header["SliceNCenterY"] = slice_n_center_y
        vmr_header["SliceNCenterZ"] = slice_n_center_z
        vmr_header["SliceThickness"] = 0.0
        vmr_header["VMROrigV16MaxValue"] = int(np.max(v16_data))
        vmr_header["VMROrigV16MeanValue"] = int(np.mean(v16_data))
        vmr_header["VMROrigV16MinValue"] = int(np.min(v16_data))
        vmr_header["VoxelResolutionInTALmm"] = 1
        vmr_header["VoxelResolutionVerified"] = 1
        vmr_header["VoxelSizeX"] = voxdims[0]
        vmr_header["VoxelSizeY"] = voxdims[1]
        vmr_header["VoxelSizeZ"] = voxdims[2]

        write_vmr(output, vmr_header, vmr_data)

    @staticmethod
    def _get_pos_from_nifti(nii):
        """
        Compute spatial orientation and position vectors from a NIfTI image.

        Args:
            nii (nibabel.Nifti1Image): Input NIfTI image.

        Returns:
            tuple: (row_dir, col_dir, slice_1_center, slice_n_center)
        """
        header = nii.header
        affine = nii.affine

        voxx, voxy, voxz = header['pixdim'][1:4]
        dimx, dimy, dimz = header['dim'][1:4]

        # Rotation matrix: in NIfTI this is usually sform/srow, so affine[:3,:3].
        niipos = affine.copy()

        nii2dcm = np.array([
            [-1, 0, 0, dimx - 1],
            [0, -1, 0, dimy - 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])

        dcmposmatrix = np.dot(niipos, nii2dcm)

        # First slice (middle x, middle y, z=0)
        dcm2bv1 = np.array([
            [1 / voxx, 0, 0, dimx / 2],
            [0, 1 / voxy, 0, dimy / 2],
            [0, 0, 1 / voxz, 0],
            [0, 0, 0, 1]
        ])
        first = dcmposmatrix @ dcm2bv1

        # Last slide (middle x, middle y, z=dimz-1)
        dcm2bvn = np.array([
            [1 / voxx, 0, 0, dimx / 2],
            [0, 1 / voxy, 0, dimy / 2],
            [0, 0, 1 / voxz, dimz - 1],
            [0, 0, 0, 1]
        ])
        last = dcmposmatrix @ dcm2bvn

        slice_1_center = [first[0,3], first[1,3], first[2,3]]
        slice_n_center = [last[0,3], last[1,3], last[2,3]]
        row_dir = [first[0,0], first[1,0], first[2,0]]
        col_dir = [first[0,1], first[1,1], first[2,1]]

        return row_dir, col_dir, slice_1_center, slice_n_center