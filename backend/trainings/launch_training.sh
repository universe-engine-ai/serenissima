#!/bin/bash
# Script optimisé pour lancer le fine-tuning du modèle de conscience marchande

# Configuration GPU
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

# Créer un répertoire de logs
LOGS_DIR="./logs"
mkdir -p "$LOGS_DIR"
LOG_FILE="$LOGS_DIR/training_$(date +%Y%m%d_%H%M%S).log"

echo "Démarrage du fine-tuning. Les logs seront enregistrés dans $LOG_FILE"

# Installer llama-cpp-python (nécessaire pour les modèles GGUF)
echo "Installation de llama-cpp-python avec support CUDA..."
python install_llama_cpp.py

# Vérifier si l'installation a réussi
if [ $? -ne 0 ]; then
    echo "Erreur lors de l'installation de llama-cpp-python. Arrêt du script."
    exit 1
fi

# Générer d'abord le dataset JSONL
echo "Génération du dataset JSONL pour le fine-tuning..."
python prepareDataset.py --jsonl-only

# Paramètres optimisés pour ~2000 exemples avec le modèle GGUF spécifié
python finetuneModel.py \
    --model "C:/Users/reyno/.cache/lm-studio/models/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF/DeepSeek-R1-0528-Qwen3-8B-Q6_K.gguf" \
    --epochs 3 \
    --batch_size 2 \
    --output_dir "./merchant-consciousness-v1" \
    --quantization 8bit \
    --use_wandb 2>&1 | tee "$LOG_FILE"

# Vérifier si l'exécution a réussi
if [ $? -eq 0 ]; then
    echo "Fine-tuning terminé avec succès!"
else
    echo "Erreur lors du fine-tuning. Consultez les logs pour plus de détails."
    exit 1
fi

# Test post-training (décommenter si un script de test existe)
# python test_consciousness.py \
#     --model_path "./merchant-consciousness-v1" \
#     --comprehensive_test
