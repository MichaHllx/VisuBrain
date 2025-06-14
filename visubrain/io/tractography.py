"""
visubrain/io/tractography.py

Module for loading and managing tractography (streamlines) data in the VisuBrain application.

Provides the Tractography class for reading tractography files (TRK, TCK, FBR), handling
streamline transformation, color mapping, and integration with NIfTI anatomical references.
Supports visualization, session-based management, and statistics within VisuBrain.

Classes:
    Tractography: Handles loading, transformation, and querying of tractography data.
"""


import numpy as np

from dipy.io.streamline import load_tractogram
from dipy.tracking.streamline import transform_streamlines


class Tractography:
    """
    Class to load, manage and process tractography streamlines (.trk/.tck files).

    Attributes:
        file_path (str): Path to the tractography file.
        reference_nifti: Reference NIfTI object for registration (required for .tck).
        streamlines: List of streamlines in voxel/image space.
        sf_t: Raw tractogram object loaded by DIPY.
        session_id: Identifier for the session this tractography belongs to.
    """

    def __init__(self, file_path: str, session_id, reference_nifti=None):
        """
        Initialize the Tractography object and load the streamlines.

        Args:
            file_path (str): Path to the tractography file (.trk or .tck).
            session_id: Session identifier for UI management.
            reference_nifti: NIfTI reference object, required for .tck files.
        """
        self.file_path = file_path
        self.reference_nifti = reference_nifti
        self.streamlines, self.sf_t = self._load_streamlines()
        self.session_id = session_id

    def _load_streamlines(self):
        """
        Load streamlines from .trk or .tck files using DIPY.

        Returns:
            tuple: (streamlines, raw tractogram object)

        Raises:
            ValueError: If a .tck file is provided without a reference NIfTI.
            ValueError: On loading error.
        """
        try:
            if self.file_path.endswith(".tck"):
                if not self.reference_nifti:
                    raise ValueError("A tck file needs an anatomical reference image beforehand.")
                sf_tracto = load_tractogram(filename=self.file_path,
                                            reference=self.reference_nifti.file_path)
            else:
                sf_tracto = load_tractogram(filename=self.file_path, reference='same')
        except Exception as e:
            raise ValueError(f"Error while loading streamlines: {e}") from e

        if self.reference_nifti is not None:
            affine = self.reference_nifti.affine
            # World streamlines coord RAS+mm -> voxel nifti image space
            stream_reg = transform_streamlines(sf_tracto.streamlines, np.linalg.inv(affine))
            return stream_reg, sf_tracto

        return sf_tracto.streamlines, sf_tracto

    def get_streamlines(self):
        """
        Get all streamlines in RAS+mm space.

        Returns:
            list: List of streamlines.
        """
        return self.streamlines

    def get_color_points(self, show_points: bool, streamlines):
        """
        Compute color mapping for each streamline point, using local tangent.

        Args:
            show_points (bool): If True, display as points (for 3D viewer). (not used here)
            streamlines : Points coordinates to be color associated

        Returns:
            tuple: (points_list, colors_list, connectivity)

        Notes:
            - Red = X axis
            - Green = Y axis
            - Blue = Z axis
        """
        points_list = []
        colors_list = []
        connectivity = []  # for line display
        offset = 0

        for streamline in streamlines:
            streamline = np.asarray(streamline)
            n_points = streamline.shape[0]

            if n_points < 2:
                colors = np.tile(np.array([255, 255, 255], dtype=np.uint8), (n_points, 1))
            else:
                diffs = np.diff(streamline, axis=0) # compute tangent for each point
                diffs = np.vstack([diffs, diffs[-1]]) # repeat last to keep size
                norms = np.linalg.norm(diffs, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                tangents = diffs / norms
                colors = (np.abs(tangents) * 255).astype(np.uint8)

            points_list.append(streamline)
            colors_list.append(colors)

            # build connectivity for this streamline (for lines display)
            if not show_points:
                cell = np.hstack(([n_points], np.arange(offset, offset + n_points)))
                connectivity.append(cell)

            offset += n_points

        return points_list, colors_list, connectivity