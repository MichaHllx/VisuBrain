"""
visubrain/io/fbr.py

Module for reading and writing custom FBR (fiber) binary files in the VisuBrain application.

Provides the BinaryFbrFile class for parsing, loading and exporting tractography data
stored in the FBR file format, including fiber group information, coordinates, and colors.
Supports integration with VisuBrain's visualization and session management.

Classes:
    BinaryFbrFile: Handles parsing and exporting of FBR tractography files.
"""


import struct

class BinaryFbrFile:
    """
    Class for reading and writing custom FBR (fiber) binary files.

    Handles parsing, reading and writing FBR files containing tractography/fiber data,
    including fibers groups, coordinates and colors.
    """

    def __init__(self, fbr_file=None):
        """
        Initialize the BinaryFbrFile class and optionally read an FBR file.

        Args:
            fbr_file (str, optional): Path to the FBR file to load.
        """
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
        """
        Read and parse the FBR binary file and populate object attributes.

        Raises:
            ValueError: If file is invalid or does not start with the expected magic bytes.
        """
        with open(self._fbr_file, 'rb') as f:
            # Read and check the magic bytes
            self._magic = f.read(4)
            if self._magic != b'\xa4\xd3\xc2\xb1':
                raise ValueError("Invalid FBR file: incorrect magic bytes")

            # Read header fields
            self._file_version = struct.unpack('<I', f.read(4))[0]
            self._coords_type = struct.unpack('<I', f.read(4))[0]
            self.fibers_origin = struct.unpack('<3f', f.read(12))
            self._num_groups = struct.unpack('<I', f.read(4))[0]

            # Read groups
            for _ in range(self._num_groups):
                group = {}
                # Read group name (null-terminated)
                group_name = bytearray()
                while True:
                    char = f.read(1)
                    if char == b'\x00':
                        break
                    group_name += char
                group['name'] = group_name.decode('latin-1')

                # Read group properties
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

                    # Read fiber points (coordinates)
                    points_data = struct.unpack(f'<{3 * num_points}f', f.read(12 * num_points))
                    x_coords = points_data[:num_points]
                    y_coords = points_data[num_points:2 * num_points]
                    z_coords = points_data[2 * num_points:]
                    fiber['points'] = list(zip(x_coords, y_coords, z_coords))

                    # Read fiber colors (RGB)
                    colors_data = struct.unpack(f'<{3 * num_points}B', f.read(3 * num_points))

                    fiber['colors'] = list(zip(colors_data[:num_points],
                                               colors_data[num_points:2 * num_points],
                                               colors_data[2 * num_points:]))
                    fibers.append(fiber)
                group['fibers'] = fibers
                self.groups.append(group)

    @staticmethod
    def write_fbr(output_fbr_file_path, header, fibers):
        """
        Write fiber data to a FBR binary file in the required format.

        Args:
            output_fbr_file_path (str): Output path for the FBR file.
            header (dict): Header dictionary describing file and group properties.
            fibers (list): List of fiber dictionaries (points and colors).
        """
        with open(output_fbr_file_path, 'wb') as f:
            # Write magic bytes
            f.write(b'\xa4\xd3\xc2\xb1')

            # Write header
            f.write(struct.pack('<I', header['FileVersion']))
            f.write(struct.pack('<I', header['CoordsType']))
            f.write(struct.pack('<3f', *header['FibersOrigin']))
            f.write(struct.pack('<I', header['NrOfGroups']))

            # Write groups and fibers
            for group in header['Groups']:
                # Write group name (null-terminated)
                f.write(group['Name'].encode('latin-1') + b'\x00')

                # Write group properties
                f.write(struct.pack('<I', group['Visible']))
                f.write(struct.pack('<i', group['Animate']))
                f.write(struct.pack('<f', group['Thickness']))
                f.write(struct.pack('<3B', *group['Color']))
                f.write(struct.pack('<I', group['NrOfFibers']))

                for fiber in fibers:
                    f.write(struct.pack('<I', fiber['NrOfPoints']))

                    # Write all X coordinates
                    f.write(struct.pack(f'<{fiber["NrOfPoints"]}f',
                                        *(point[0] for point in fiber['Points'])))

                    # Write all Y coordinates
                    f.write(struct.pack(f'<{fiber["NrOfPoints"]}f',
                                        *(point[1] for point in fiber['Points'])))

                    # Write all Z coordinates
                    f.write(struct.pack(f'<{fiber["NrOfPoints"]}f',
                                        *(point[2] for point in fiber['Points'])))

                    # Write all R colors
                    f.write(struct.pack(f'<{fiber["NrOfPoints"]}B',
                                        *(point[3] for point in fiber['Points'])))

                    # Write all G colors
                    f.write(struct.pack(f'<{fiber["NrOfPoints"]}B',
                                        *(point[4] for point in fiber['Points'])))

                    # Write all B colors
                    f.write(struct.pack(f'<{fiber["NrOfPoints"]}B',
                                        *(point[5] for point in fiber['Points'])))

    def get_fiber_coordinates(self):
        """
        Get a list of all fiber coordinates in all groups.

        Returns:
            list: List of lists of fiber coordinates for each group.
        """
        coordinates = []
        for group in self.groups:
            for fiber in group['fibers']:
                coordinates.append(fiber['points'])
        return coordinates

    def get_header(self):
        """
        Return a string describing the main header fields of the FBR file.

        Returns:
            str: Header summary.
        """
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
        return dico