
"""
visubrain/core/converter.py

Module for converting neuroimaging file formats in the VisuBrain project.

Provides the Converter class, which enables conversion between anatomical and tractography
file formats (such as NIfTI, TRK, TCK, FBR, VMR) with optional anatomical reference handling.
Supports seamless integration with VisuBrain's GUI and batch operations.

Classes:
    Converter: Handles file format conversion for neuroimaging and tractography data.
"""


import gzip
import shutil
from pathlib import Path

import numpy as np
import nibabel as nib

from dipy.io.stateful_tractogram import StatefulTractogram, Space
from dipy.io.streamline import load_tractogram, save_tractogram
from bvbabel.vmr import read_vmr

from visubrain.io.fbr import BinaryFbrFile
from visubrain.io.tractography import Tractography
from visubrain.io.vmr import VMRFile


class Converter:
    """
    Utility class to convert between different neuroimaging file formats
    (VMR, NIfTI, VOI, TRK, TCK, FBR).

    Handles conversions, manages file extension detection and provides multiple private methods
    for each specific conversion.

    Attributes:
        input (str): Path to the input file.
        output (str): Path to the output file.
        anatomical_ref (str | None): Optional anatomical reference for certain conversions.
        in_ext (str): Extension of the input file.
        out_ext (str): Extension of the output file.
    """
    def __init__(self,
                 input_file: str,
                 output_file: str,
                 anatomical_ref: str | None = None):
        """
        Initialize the Converter.

        Args:
            input_file (str): Path to the input file.
            output_file (str): Path to the output file.
            anatomical_ref (str, optional): Anatomical reference, required for some formats
            (e.g., tck, fbr).
        """
        self.input = input_file
        self.output = output_file

        self.anatomical_ref = anatomical_ref # pour tck et fbr (obligatoire)

        self.in_ext = ''.join(Path(input_file).suffixes).lower().lstrip('.')
        self.out_ext = ''.join(Path(output_file).suffixes).lower().lstrip('.')
        self._validate_extensions()

    _CONVERTERS = {
        ('trk','fbr'): 'trk_to_fbr',
        ('fbr','trk'): 'fbr_to_trk',
        ('trk','tck'): 'trk_to_tck',
        ('tck','trk'): 'tck_to_trk',
        ('voi', 'nii'): 'voi_to_nii',
        ('voi', 'nii.gz'): 'voi_to_nii_gz',
        ('nii', 'voi'): 'nii_to_voi',
        ('nii.gz', 'voi'): 'nii_gz_to_voi',
        ('vmr', 'nii'): 'vmr_to_nii',('vmr', 'nii.gz'): 'vmr_to_nii',
        ('nii', 'vmr'): 'nii_to_vmr',('nii.gz', 'vmr'): 'nii_to_vmr'
    }

    def _validate_extensions(self):
        """
        Validate that the combination of input and output extensions is supported.

        Raises:
            ValueError: If the conversion is not supported.
        """
        key = (self.in_ext, self.out_ext)
        if key not in self._CONVERTERS:
            raise ValueError(f"Conversion {key} not supported")

    def convert(self):
        """
        Perform the conversion by dispatching to the appropriate method.

        Raises:
            ValueError: If conversion fails.
        """
        try:
            method_name = self._CONVERTERS[(self.in_ext, self.out_ext)]
            getattr(self, method_name)()
        except Exception as e :
            raise ValueError(f"Conversion {self.in_ext} to {self.out_ext} \n {e}") from e

    def trk_to_tck(self):
        """Convert a .trk tractography file to .tck format."""
        sft = load_tractogram(str(self.input), 'same')
        save_tractogram(sft, str(self.output))

    def tck_to_trk(self):
        """
        Convert a .tck tractography file to .trk format.

        Raises:
            ValueError: If anatomical reference is not provided.
        """
        if self.anatomical_ref is None:
            raise ValueError("A tck file needs an anatomical reference file.")
        sft = load_tractogram(self.input, self.anatomical_ref)
        save_tractogram(sft, self.output)

    def vmr_to_nii(self):
        """
        Convert a VMR file to NIfTI (.nii) format.

        Raises:
            ValueError: If conversion fails.
        """
        try:
            header, data = read_vmr(self.input)

            col_dir = np.array([header["ColDirX"],
                                header["ColDirY"],
                                header["ColDirZ"]])

            row_dir = np.array([header["RowDirX"],
                                header["RowDirY"],
                                header["RowDirZ"]])

            image_orientation_dcm = np.column_stack((row_dir,
                                                     col_dir,
                                                     np.cross(row_dir, col_dir)))

            # volume center position
            slice1_center = np.array([header["Slice1CenterX"],
                                      header["Slice1CenterY"],
                                      header["Slice1CenterZ"]])
            slice_n_center = np.array([header["SliceNCenterX"],
                                       header["SliceNCenterY"],
                                       header["SliceNCenterZ"]])
            image_position_center_dcm = (slice1_center + slice_n_center) / 2

            # 4x4 matrix world (dicom) to patient
            pixel_spacing_dcm = np.array([header["VoxelSizeX"],
                                          header["VoxelSizeY"],
                                          header["VoxelSizeZ"]])# voxels size (mm)
            dcm_to_patient = np.eye(4)
            dcm_to_patient[:3, :3] = image_orientation_dcm * pixel_spacing_dcm.reshape(1, 3)
            dcm_to_patient[:3, 3] = image_position_center_dcm

            # center of the volume to corner (voxel origin)
            shift_center = np.eye(4)
            shift_center[0, 3] = -(header["DimX"] + 1) / 2
            shift_center[1, 3] = -(header["DimY"] + 2) / 2
            shift_center[2, 3] = -(header["DimZ"] + 2) / 2
            # shift center to corner
            dcm_to_patient = np.dot(dcm_to_patient, shift_center)

            # np.diag([-1, -1, 1, 1]) = patient_to_ras = (flip X et Y)
            voxel2world = np.dot(np.diag([-1, -1, 1, 1]), dcm_to_patient)

            if np.all(voxel2world[:3, :3] == 0):
                voxel2world = np.eye(4)

            nii = nib.Nifti1Image(data, affine=voxel2world)
            nii.header["pixdim"][1] = header["VoxelSizeX"]
            nii.header["pixdim"][2] = header["VoxelSizeY"]
            nii.header["pixdim"][3] = header["VoxelSizeZ"]
            nii.header["dim"][2] = header["DimX"]
            nii.header["dim"][3] = header["DimY"]
            nii.header["dim"][1] = header["DimZ"]
            nib.save(nii, self.output)
        except Exception as exc:
            raise ValueError("Error while converting the VMR file.") from exc

    def nii_to_vmr(self):
        """
        Convert a NIfTI (.nii) file to VMR format.

        Raises:
            ValueError: If the input file is not a valid NIfTI file.
        """
        try:
            vmr_obj = VMRFile()
            vmr_obj.write_from_nifti(self.input, self.output)
        except Exception as exc:
            raise ValueError("The input file is not a valid Nifti file.") from exc

    def voi_to_nii(self):
        """Convert a VOI (gzipped) file to uncompressed NIfTI (.nii)."""
        with gzip.open(self.input, 'rb') as f_in:
            with open(self.output, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    def voi_to_nii_gz(self):
        """Copy a VOI file to a NIfTI compressed format (.nii.gz)."""
        shutil.copy(self.input, self.output)

    def nii_to_voi(self):
        """Convert a NIfTI (.nii) file to gzipped VOI format."""
        with open(self.input, 'rb') as f_in:
            with gzip.open(self.output, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    def nii_gz_to_voi(self):
        """Copy a gzipped NIfTI file (.nii.gz) to VOI format."""
        shutil.copy(self.input, self.output)

    def trk_to_fbr(self):
        """Convert a .trk tractography file to .fbr format."""

        tracto_obj = Tractography(str(self.input), 0, reference_nifti=None)

        sf_t: StatefulTractogram = tracto_obj.sf_t
        dim_mm = sf_t.dimensions * sf_t.voxel_sizes

        origin_mm_pil = [dim_mm[1] / 2, dim_mm[2] / 2, dim_mm[0] / 2]

        # streamlines RAS+ mm
        streamlines_ras = tracto_obj.get_streamlines()

        # streamlines RAS+ mm --> PIL+ mm  (BVI)
        streamlines_pil = []
        for sl in streamlines_ras:
            # flip axes + axe orient = (x_pil = -y_ras, y_pil = -z_ras, z_pil = -x_ras)
            sl_pil = np.stack([-sl[:, 1], -sl[:, 2], -sl[:, 0]], axis=1)

            # origin offset
            sl_pil = sl_pil + origin_mm_pil

            streamlines_pil.append(sl_pil)

        _, colors, _ = tracto_obj.get_color_points(show_points=False, streamlines=streamlines_pil)
        header, fibers = self._prepare_fbr_data_from_trk(streamlines_pil, colors, origin_mm_pil)
        new_fbr = BinaryFbrFile()
        new_fbr.write_fbr(self.output, header, fibers)

    @staticmethod
    def _prepare_fbr_data_from_trk(streamlines, colors, origin):
        """
        Prepare the header and fiber data for writing an FBR file from TRK streamlines.

        Args:
            streamlines (list): List of streamlines.
            colors (list): List of colors for each point in each streamline.

        Returns:
            tuple: Header dict, fibers list.
        """
        fibers = []
        for streamline, color in zip(streamlines, colors):
            fiber = {
                'NrOfPoints': len(streamline),
                'Points': [
                    [float(point[0]), float(point[1]), float(point[2]),
                     int(rgb[0]), int(rgb[1]), int(rgb[2])]
                    for point, rgb in zip(streamline, color)
                ]
            }
            fibers.append(fiber)

        header = {
            'FileVersion': 5,
            'CoordsType': 2,
            'FibersOrigin': [origin[0], origin[1], origin[2]],
            'NrOfGroups': 1,
            'Groups': [
                {
                    'Name': 'trk_conversion_PIL+mm',
                    'Visible': 1,
                    'Animate': -1,
                    'Thickness': 0.3,
                    'Color': [0, 255, 255],
                    'NrOfFibers': len(fibers)
                }
            ]
        }
        return header, fibers

    def fbr_to_trk(self):
        """
        Convert a .fbr fiber bundle file to .trk tractography format.

        Raises:
            ValueError: If anatomical reference is not provided.
        """
        if self.anatomical_ref is None:
            raise ValueError("A fbr file needs an anatomical reference file.")

        fbr_obj = BinaryFbrFile(self.input)
        if fbr_obj.get_header()['CoordsType'] != 2:
            raise ValueError("Only FBR with BVI coordinates are supported.")

        streamlines = self._prepare_trk_data_from_fbr(fbr_obj)

        try:
            sf_t = StatefulTractogram(streamlines, self.anatomical_ref, space=Space.RASMM)
            save_tractogram(sf_t, self.output)
        except Exception as exc:
            raise ValueError("Problem between the reference anatomy and the fbr file") from exc

    @staticmethod
    def _prepare_trk_data_from_fbr(fbr_obj):
        """
        Prepare TRK streamlines from an FBR file object and a NIfTI reference image.

        Args:
            fbr_obj (BinaryFbrFile): FBR file object.

        Returns:
            list: List of valid streamlines.
        """
        streamlines = []
        for group in fbr_obj.groups:
            for fiber in group['fibers']:
                if len(fiber['points']) < 2:
                    continue

                fbr_pil = np.array(fiber['points'], dtype=np.float32)
                # flip axes + axe orient = (x_ras = -z_pil, y_ras = -x_pil, z_ras = -y_pil)
                trk_x, trk_y, trk_z = -fbr_pil[:, 2], -fbr_pil[:, 0], -fbr_pil[:, 1]

                streamline_ras_space = np.column_stack((trk_x, trk_y, trk_z))
                streamlines.append(streamline_ras_space.astype(np.float32))

        return streamlines
