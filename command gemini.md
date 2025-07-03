aider --model gemini/gemini-2.5-pro-preview-06-05

ngrok http 1234 --url trusted-magpie-social.ngrok-free.app

  python finetuneModel.py --epochs 3 --batch_size 1 --gradient_accumulation_steps 8     --fp16 --no-int8 --save_steps 100 --warmup_steps 100 --save_total_limit 1     --lora_r 16 --learning_rate 1e-6 --lora_alpha 32     --lora_target_modules "q_proj,v_proj,k_proj,o_proj,gate_proj,up_proj,down_proj"    --no-test-generation