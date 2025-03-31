import nibabel as nib
import numpy as np

from dipy.io.streamline import load_tractogram
from unravel.utils import get_streamline_density

from src.fbr_management.write_binary_fbr import write_fbr

def trk_to_fbr(trk_file_path, fbr_file_path):

    # Charger le fichier .trk
    sft = load_tractogram(trk_file_path, 'same')
    sft.to_vox()
    sft.to_corner()
    streamlines = sft.streamlines

    rgb = get_streamline_density(sft, color=True)                                       #|
    coord_increase = np.floor(streamlines._data).astype(int)                            #|→ problèmes de couleur !
    rgb_points = rgb[coord_increase[:, 0], coord_increase[:, 1], coord_increase[:, 2]]  #|

    # Préparer les données pour le fichier .fbr
    fibers = []
    color_index = 0
    for streamline in streamlines:
        fiber = {
            'NrOfPoints': len(streamline),
            'Points': []
        }
        for point in streamline:
            color = rgb_points[color_index]
            fiber['Points'].append([float(point[0]), float(point[1]), float(point[2]),
                                    int(color[0]), int(color[1]), int(color[2])])
            color_index += 1
        fibers.append(fiber)

    # Créer l'en-tête du fichier .fbr
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

    write_fbr(fbr_file_path, header, fibers)
