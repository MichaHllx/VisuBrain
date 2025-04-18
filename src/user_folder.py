
class UserFolder:
    def __init__(self, working_nifti_obj):
        self._working_nifti_obj = working_nifti_obj
        self._tracts = []
        self._rois = []

    def get_nifti_obj(self):
        return self._working_nifti_obj

    def get_tracts(self):
        return self._tracts

    def get_rois(self):
        return self._rois
