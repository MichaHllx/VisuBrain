# visubrain/io/fbr.py

import struct

class BinaryFbrFile:

    def __init__(self, fbr_file=None):
        self._fbr_file = fbr_file
        self._magic = None
        self._file_version = None
        self._coords_type = None
        self.fibers_origin = None
        self._num_groups = None
        self.num_fibers = None
        self.groups = []
        if fbr_file is not None:
            self._read()

    def _read(self):
        with open(self._fbr_file, 'rb') as f:
            # Lire et vérifier les octets magiques
            self._magic = f.read(4)
            if self._magic != b'\xa4\xd3\xc2\xb1':
                raise ValueError("Fichier FBR invalide : octets magiques incorrects")

            # Lire les champs header
            self._file_version = struct.unpack('<I', f.read(4))[0]
            self._coords_type = struct.unpack('<I', f.read(4))[0]
            self.fibers_origin = struct.unpack('<3f', f.read(12))
            self._num_groups = struct.unpack('<I', f.read(4))[0]

            # Lire les groupes
            for _ in range(self._num_groups):
                group = {}
                # Lire le nom du groupe (! fin avec un caractère nul !)
                group_name = bytearray()
                while True:
                    char = f.read(1)
                    if char == b'\x00':
                        break
                    group_name += char
                group['name'] = group_name.decode('latin-1')

                # Lire les propriétés du groupe
                group['visible'] = struct.unpack('<I', f.read(4))[0]
                group['animate'] = struct.unpack('<i', f.read(4))[0]
                group['thickness'] = struct.unpack('<f', f.read(4))[0]
                group['color'] = struct.unpack('<3B', f.read(3))
                num_fibers = struct.unpack('<I', f.read(4))[0]
                self.num_fibers = num_fibers

                fibers = []
                for _ in range(num_fibers):
                    fiber = {}
                    num_points = struct.unpack('<I', f.read(4))[0]

                    # Lire les points de la fibre (coordonnées)
                    points_data = struct.unpack(f'<{3 * num_points}f', f.read(12 * num_points))
                    x_coords = points_data[:num_points]
                    y_coords = points_data[num_points:2 * num_points]
                    z_coords = points_data[2 * num_points:]
                    fiber['points'] = list(zip(x_coords, y_coords, z_coords))

                    # Lire les couleurs des points (RGB)
                    colors_data = struct.unpack(f'<{3 * num_points}B', f.read(3 * num_points))
                    r_values = colors_data[:num_points]
                    g_values = colors_data[num_points:2 * num_points]
                    b_values = colors_data[2 * num_points:]
                    fiber['colors'] = list(zip(r_values, g_values, b_values))
                    fibers.append(fiber)
                group['fibers'] = fibers
                self.groups.append(group)

    @staticmethod
    def write_fbr(output_fbr_file_path, header, fibers):
        with open(output_fbr_file_path, 'wb') as f:
            # Écrire les octets magiques
            f.write(b'\xa4\xd3\xc2\xb1')

            # Écrire le header
            f.write(struct.pack('<I', header['FileVersion']))
            f.write(struct.pack('<I', header['CoordsType']))
            f.write(struct.pack('<3f', *header['FibersOrigin'])) # l'astérisque permet de "décompacter" la liste
            f.write(struct.pack('<I', header['NrOfGroups']))

            # Écrire les groupes et les fibres
            for group in header['Groups']:
                # Écrire le nom du groupe (caractère nul à la fin !)
                f.write(group['Name'].encode('latin-1') + b'\x00')

                # Écrire les propriétés du groupe
                f.write(struct.pack('<I', group['Visible']))
                f.write(struct.pack('<i', group['Animate']))
                f.write(struct.pack('<f', group['Thickness']))
                f.write(struct.pack('<3B', *group['Color']))
                f.write(struct.pack('<I', group['NrOfFibers']))

                # pour respecter format fbr binaire, obligation d'écrire tous les x puis tous les y puis tous les z, etc
                for fiber in fibers:
                    f.write(struct.pack('<I', fiber['NrOfPoints']))

                    # toutes les coordonnées X
                    f.write(struct.pack(f'<{fiber["NrOfPoints"]}f', *(point[0] for point in fiber['Points'])))

                    # toutes les coordonnées Y
                    f.write(struct.pack(f'<{fiber["NrOfPoints"]}f', *(point[1] for point in fiber['Points'])))

                    # toutes les coordonnées Z
                    f.write(struct.pack(f'<{fiber["NrOfPoints"]}f', *(point[2] for point in fiber['Points'])))

                    # toutes les couleurs R
                    f.write(struct.pack(f'<{fiber["NrOfPoints"]}B', *(point[3] for point in fiber['Points'])))

                    # toutes les couleurs G
                    f.write(struct.pack(f'<{fiber["NrOfPoints"]}B', *(point[4] for point in fiber['Points'])))

                    # toutes les couleurs B
                    f.write(struct.pack(f'<{fiber["NrOfPoints"]}B', *(point[5] for point in fiber['Points'])))

    def get_fiber_coordinates(self):
        coordinates = []
        for group in self.groups:
            for fiber in group['fibers']:
                coordinates.append(fiber['points'])
        return coordinates

    def get_header(self):
        dico =  {
            'FBRFile' : self._fbr_file,
            'Animate' : ','.join([str(g['animate']) for g in self.groups]),
            'Color' : ','.join([str(g['color']) for g in self.groups]),
            'CoordsType' : self._coords_type,
            'FibersOrigin' : self.fibers_origin,
            'FileVersion' : self._file_version,
            'Name' : ','.join([g['name'] for g in self.groups]),
            'NrOfFibers' : ','.join([str(len(g['fibers'])) for g in self.groups]),
            'NrOfGroups' : len(self.groups),
            'Thickness' : ','.join([str(g['thickness']) for g in self.groups]),
            'Visible' : ','.join([str(g['visible']) for g in self.groups])
        }
        return dico.__str__()
