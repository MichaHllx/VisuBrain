import os
import numpy as np

from nibabel.streamlines import Tractogram, TrkFile
from dipy.io.streamline import load_tractogram

from fbr_file import BinaryFbrFile


class Converter:

    def __init__(self, input_file: str, output_file: str, conversion_type: str):
        self.input_file = input_file
        self.output_file = output_file
        self.conversion_type = conversion_type.lower()
        self._validate_files()

    def _validate_files(self):
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Entry file '{self.input_file}' does not exist.")

        ext = os.path.splitext(self.input_file)[1].lower()
        if self.conversion_type == "trk_to_fbr":
            if ext != '.trk':
                raise ValueError(
                    f"For a trk_to_fbr conversion, entry file should be type '.trk', "
                    f"but type '{ext}' was given.")
        elif self.conversion_type == "fbr_to_trk":
            if ext != '.fbr':
                raise ValueError(
                    f"For a fbr_to_trk conversion, entry file should be type '.fbr', "
                    f"but type '{ext}' was given.")

    def convert(self):
        if self.conversion_type == "trk_to_fbr":
            self._convert_trk_to_fbr()
        elif self.conversion_type == "fbr_to_trk":
            self._convert_fbr_to_trk()
        else:
            raise ValueError("Conversion type unsupported. Please use 'trk_to_fbr' or 'fbr_to_trk'.")

    def _convert_trk_to_fbr(self):
        # Charger le fichier .trk
        sft = load_tractogram(self.input_file, 'same')
        sft.to_vox()
        sft.to_corner()
        streamlines = sft.streamlines

        header, fibers = self._prepare_fbr_data_from_trk(streamlines)

        new_fbr = BinaryFbrFile()
        new_fbr.write_fbr(self.output_file, header, fibers)

    @staticmethod
    def _prepare_fbr_data_from_trk(streamlines):

        fibers = []
        for streamline in streamlines:
            fiber = {
                'NrOfPoints': len(streamline),
                'Points': [
                    [float(point[0]), float(point[1]), float(point[2]), 255, 255, 255]
                    for point in streamline
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

    def _convert_fbr_to_trk(self):

        fbr_obj = BinaryFbrFile(self.input_file)

        # Extraction data pour format .trk
        streamlines, data_per_point, affine_to_rasmm, header = self._prepare_trk_data_from_fbr(fbr_obj)

        tractogram = Tractogram(streamlines=streamlines, data_per_point=data_per_point, affine_to_rasmm=affine_to_rasmm)
        new_trk = TrkFile(tractogram=tractogram, header=header)
        new_trk.save(self.output_file)

    @staticmethod
    def _prepare_trk_data_from_fbr(fbr_obj):
        streamlines = []
        data_per_point = {'colors': []}
        for group in fbr_obj._groups:
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
        x_res = int(fbr_obj._fibers_origin[0] * 2)   # |
        y_res = int(fbr_obj._fibers_origin[1] * 2)   # |→ BV considère l'origine comme étant le centre du volume
        z_res = int(fbr_obj._fibers_origin[2] * 2)   # |

        voxel_size = [1.0, 1.0, 1.0]  # à adapter

        header = {
            'magic_number': b'TRACK',
            'dimensions': np.array([x_res, y_res, z_res], dtype=np.int16),
            'voxel_sizes': np.array(voxel_size, dtype=np.float32),
            'origin': np.array(fbr_obj._fibers_origin, dtype=np.float32),
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
            'nb_streamlines': fbr_obj._num_fibers,
            'version': 2,
            'hdr_size': 1000
        }

        # Info sur les dimensions de l'image FBR
        # Info sur les dimensions des voxels de l'image FBR
        # Info sur l'ordre/l'orientation des voxels de l'image FBR (RAS, RAS+, LPS, ...)
        # Donc info sur l'espace de référence utilisé pour l'image FBR
        # Info sur (0,0,0) au centre d'un voxel ou dans le coin (TRK c'est dans le coin d'un voxel)
        # Ensuite trouver la transformation affine pour passer de l'espace des voxels de l'image FBR à l'espace RASMM (affine_to_rasmm)

        return streamlines, data_per_point, affine_to_rasmm, header
