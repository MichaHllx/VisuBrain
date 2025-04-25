# visubrain/core/converter.py

import numpy as np

from pathlib import Path

from nibabel.streamlines import Tractogram, TrkFile, TckFile
from dipy.io.streamline import load_tractogram, save_tractogram

from visubrain.io.fbr import BinaryFbrFile
from visubrain.io.tractography import TractographyFile


class Converter:
    def __init__(self,
                 input_file: str,
                 output_file: str,
                 anatomical_ref: str | None = None):
        self.input = input_file
        self.output = output_file

        self.anatomical_ref = anatomical_ref # pour le cas du tck (obligatoire)

        self.in_ext = Path(input_file).suffix.lower().lstrip('.')
        self.out_ext = Path(output_file).suffix.lower().lstrip('.')
        self._validate_extensions()

    _CONVERTERS = {
        ('trk','fbr'): '_trk_to_fbr',
        ('fbr','trk'): '_fbr_to_trk',
        ('trk','tck'): '_trk_to_tck',
        ('tck','trk'): '_tck_to_trk',
    }

    def _validate_extensions(self):
        key = (self.in_ext, self.out_ext)
        if key not in self._CONVERTERS:
            raise ValueError(f"Conversion {key} not supported")

    def convert(self):
        method_name = self._CONVERTERS[(self.in_ext, self.out_ext)]
        getattr(self, method_name)()

    def _trk_to_tck(self):
        sft = load_tractogram(str(self.input), 'same')
        save_tractogram(sft, str(self.output))

    def _tck_to_trk(self):
        if self.anatomical_ref is None:
            raise ValueError("A tck file needs an anatomical reference file.")
        sft = load_tractogram(self.input, self.anatomical_ref)
        save_tractogram(sft, self.output)

    def _trk_to_fbr(self):
        # Charger le fichier .trk
        sft = load_tractogram(str(self.input), 'same')
        sft.to_vox()
        sft.to_corner()
        streamlines = sft.streamlines

        tracto_obj = TractographyFile(str(self.input))
        points, colors, connectivity = tracto_obj.get_color_points(show_points=False)

        header, fibers = self._prepare_fbr_data_from_trk(streamlines, colors)

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

        # Préparation du header
        header = {
            'FileVersion': 5,
            'CoordsType': 2,
            'FibersOrigin': [128.0, 128.0, 128.0],
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

        fbr_obj = BinaryFbrFile(self.input)

        # Extraction data pour format .trk
        streamlines, data_per_point, affine_to_rasmm, header = self._prepare_trk_data_from_fbr(fbr_obj)

        tractogram = Tractogram(streamlines=streamlines, data_per_point=data_per_point, affine_to_rasmm=affine_to_rasmm)
        new_trk = TrkFile(tractogram=tractogram, header=header)
        new_trk.save(self.output)

    @staticmethod
    def _prepare_trk_data_from_fbr(fbr_obj):
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

        affine_to_rasmm = np.array([[1, 0, 0, 0],
                                    [0, 1, 0, 0],
                                    [0, 0, 1, 0],
                                    [0, 0, 0, 1]])  # Affine par défaut, à adapter

        # Création d'un header simplifié pour .trk, à adapter
        x_res = int(fbr_obj.fibers_origin[0] * 2)   # |
        y_res = int(fbr_obj.fibers_origin[1] * 2)   # |→ BV considère l'origine comme étant le centre du volume
        z_res = int(fbr_obj.fibers_origin[2] * 2)   # |

        voxel_size = [1.0, 1.0, 1.0]  # à adapter

        header = {
            'magic_number': b'TRACK',
            'dimensions': np.array([x_res, y_res, z_res], dtype=np.int16),
            'voxel_sizes': np.array(voxel_size, dtype=np.float32),
            'origin': np.array(fbr_obj.fibers_origin, dtype=np.float32),
            'nb_scalars_per_point': 0,
            'scalar_name': np.array([b''] * 10, dtype='|S20'),
            'nb_properties_per_streamline': 0,
            'property_name': np.array([b''] * 10, dtype='|S20'),
            'voxel_to_rasmm': np.array(affine_to_rasmm, dtype=np.float32),
            'reserved': b'',
            'voxel_order': b'RAS',
            'pad2': b'',
            'image_orientation_patient': np.array([0., 0., 0., 0., 0., 0.], dtype=np.float32),
            'pad1': b'',
            'invert_x': b'',
            'invert_y': b'',
            'invert_z': b'',
            'swap_xy': b'',
            'swap_yz': b'',
            'swap_zx': b'',
            'nb_streamlines': fbr_obj.num_fibers,
            'version': 2,
            'hdr_size': 1000
        }

        return streamlines, data_per_point, affine_to_rasmm, header
