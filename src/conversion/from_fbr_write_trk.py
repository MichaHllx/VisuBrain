import numpy as np
import nibabel as nib
from nibabel.streamlines.tractogram import Tractogram
from nibabel.streamlines import trk, TrkFile, header

from src.fbr_management.read_binary_fbr import BinaryFBRfile # Import the custom FBR reader

# --- Step 1. Read the FBR file ---
current_fbr = BinaryFBRfile('/Users/mhalleux/Library/CloudStorage/Dropbox/Mac/Documents/UCL/Master2_Q2/TFE/TFE_repo/file_samples/fbr_samples/binary_encoding/TRACT_test.fbr')
current_fbr.read()
print(current_fbr)

streamlines = []
data_per_point = {'colors': []}

for group in current_fbr.groups:
    for fiber in group['fibers']:
        pts = np.array(fiber['points'])
        colors = np.array(fiber['colors'])
        if pts.shape[0] < 2:
            continue
        streamlines.append(pts)
        data_per_point['colors'].append(colors)

#TODO:
# Info sur les dimensions de l'image FBR
# Info sur les dimensions des voxels de l'image FBR
# Info sur l'ordre/l'orientation des voxels de l'image FBR (RAS, RAS+, LPS, ...)
# Donc info sur l'espace de référence utilisé pour l'image FBR
# Info sur (0,0,0) au centre d'un voxel ou dans le coin (TRK c'est dans le coin d'un voxel)
# Ensuite estimer la transformation affine pour passer de l'espace des voxels de l'image FBR à l'espace RASMM (affine_to_rasmm)

affine_to_rasmm = np.array([[1, 0, 0, 0],
                            [0, 1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])

# le tracto composé des streamlines
trk_tracto = Tractogram(streamlines=streamlines, data_per_point=data_per_point, affine_to_rasmm=affine_to_rasmm)

# --- Step 2. Extract volume size, voxel size, and origin ---
x_resolution = current_fbr.fibers_origin[0]*2  # |
y_resolution = current_fbr.fibers_origin[1]*2  # |---> BV considère l'origine comme étant le centre du volume
z_resolution = current_fbr.fibers_origin[2]*2  # |

voxel_size = [1.0, 1.0, 1.0] # à trouver

# --- Step 3. Create the trk header dictionary ---
trk_header = {
    'magic_number': b'TRACK',
    'dimensions': np.array([x_resolution, y_resolution, z_resolution], dtype=np.int16),
    'voxel_sizes': np.array(voxel_size, dtype=np.float32),
    'origin': np.array(current_fbr.fibers_origin, dtype=np.float32),
    'nb_scalars_per_point': 0,
    'scalar_name': np.array([b'', b'', b'', b'', b'', b'', b'', b'', b'', b''], dtype='|S20'),
    'nb_properties_per_streamline': 0,
    'property_name': np.array([b'', b'', b'', b'', b'', b'', b'', b'', b'', b''], dtype='|S20'),
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
    'nb_streamlines': current_fbr.num_fibers,
    'version': 2,
    'hdr_size': 1000
}

new_trk = TrkFile(tractogram=trk_tracto, header=trk_header)
print(new_trk.header)
new_trk.save('/Users/mhalleux/Library/CloudStorage/Dropbox/Mac/Documents/UCL/Master2_Q2/TFE/TFE_repo/output/FBR_conversion_test.trk')


"""
# --- Step 2. Extract streamlines ---
# The FBR file structure (as provided) contains one or more groups,
# each with a list of fibers. Each fiber has a list of (x,y,z) points.
streamlines = []
for group in fbr_reader.groups:
    for fiber in group['fibers']:
        pts = np.array(fiber['points'])
        # Skip fibers that do not have at least 2 points.
        #if pts.shape[0] < 2:
        #    continue
        streamlines.append(pts)
print(f"Found {len(streamlines)} streamlines in the FBR file.\n")


# --- Step 3. Create a nibabel Tractogram ---
# Set up an affine transformation.
# Since the FBR file saves coordinates offset by 128 (see FBR new file code),
# you might want to subtract 128 so that the coordinates are in a standard space.
# For example, an affine that subtracts 128 in x,y,z:
#affine = np.eye(4)
#affine[:3, 3] = -128

# Alternatively, if you wish to keep the coordinates as saved,
# use the identity:
affine = np.eye(4)

# Create the tractogram. (You can also add per-streamline or per-point data if needed.)
tractogram = Tractogram(streamlines, affine_to_rasmm=affine)

# --- Step 4. Save the tractogram to a TRK file ---
nib.streamlines.save(tractogram, '/Users/mhalleux/Library/CloudStorage/Dropbox/Mac/Documents/UCL/Master2_Q2/TFE/TFE_repo/output/conversionFBR.trk')


trkFile_instance = trk.TrkFile(tractogram)
print(trkFile_instance.is_correct_format('/Users/mhalleux/Library/CloudStorage/Dropbox/Mac/Documents/UCL/Master2_Q2/TFE/TFE_repo/output/conversionFBR.trk'))
print(trkFile_instance.header)

print(TrkFile._read_header('/Users/mhalleux/Library/CloudStorage/Dropbox/Mac/Documents/UCL/Master2_Q2/TFE/TFE_repo/trk_samples/NT1_cc_ant_midbody_cc_center.trk'))
print(TrkFile._read_header('/Users/mhalleux/Library/CloudStorage/Dropbox/Mac/Documents/UCL/Master2_Q2/TFE/TFE_repo/trk_samples/C3B1_cl_left.trk'))
print(TrkFile._read_header('/Users/mhalleux/Library/CloudStorage/Dropbox/Mac/Documents/UCL/Master2_Q2/TFE/TFE_repo/trk_samples/NT1_cc_isthmus_cc_center.trk'))
print(TrkFile._read_header('/Users/mhalleux/Library/CloudStorage/Dropbox/Mac/Documents/UCL/Master2_Q2/TFE/TFE_repo/trk_samples/NT1_cc_splenium_cc_center.trk'))
"""
