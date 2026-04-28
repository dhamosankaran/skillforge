---
slug: lora-and-qlora
title: LoRA and QLoRA
display_order: 0
quiz_items:
  - question: 'Why does LoRA produce results comparable to full-parameter fine-tuning despite training only ~0.1-1% of the parameters, and what is QLoRA''s additional contribution?'
    answer: 'LoRA freezes the base model''s weights and learns a low-rank update to selected projection matrices (typically the attention Q and V projections), based on the empirical observation that fine-tuning updates have low intrinsic rank — most of the change can be captured by adding A·B where A and B are small. QLoRA extends this by quantizing the frozen base weights to 4-bit (NF4 quantization), so a 70B model that would normally need 140GB+ of VRAM for fine-tuning fits in ~48GB. The trainable LoRA adapters stay in higher precision, so quality only marginally degrades versus 16-bit LoRA.'
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: 'Show a minimal HuggingFace `peft` config for LoRA fine-tuning a 7B causal LM, targeting attention projections with rank 16.'
    answer: |
      from peft import LoraConfig, get_peft_model

      config = LoraConfig(
          r=16,
          lora_alpha=32,
          target_modules=["q_proj", "v_proj"],
          lora_dropout=0.05,
          bias="none",
          task_type="CAUSAL_LM",
      )
      model = get_peft_model(base_model, config)
      model.print_trainable_parameters()
    question_type: code_completion
    difficulty: hard
    display_order: 1
---
## Concept

Full-parameter fine-tuning of a 7B+ model is slow, expensive, and
mostly unnecessary. LoRA (Low-Rank Adaptation) is the workhorse
parameter-efficient method: freeze the base weights, add small
trainable matrices A and B such that the effective weight update is
ΔW = A·B with rank r ∈ [4, 64]. Trains 0.1-1% of parameters; quality
typically within 1-2% of full fine-tuning on instruction-following
tasks.

QLoRA goes further: quantize the frozen base to 4-bit (NF4), keep the
LoRA adapters in 16-bit. Brings 70B fine-tuning into single-GPU reach.

## Production

The defaults that work:

- **Rank `r`.** 8-16 for instruction tuning; 32-64 for domain
  adaptation. Higher rank stops paying back fast.
- **`alpha`.** Conventional default `alpha = 2 * r`. Effective scale
  is `alpha / r`.
- **Target modules.** `q_proj` + `v_proj` is the cheap default;
  including `o_proj`, `k_proj`, MLP up/down projections improves
  quality at higher VRAM cost.
- **Learning rate.** 1e-4 to 3e-4 for LoRA; 2e-4 is a strong default.
  Higher than full-FT because only the adapters train.

```python
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4")
base = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.1-8B", quantization_config=bnb)

config = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM")
model = get_peft_model(base, config)
```

A 7B QLoRA fine-tune on 50K examples typically runs in 4-12 hours on a
single A100. Train, then merge the adapter weights for inference if you
want flat throughput, or keep them separate if you want hot-swappable
adapters.

## Examples

| Task                       | Method      | When                            |
|----------------------------|-------------|----------------------------------|
| Style / format adaptation  | Prompt only | Low investment, fast iteration  |
| Tone / voice               | LoRA        | After prompt hits a quality cap |
| Domain language (legal)    | LoRA        | Need consistent terminology     |
| New skill (function calling) | Full FT or QLoRA | Skill not in base capability |
| Multi-tenant per-customer  | Many small LoRAs | Hot-swappable adapters per request |

The pattern: start with prompting; reach for LoRA when the prompt
ceiling is below your quality bar; reserve full fine-tuning for tasks
where LoRA's quality gap is genuinely the blocker.
