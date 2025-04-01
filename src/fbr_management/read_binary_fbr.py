# import struct
#
# class BinaryFBRfile:
#     def __init__(self, filename):
#         self.filename = filename
#         self.magic = None
#         self.file_version = None
#         self.coords_type = None
#         self.fibers_origin = None
#         self.num_fibers = None
#         self.groups = []
#
#     def read(self):
#         with open(self.filename, 'rb') as f:
#             # Lire et vérifier les octets magiques
#             self.magic = f.read(4)
#             if self.magic != b'\xa4\xd3\xc2\xb1':
#                 raise ValueError("Fichier FBR invalide : octets magiques incorrects")
#
#             # Lire les champs d'en-tête
#             self.file_version = struct.unpack('<I', f.read(4))[0]
#             self.coords_type = struct.unpack('<I', f.read(4))[0]
#             self.fibers_origin = struct.unpack('<3f', f.read(12))
#             self.num_groups = struct.unpack('<I', f.read(4))[0]
#
#             # Lire les groupes
#             for _ in range(self.num_groups):
#                 group = {}
#                 # Lire le nom du groupe (chaîne terminée par un caractère nul)
#                 group_name = bytearray()
#                 while True:
#                     char = f.read(1)
#                     if char == b'\x00':
#                         break
#                     group_name += char
#                 group['name'] = group_name.decode('latin-1')
#
#                 # Lire les propriétés du groupe
#                 group['visible'] = struct.unpack('<I', f.read(4))[0]
#                 group['animate'] = struct.unpack('<i', f.read(4))[0]
#                 group['thickness'] = struct.unpack('<f', f.read(4))[0]
#                 group['color'] = struct.unpack('<3B', f.read(3))
#                 num_fibers = struct.unpack('<I', f.read(4))[0]
#                 self.num_fibers = num_fibers
#
#                 fibers = []
#                 for _ in range(num_fibers):
#                     fiber = {}
#                     num_points = struct.unpack('<I', f.read(4))[0]
#
#                     # Lire les points de la fibre (coordonnées)
#                     points_data = struct.unpack(f'<{3 * num_points}f', f.read(12 * num_points))
#                     x_coords = points_data[:num_points]
#                     y_coords = points_data[num_points:2 * num_points]
#                     z_coords = points_data[2 * num_points:]
#                     fiber['points'] = list(zip(x_coords, y_coords, z_coords))
#
#                     # Lire les couleurs des points (RGB)
#                     colors_data = struct.unpack(f'<{3 * num_points}B', f.read(3 * num_points))
#                     r_values = colors_data[:num_points]
#                     g_values = colors_data[num_points:2 * num_points]
#                     b_values = colors_data[2 * num_points:]
#                     fiber['colors'] = list(zip(r_values, g_values, b_values))
#                     fibers.append(fiber)
#                 group['fibers'] = fibers
#                 self.groups.append(group)
#
#         return self
#
#     def get_fiber_coordinates(self):
#         coordinates = []
#         for group in self.groups:
#             for fiber in group['fibers']:
#                 coordinates.append(fiber['points'])
#         return coordinates
#
#     def header(self):
#         dico =  {
#             'FBRFile' : self.filename,
#             'Animate' : ','.join([str(g['animate']) for g in self.groups]),
#             'Color' : ','.join([str(g['color']) for g in self.groups]),
#             'CoordsType' : self.coords_type,
#             'FibersOrigin' : self.fibers_origin,
#             'FileVersion' : self.file_version,
#             'Name' : ','.join([g['name'] for g in self.groups]),
#             'NrOfFibers' : ','.join([str(len(g['fibers'])) for g in self.groups]),
#             'NrOfGroups' : len(self.groups),
#             'Thickness' : ','.join([str(g['thickness']) for g in self.groups]),
#             'Visible' : ','.join([str(g['visible']) for g in self.groups])
#         }
#         return dico.__str__()
#                 # "\n"
#                 # f"num_points={','.join([str(sum([len(f['points']) for f in g['fibers']])) for g in self.groups])}\n"
#                 # f"#points_by_fiber={','.join([str([len(f['points']) for f in g['fibers']]) for g in self.groups])}\n"
#                 # f"points_coord={','.join([str([f['points'] for f in g['fibers']]) for g in self.groups])}\n")
