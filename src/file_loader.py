from nifti_file import NiftiFile
from tractography_file import TractographyFile
from PyQt6.QtWidgets import QMessageBox

class FileLoader:
    def __init__(self):
        pass

    def load_nifti(self, file_path: str) -> NiftiFile | None:
        try:
            nifti_obj = NiftiFile(file_path)
            return nifti_obj
        except Exception as e:
            QMessageBox.critical(None, "Erreur", f"Erreur lors du chargement du NIfTI: {e}")
            return None

    def load_tractography(self, file_path: str, nifti_ref: NiftiFile = None) -> TractographyFile | None:
        try:
            tracto_obj = TractographyFile(file_path, reference_nifti=nifti_ref)
            return tracto_obj
        except Exception as e:
            QMessageBox.critical(None, "Erreur", f"Erreur lors du chargement de la tractographie: {e}")
            return None
