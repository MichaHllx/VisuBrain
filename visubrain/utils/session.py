# visubrain/utils/session.py
from pathlib import Path

import numpy as np


class Session:
    _id_counter = 0

    def __init__(self, display_name, volume_obj, viewer):
        self._id = Session._id_counter
        Session._id_counter += 1
        self.display_name = display_name
        self.volume_obj = volume_obj
        self.viewer = viewer

        if volume_obj is not None:
            # pour la visu
            self.slice_positions = {'axial': volume_obj.get_dimensions()[2] // 2,
                                    'coronal': volume_obj.get_dimensions()[1] // 2,
                                    'sagittal': volume_obj.get_dimensions()[0] // 2}
        self.opacity = 0.5
        self.zoom_factor = 1.0
        self.background_color = "white"
        self.rendering_mode = "Slices"

        # pour le content
        self.tracts = {}    # {file_path: tracto_obj}
        # self.rois = {}      # {file_path: roi_obj}

    def add_tract(self, tracto_obj):
        self.tracts[tracto_obj.file_path] = tracto_obj

    # def add_roi(self, roi_obj):
    #     self.rois[roi_obj.file_path] = roi_obj

    def get_uid(self):
        return self._id

    def apply(self):
        v = self.viewer
        if self.volume_obj is not None:
            v.set_working_nifti_obj(self.volume_obj)
            v.render_mode(self.rendering_mode, self.opacity)

        for tract in self.tracts.values():
            v.show_tractogram(tract, show_points=False)

    def tract_statistics(self):
        report_lines = []
        for name, tracto_obj in self.tracts.items():
            slines = tracto_obj.get_streamlines()
            n_streams = len(slines)
            lengths = []
            for sl in slines:
                pts = np.asarray(sl)
                if pts.shape[0] < 2:
                    continue
                diffs = np.diff(pts, axis=0)
                lengths.append(np.linalg.norm(diffs, axis=1).sum())
            mean_len = np.mean(lengths) if lengths else 0.0
            total_len = np.sum(lengths)
            report_lines.append(
                f"{Path(name).name}\n"
                f"  • Number of streamlines: {n_streams}\n"
                f"  • Mean length: {mean_len:.1f}mm\n"
                f"  • Total length: {total_len:.1f}mm\n"
            )

        return report_lines