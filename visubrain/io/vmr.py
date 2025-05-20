# visubrain/io/vmr.py

import nibabel as nib
import numpy as np

from bvbabel.vmr import write_vmr, create_vmr


class VMRFile:
    def __init__(self):
        pass

    @staticmethod
    def write_from_nifti(nifti_path, output):
        """
        The code for building the VMR file is a copy (partially modified) of the vmr writing structure of part of the
        example as displayed on 15/05/2025 in the bvbabel repository (https://github.com/ofgulban/bvbabel) in the file
        "examples/read_nifti_write_vmr.py".

        MIT License

        Copyright (c) 2021 Omer Faruk Gulban

        Permission is hereby granted, free of charge, to any person obtaining a copy
        of this software and associated documentation files (the "Software"), to deal
        in the Software without restriction, including without limitation the rights
        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
        copies of the Software, and to permit persons to whom the Software is
        furnished to do so, subject to the following conditions:

        The above copyright notice and this permission notice shall be included in all
        copies or substantial portions of the Software.

        THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
        IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
        LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
        OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
        SOFTWARE.
        """
        nii = nib.load(nifti_path)
        affine = nii.affine
        print(affine)
        nii_data = np.nan_to_num(nii.get_fdata(), nan=0.)

        rowDirX = affine[0][0]
        rowDirY = affine[1][0]
        rowDirZ = affine[2][0]

        colDirX = affine[0][1]
        colDirY = affine[1][1]
        colDirZ = affine[2][1]

        normalX = affine[0][2]
        normalY = affine[1][2]
        normalZ = affine[2][2]

        sliceCenX = affine[0][3]
        sliceCenY = affine[1][3]
        sliceCenZ = affine[2][3]

        v16_data = np.copy(nii_data)
        thr_min, thr_max = np.percentile(v16_data[v16_data != 0], [0, 100])
        v16_data[v16_data > thr_max] = thr_max
        v16_data[v16_data < thr_min] = thr_min
        v16_data = v16_data - thr_min
        v16_data = v16_data / (thr_max - thr_min) * 65535
        v16_data = np.asarray(v16_data, dtype=np.ushort)

        dims = nii_data.shape
        voxdims = [nii.header["pixdim"][1],
                   nii.header["pixdim"][2],
                   nii.header["pixdim"][3]]
        # Create VMR
        vmr_header, vmr_data = create_vmr()

        # Update VMR data (type cast nifti data to uint8 after range normalization)
        vmr_data = np.copy(nii_data)
        thr_min, thr_max = np.percentile(vmr_data[vmr_data != 0], [1, 99])
        vmr_data[vmr_data > thr_max] = thr_max
        vmr_data[vmr_data < thr_min] = thr_min
        vmr_data = vmr_data - thr_min
        vmr_data = vmr_data / (thr_max - thr_min) * 225  # Special BV range
        vmr_data = np.asarray(vmr_data, dtype=np.ubyte)

        # Update VMR headers
        vmr_header["ColDirX"] = colDirX
        vmr_header["ColDirY"] = colDirY
        vmr_header["ColDirZ"] = colDirZ
        vmr_header["CoordinateSystem"] = 0
        vmr_header["DimX"] = dims[1]  # nii.header["dim"][2]
        vmr_header["DimY"] = dims[2]  # nii.header["dim"][3]
        vmr_header["DimZ"] = dims[0]  # nii.header["dim"][1]
        vmr_header["File version"] = 4
        vmr_header["FoVCols"] = 0.0
        vmr_header["FoVRows"] = 0.0
        vmr_header["FramingCubeDim"] = np.max(nii_data.shape)
        vmr_header["GapThickness"] = 0.0
        vmr_header["LeftRightConvention"] = 1
        vmr_header["NCols"] = 0
        vmr_header["NRows"] = 0
        vmr_header["NrOfPastSpatialTransformations"] = 0  # List here is for affine
        vmr_header["OffsetX"] = 0
        vmr_header["OffsetY"] = 0
        vmr_header["OffsetZ"] = 0
        vmr_header["PosInfosVerified"] = 1
        vmr_header["ReferenceSpaceVMR"] = 0
        vmr_header["RowDirX"] = rowDirX
        vmr_header["RowDirY"] = rowDirY
        vmr_header["RowDirZ"] = rowDirZ
        vmr_header["Slice1CenterX"] = sliceCenX
        vmr_header["Slice1CenterY"] = sliceCenY
        vmr_header["Slice1CenterZ"] = sliceCenZ
        vmr_header["SliceNCenterX"] = sliceCenX
        vmr_header["SliceNCenterY"] = sliceCenY
        vmr_header["SliceNCenterZ"] = sliceCenZ
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