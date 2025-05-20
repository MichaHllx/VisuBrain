# visubrain/core/converter.py
import gzip
import shutil

import numpy as np
import nibabel as nib

from pathlib import Path

from dipy.io.stateful_tractogram import StatefulTractogram, Space
from dipy.io.streamline import load_tractogram, save_tractogram
from bvbabel.vmr import read_vmr

from visubrain.io.fbr import BinaryFbrFile
from visubrain.io.tractography import Tractography
from visubrain.io.vmr import VMRFile


class Converter:
    def __init__(self,
                 input_file: str,
                 output_file: str,
                 anatomical_ref: str | None = None):
        self.input = input_file
        self.output = output_file

        self.anatomical_ref = anatomical_ref # pour tck et fbr (obligatoire)

        self.in_ext = ''.join(Path(input_file).suffixes).lower().lstrip('.')
        self.out_ext = ''.join(Path(output_file).suffixes).lower().lstrip('.')
        self._validate_extensions()

    _CONVERTERS = {
        ('trk','fbr'): '_trk_to_fbr',
        ('fbr','trk'): '_fbr_to_trk',
        ('trk','tck'): '_trk_to_tck',
        ('tck','trk'): '_tck_to_trk',
        ('voi', 'nii'): '_voi_to_nii',
        ('voi', 'nii.gz'): '_voi_to_nii_gz',
        ('nii', 'voi'): '_nii_to_voi',
        ('nii.gz', 'voi'): '_nii_gz_to_voi',
        ('vmr', 'nii'): '_vmr_to_nii',('vmr', 'nii.gz'): '_vmr_to_nii',
        ('nii', 'vmr'): '_nii_to_vmr',('nii.gz', 'vmr'): '_nii_to_vmr'
    }

    def _validate_extensions(self):
        key = (self.in_ext, self.out_ext)
        if key not in self._CONVERTERS:
            raise ValueError(f"Conversion {key} not supported")

    def convert(self):
        try:
            method_name = self._CONVERTERS[(self.in_ext, self.out_ext)]
            getattr(self, method_name)()
        except:
            raise ValueError(f"conversion {self.in_ext} to {self.out_ext}")

    def _trk_to_tck(self):
        sft = load_tractogram(str(self.input), 'same')
        save_tractogram(sft, str(self.output))

    def _tck_to_trk(self):
        if self.anatomical_ref is None:
            raise ValueError("A tck file needs an anatomical reference file.")
        sft = load_tractogram(self.input, self.anatomical_ref)
        save_tractogram(sft, self.output)

    def _vmr_to_nii(self):
        try:
            header, data = read_vmr(self.input)

            colDirX = header["ColDirX"]
            colDirY = header["ColDirY"]
            colDirZ = header["ColDirZ"]

            rowDirX = header["RowDirX"]
            rowDirY = header["RowDirY"]
            rowDirZ = header["RowDirZ"]

            rowDir = np.array([rowDirX, rowDirY, rowDirZ])
            colDir = np.array([colDirX, colDirY, colDirZ])

            normal = np.cross(rowDir, colDir)

            sliceCenterX = header["SliceNCenterX"]
            sliceCenterY = header["SliceNCenterY"]
            sliceCenterZ = header["SliceNCenterZ"]

            custom_affine = np.eye(4)
            custom_affine[0:3, 0] = rowDir
            custom_affine[0:3, 1] = colDir
            custom_affine[0:3, 2] = normal

            if np.all(custom_affine[:3, :3] == 0):
                custom_affine = np.eye(4) # proposer au user d'indiquer une anat de ref nifti pour avoir une mat affine corresp ?

            custom_affine[0:3, 3] = [sliceCenterX, sliceCenterY, sliceCenterZ]

            nii = nib.Nifti1Image(data, affine=custom_affine)
            nib.save(nii, self.output)
        except:
            raise ValueError("The input file is not a valid BrainVoyager VMR file.")

    def _nii_to_vmr(self):
        try:
            vmr_obj = VMRFile
            vmr_obj.write_from_nifti(self.input, self.output)
        except:
            raise ValueError("The input file is not a valid Nifti file.")

    def _voi_to_nii(self):
        with gzip.open(self.input, 'rb') as f_in:
            with open(self.output, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    def _voi_to_nii_gz(self):
        shutil.copy(self.input, self.output)

    def _nii_to_voi(self):
        with open(self.input, 'rb') as f_in:
            with gzip.open(self.output, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    def _nii_gz_to_voi(self):
        shutil.copy(self.input, self.output)

    def _trk_to_fbr(self):
        tracto_obj = Tractography(str(self.input))

        points, colors, connectivity = tracto_obj.get_color_points(show_points=False)

        header, fibers = self._prepare_fbr_data_from_trk(tracto_obj.get_streamlines(), colors)
        new_fbr = BinaryFbrFile()
        new_fbr.write_fbr(self.output, header, fibers)

    @staticmethod
    def _prepare_fbr_data_from_trk(streamlines, colors):

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
            'CoordsType': 0, # RASmm
            'FibersOrigin': [0.0, 0.0, 0.0],
            'NrOfGroups': 1,
            'Groups': [
                {
                    'Name': 'trk_conversion',
                    'Visible': 1,
                    'Animate': -1,
                    'Thickness': 0.3,
                    'Color': [0, 255, 255],
                    'NrOfFibers': len(fibers)
                }
            ]
        }
        return header, fibers

    def _fbr_to_trk(self):
        if self.anatomical_ref is None:
            raise ValueError("A fbr file needs an anatomical reference file.")
        fbr_obj = BinaryFbrFile(self.input)
        ref_img = nib.load(self.anatomical_ref)

        output_streamlines = self._prepare_trk_data_from_fbr(fbr_obj, ref_img)

        tracto = StatefulTractogram(output_streamlines, reference=ref_img, space=Space.RASMM)
        save_tractogram(tracto, self.output)

    def _prepare_trk_data_from_fbr(self, fbr_obj, ref_img):
        streamlines = []
        data_per_point = {'colors': []}
        for group in fbr_obj.groups:
            for fiber in group['fibers']:
                pts = np.array(fiber['points'])
                colors = np.array(fiber['colors'])
                if pts.shape[0] < 2:
                    continue
                streamlines.append(pts)
                data_per_point['colors'].append(colors)

        streamlines_corr = self._correct_fbr_to_nifti(streamlines, ref_img)
        valid_streamlines = self._filter_valid_streamlines(streamlines_corr, ref_img)

        return valid_streamlines

    def _correct_fbr_to_nifti(self, streamlines, img):
        shape = np.array(img.shape[:3])
        affine = img.affine
        center_voxel = (shape - 1) / 2.0
        center_mm = nib.affines.apply_affine(affine, center_voxel)
        scale = np.sign(np.diag(affine)[:3])
        streamlines_corr = [sl + center_mm for sl in streamlines]
        return streamlines_corr

    def _filter_valid_streamlines(self, streamlines, img):
        shape = np.array(img.shape[:3])
        inv_aff = np.linalg.inv(img.affine)
        valid = []
        for sl in streamlines:
            ijk = nib.affines.apply_affine(inv_aff, sl)
            if (ijk >= 0).all() and (ijk < shape).all():
                valid.append(sl)
        return valid
