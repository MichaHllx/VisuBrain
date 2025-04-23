import numpy as np

from PyQt6.QtWidgets import QMessageBox
from dipy.io.streamline import load_tractogram
from dipy.tracking.streamline import transform_streamlines


class TractographyFile:

    def __init__(self, file_path: str, reference_nifti=None):
        self.file_path = file_path
        self.reference_nifti = reference_nifti
        self.streamlines, self.raw_data = self._load_streamlines()

    def _load_streamlines(self):
        if self.file_path.endswith(".tck"):
            if not self.reference_nifti:
                QMessageBox.critical(None, "Error", "A tck file needs an anatomical reference image beforehand.")
                return
            tracto = load_tractogram(self.file_path, self.reference_nifti.file_path)
        else:
            tracto = load_tractogram(self.file_path, 'same')

        if self.reference_nifti is not None:
            # passage de l'espace image à l'espace RASmm du fichier anat
            affine = self.reference_nifti.affine
            stream_reg = transform_streamlines(tracto.streamlines, np.linalg.inv(affine))
            return stream_reg, tracto

        return tracto.streamlines, tracto

    def get_streamlines(self):
        return self.streamlines

    def get_color_points(self, show_points: bool):
        """
          - Red = axe X
          - Green = axe Y
          - Blue = axe Z
        """
        points_list = []
        colors_list = []
        connectivity = []  # (pour l'affichage des lignes)
        offset = 0

        for streamline in self.streamlines:
            streamline = np.asarray(streamline)
            n_points = streamline.shape[0]

            if n_points < 2:
                colors = np.tile(np.array([255, 255, 255], dtype=np.uint8), (n_points, 1))
            else:
                diffs = np.diff(streamline, axis=0) # calcul tangente de chaque point (dérivée)
                diffs = np.vstack([diffs, diffs[-1]]) # répéter dernière pour garder la mm size
                norms = np.linalg.norm(diffs, axis=1, keepdims=True) # normalise le vecteur (size=1)
                norms[norms == 0] = 1.0
                tangents = diffs / norms
                colors = (np.abs(tangents) * 255).astype(np.uint8)

            points_list.append(streamline)
            colors_list.append(colors)

            # construction de la connectivité pour cette streamline
            if not show_points:
                cell = np.hstack(([n_points], np.arange(offset, offset + n_points)))
                connectivity.append(cell)

            offset += n_points

        return points_list, colors_list, connectivity
