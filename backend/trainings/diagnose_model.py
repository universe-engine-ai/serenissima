#!/usr/bin/env python3
"""
Script de diagnostic pour tester le chargement des modèles Hugging Face.
Utile pour déboguer les problèmes de chargement de modèles récents.

Usage:
    python diagnose_model.py [--model MODEL_NAME]
"""

import argparse
import transformers
from transformers import AutoConfig, AutoTokenizer, AutoModelForCausalLM
import torch
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Diagnostiquer le chargement d'un modèle Hugging Face")
    parser.add_argument("--model", type=str, default="deepseek-ai/DeepSeek-R1-0528-Qwen3-8B", 
                        help="Nom ou ID du modèle à tester")
    parser.add_argument("--verbose", action="store_true", help="Afficher des informations détaillées")
    
    args = parser.parse_args()
    model_name = args.model
    verbose = args.verbose
    
    print(f"🔍 Diagnostic du modèle: {model_name}")
    print(f"📚 Transformers version: {transformers.__version__}")
    print(f"🔥 PyTorch version: {torch.__version__}")
    print(f"💻 CUDA disponible: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"🖥️ GPU: {torch.cuda.get_device_name(0)}")
    
    # 1. Tester la configuration
    print("\n1️⃣ Test de la configuration...")
    try:
        config = AutoConfig.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        print(f"✅ Configuration chargée")
        print(f"   Architecture: {config.architectures if hasattr(config, 'architectures') else 'Non spécifiée'}")
        print(f"   Model type: {config.model_type}")
        if verbose:
            print(f"   Configuration complète: {config}")
    except Exception as e:
        print(f"❌ Erreur config: {e}")
    
    # 2. Tester le tokenizer
    print("\n2️⃣ Test du tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        print(f"✅ Tokenizer chargé")
        print(f"   Taille du vocabulaire: {tokenizer.vocab_size if hasattr(tokenizer, 'vocab_size') else 'Non disponible'}")
        print(f"   Tokens spéciaux: {tokenizer.all_special_tokens}")
        
        # Test de tokenization
        test_text = "Bonjour, je suis un marchand vénitien."
        tokens = tokenizer(test_text)
        print(f"   Test de tokenization: '{test_text}' → {len(tokens['input_ids'])} tokens")
    except Exception as e:
        print(f"❌ Erreur tokenizer: {e}")
    
    # 3. Tester le modèle avec différentes approches
    print("\n3️⃣ Test du modèle...")
    approaches = [
        ("AutoModelForCausalLM", AutoModelForCausalLM),
        ("AutoModel", transformers.AutoModel),
    ]
    
    model_loaded = False
    for name, model_class in approaches:
        try:
            print(f"\nTest avec {name}...")
            model = model_class.from_pretrained(
                model_name,
                trust_remote_code=True,
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
                device_map="auto"
            )
            print(f"✅ {name} fonctionne!")
            
            # Afficher des informations sur le modèle
            if hasattr(model, "config"):
                if hasattr(model.config, "hidden_size"):
                    print(f"   Taille cachée: {model.config.hidden_size}")
                if hasattr(model.config, "num_hidden_layers"):
                    print(f"   Nombre de couches: {model.config.num_hidden_layers}")
            
            # Test de génération
            if hasattr(model, "generate") and callable(model.generate):
                try:
                    print("\n4️⃣ Test de génération...")
                    inputs = tokenizer("Bonjour, je suis", return_tensors="pt").to(model.device)
                    outputs = model.generate(inputs["input_ids"], max_new_tokens=20, do_sample=True)
                    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
                    print(f"   Texte généré: {generated_text}")
                except Exception as e:
                    print(f"❌ Erreur lors de la génération: {e}")
            
            model_loaded = True
            break
        except Exception as e:
            print(f"❌ {name} erreur: {e}")
    
    if not model_loaded:
        print("\n❌ Échec du chargement du modèle avec toutes les approches")
        print("\n💡 Suggestions:")
        print("   1. Vérifiez que vous avez la dernière version de transformers:")
        print("      pip install --upgrade transformers")
        print("   2. Assurez-vous d'avoir suffisamment de mémoire GPU/RAM")
        print("   3. Assurez-vous d'avoir suffisamment de mémoire GPU/RAM")
        print("   4. Vérifiez si le modèle nécessite des dépendances spécifiques")
    else:
        print("\n✅ Diagnostic terminé avec succès!")

if __name__ == "__main__":
    main()
