"""
visubrain/utils/session.py

Module for session management in the VisuBrain application.

Defines the Session class for managing user sessions, including loaded anatomical volumes,
tractography data, visualization state, and statistics. Supports multi-session workflows,
display parameter saving/restoration, and tractography reporting.

Classes:
    Session: Represents a VisuBrain session, storing data, display state, and content.
"""


from pathlib import Path
import numpy as np


class Session:
    """
    Class representing a session of visualization and data, including loaded volume, display state,
     and tractographies.

    Attributes:
        display_name (str): Display name of the session.
        volume_obj: Reference to the loaded NIfTI volume object.
        viewer: The viewer object controlling display.
        slice_positions (dict): Slice positions per orientation.
        opacity (float): Current opacity for visualization.
        zoom_factor (float): Zoom factor for the viewer.
        background_color (str): Current background color.
        rendering_mode (str): Rendering mode ("Slices", "Volume 3D", etc).
        tracts (dict): Loaded tractography objects.
    """
    _id_counter = 0

    def __init__(self, display_name, volume_obj, viewer):
        """
        Initialize the session with volume, viewer, and display parameters.

        Args:
            display_name (str): Name for the session.
            volume_obj: Loaded NIfTI object for anatomical volume.
            viewer: The viewer object for visualization.
        """
        self._id = Session._id_counter
        Session._id_counter += 1
        self.display_name = display_name
        self.volume_obj = volume_obj
        self.viewer = viewer

        if volume_obj is not None:
            # For visualization: initialize slice positions to middle of each axis
            self.slice_positions = {'axial': volume_obj.get_dimensions()[2] // 2,
                                    'coronal': volume_obj.get_dimensions()[1] // 2,
                                    'sagittal': volume_obj.get_dimensions()[0] // 2}
        self.opacity = 0.5
        self.zoom_factor = 1.0
        self.background_color = "white"
        self.rendering_mode = "Slices"

        # Content management
        self.tracts = {}    # {file_path: tracto_obj}

    def add_tract(self, tracto_obj):
        """
        Add a tractography object to the session.

        Args:
            tracto_obj: Tractography object to add.
        """
        self.tracts[tracto_obj.file_path] = tracto_obj

    def get_uid(self):
        """
        Get the unique identifier of the session.

        Returns:
            int: Unique session ID.
        """
        return self._id

    def apply(self):
        """
        Apply the session parameters and data to the viewer.

        Updates the viewer's state to reflect this session's data
        (volume, tracts, display settings).
        """
        v = self.viewer
        if self.volume_obj is not None:
            v.set_working_nifti_obj(self.volume_obj)
            v.render_mode(self.rendering_mode, self.opacity)

        for tract in self.tracts.values():
            v.show_tractogram(tract, show_points=False)

    def tract_statistics(self):
        """
        Compute and return statistics for each tractography in the session.

        Returns:
            list: List of formatted strings with statistics per tractography.
        """
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
