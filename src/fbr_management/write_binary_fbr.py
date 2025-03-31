import struct

def write_fbr(filename, header, fibers):
    with open(filename, 'wb') as f:
        # Écrire les octets magiques
        f.write(b'\xa4\xd3\xc2\xb1')

        # Écrire les champs d'en-tête
        f.write(struct.pack('<I', header['FileVersion']))
        f.write(struct.pack('<I', header['CoordsType']))
        f.write(struct.pack('<3f', *header['FibersOrigin'])) # l'astérisque permet de "décompacter" la liste
        f.write(struct.pack('<I', header['NrOfGroups']))

        # Écrire les groupes et les fibres
        for group in header['Groups']:
            # Écrire le nom du groupe (chaîne terminée par un caractère nul)
            f.write(group['Name'].encode('latin-1') + b'\x00')

            # Écrire les propriétés du groupe
            f.write(struct.pack('<I', group['Visible']))
            f.write(struct.pack('<i', group['Animate']))
            f.write(struct.pack('<f', group['Thickness']))
            f.write(struct.pack('<3B', *group['Color']))
            f.write(struct.pack('<I', group['NrOfFibers']))

            # par respect du format fbr binaire, obligation d'écrire tous les x puis tous les y puis tous les z, etc
            for fiber in fibers:
                f.write(struct.pack('<I', fiber['NrOfPoints']))

                # Écrire toutes les coordonnées X en une seule fois
                f.write(struct.pack(f'<{fiber["NrOfPoints"]}f', *(point[0] for point in fiber['Points'])))

                # Écrire toutes les coordonnées Y en une seule fois
                f.write(struct.pack(f'<{fiber["NrOfPoints"]}f', *(point[1] for point in fiber['Points'])))

                # Écrire toutes les coordonnées Z en une seule fois
                f.write(struct.pack(f'<{fiber["NrOfPoints"]}f', *(point[2] for point in fiber['Points'])))

                # Écrire toutes les couleurs R en une seule fois
                f.write(struct.pack(f'<{fiber["NrOfPoints"]}B', *(point[3] for point in fiber['Points'])))

                # Écrire toutes les couleurs G en une seule fois
                f.write(struct.pack(f'<{fiber["NrOfPoints"]}B', *(point[4] for point in fiber['Points'])))

                # Écrire toutes les couleurs B en une seule fois
                f.write(struct.pack(f'<{fiber["NrOfPoints"]}B', *(point[5] for point in fiber['Points'])))


# # Exemple d'utilisation
# header = {
#     'FileVersion': 5,
#     'CoordsType': 2,
#     'FibersOrigin': [128.0, 128.0, 128.0],
#     'NrOfGroups': 1,
#     'Groups': [
#         {
#             'Name': 'default',
#             'Visible': 1,
#             'Animate': 0,
#             'Thickness': 0.3,
#             'Color': [64, 64, 192],
#             'NrOfFibers': 2
#         }
#     ]
# }
#
# fibers = [
#     {
#         'NrOfPoints': 4,
#         'Points': [
#             [1.0, 2.0, 3.0, 255, 0, 0], # [x, y, z, R, G, B]
#             [4.0, 5.0, 6.0, 0, 255, 0],
#             [7.0, 8.0, 9.0, 0, 0, 255],
#             [10.0, 11.0, 12.0, 8, 8, 8]
#         ]
#     },
#     {
#         'NrOfPoints': 3,
#         'Points': [
#             [1.0, 2.0, 15.0, 25, 0, 0],  # [x, y, z, R, G, B]
#             [4.0, 5.0, 16.0, 0, 25, 0],
#             [7.0, 8.0, 17.0, 0, 0, 25]
#         ]
#     }
# ]
#
# write_fbr('/Users/mhalleux/Library/CloudStorage/Dropbox/Mac/Documents/UCL/Master2_Q2/TFE/TFE_repo/output/example_fbr_writing.fbr', header, fibers)