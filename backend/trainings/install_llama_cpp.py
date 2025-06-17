#!/usr/bin/env python3
"""
Script d'installation de llama-cpp-python avec support CUDA.

Ce script installe llama-cpp-python avec les options appropriées pour le support CUDA.
Il doit être exécuté avant de lancer le fine-tuning si vous utilisez des modèles GGUF.
"""

import os
import sys
import subprocess
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("install_llama_cpp")

def check_gpu_available():
    """Vérifie si un GPU est disponible."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            return len(gpus) > 0
        except ImportError:
            return False

def install_llama_cpp():
    """Installe llama-cpp-python avec support CUDA si disponible."""
    log.info("Vérification de la disponibilité du GPU...")
    gpu_available = check_gpu_available()
    
    # Vérifier si llama-cpp-python est déjà installé
    try:
        import llama_cpp
        log.info(f"llama-cpp-python est déjà installé (version: {llama_cpp.__version__})")
        
        # Vérifier si la version installée a le support CUDA
        if gpu_available:
            try:
                # Tenter de créer un modèle avec n_gpu_layers pour vérifier le support CUDA
                # Cela échouera silencieusement si le support CUDA n'est pas disponible
                test_model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_model.bin")
                with open(test_model_path, "wb") as f:
                    f.write(b"test")  # Fichier factice
                
                try:
                    llama_cpp.Llama(model_path=test_model_path, n_gpu_layers=1)
                    log.info("Le support CUDA semble être activé dans l'installation existante.")
                    os.remove(test_model_path)
                    return True
                except Exception:
                    log.warning("L'installation existante ne semble pas avoir le support CUDA. Réinstallation...")
                    os.remove(test_model_path)
                    # Continuer avec la réinstallation
            except Exception as e:
                log.warning(f"Impossible de vérifier le support CUDA: {e}. Réinstallation...")
        else:
            # Si pas de GPU, pas besoin de réinstaller
            return True
    except ImportError:
        log.info("llama-cpp-python n'est pas installé. Installation en cours...")
    
    if gpu_available:
        log.info("GPU détecté. Installation de llama-cpp-python avec support CUDA...")
        os.environ["CMAKE_ARGS"] = "-DLLAMA_CUBLAS=on"
        os.environ["FORCE_CMAKE"] = "1"
    else:
        log.info("Aucun GPU détecté. Installation de llama-cpp-python sans support CUDA...")
    
    try:
        # Désinstaller d'abord si déjà installé
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "llama-cpp-python"])
            log.info("Version précédente de llama-cpp-python désinstallée.")
        except:
            pass
        
        log.info("Installation de llama-cpp-python...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir", "llama-cpp-python==0.2.26"])
        log.info("llama-cpp-python installé avec succès!")
        
        # Vérifier l'installation
        import importlib
        if 'llama_cpp' in sys.modules:
            importlib.reload(sys.modules['llama_cpp'])
        else:
            import llama_cpp
        
        log.info(f"Version de llama-cpp-python installée: {llama_cpp.__version__}")
        return True
    except Exception as e:
        log.error(f"Erreur lors de l'installation de llama-cpp-python: {e}")
        return False

if __name__ == "__main__":
    log.info("Démarrage de l'installation de llama-cpp-python...")
    success = install_llama_cpp()
    
    if success:
        log.info("Installation réussie. Vous pouvez maintenant exécuter le script de fine-tuning.")
        sys.exit(0)
    else:
        log.error("L'installation a échoué. Veuillez consulter les logs pour plus de détails.")
        sys.exit(1)
