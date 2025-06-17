#!/bin/bash
# Script optimisé pour lancer le fine-tuning du modèle de conscience marchande

# Configuration GPU
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

# Paramètres optimisés pour ~2000 exemples avec RTX 3090 Ti
python finetuneModel.py \
    --model "deepseek-r1-0528-qwen3-8b-q6_k" \
    --epochs 3 \
    --batch_size 2 \
    --output_dir "./merchant-consciousness-v1" \
    --quantization 8bit \
    --use_wandb

# Test post-training (décommenter si un script de test existe)
# python test_consciousness.py \
#     --model_path "./merchant-consciousness-v1" \
#     --comprehensive_test
