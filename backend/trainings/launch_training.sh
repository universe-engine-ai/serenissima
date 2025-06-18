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

# Générer d'abord le dataset JSONL
echo "Génération du dataset JSONL pour le fine-tuning..."
python prepareDataset.py --jsonl-only

# Paramètres optimisés pour ~2000 exemples avec le modèle DeepSeek
python finetuneModel.py \
    --model "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B" \
    --epochs 3 \
    --batch_size 1 \
    --gradient_accumulation_steps 16 \
    --output_dir "./merchant-consciousness-v1" \
    --quantization none \
    --lora_r 8 \
    --lora_alpha 16 \
    --target_modules "q_proj,v_proj" \
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
