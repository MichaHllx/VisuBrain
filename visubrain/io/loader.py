# visubrain/io/loader.py
from PyQt6.QtWidgets import QMessageBox
from visubrain.io.nifti import NiftiFile
from visubrain.io.tractography import TractographyFile


def load_nifti(file_path: str) -> NiftiFile | None:
    try:
        return NiftiFile(file_path)
    except Exception as e:
        QMessageBox.critical(None, "Erreur", f"Erreur lors du chargement du NIfTI: {e}")
        return None

def load_tractography(file_path: str, nifti_ref=None) -> TractographyFile | None:
    try:
        return TractographyFile(file_path, reference_nifti=nifti_ref)
    except Exception as e:
        QMessageBox.critical(None, "Erreur", f"Erreur lors du chargement de la tractographie: {e}")
        return None