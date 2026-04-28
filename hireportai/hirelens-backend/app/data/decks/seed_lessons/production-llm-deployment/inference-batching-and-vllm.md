---
slug: inference-batching-and-vllm
title: Inference Batching and vLLM
display_order: 0
quiz_items:
  - question: 'Why does continuous batching (PagedAttention / vLLM) outperform static batching for LLM inference workloads, and what is the operational trade-off?'
    answer: 'Static batching collects N requests, runs the prefill+decode loop together, and waits for the slowest sequence to finish — short outputs sit idle behind long ones, and GPU utilization drops as the batch decodes. Continuous batching processes the prefill and decode stages independently and admits new requests into the running batch every step, so finished sequences are evicted immediately and the batch stays full. The operational trade-off is added complexity in the inference engine (KV cache management, scheduling), and head-of-line latency variance — a single slow request can briefly inflate the batch but no longer blocks others.'
    question_type: free_text
    difficulty: hard
    display_order: 0
  - question: 'A team is sizing a vLLM deployment for a 7B model serving 200 RPS with average 600 input + 400 output tokens. Which is the most reasonable starting GPU choice?'
    answer: 'A100 80GB or H100 80GB — the KV cache and concurrent-batch headroom both consume VRAM linearly with concurrency'
    question_type: mcq
    distractors:
      - 'A single T4 16GB will suffice for 7B inference'
      - 'CPU-only inference with quantization is the right baseline'
      - 'Three L4 24GB cards in tensor-parallel give better cost/throughput'
    difficulty: medium
    display_order: 1
---
## Concept

The single biggest unlock for self-hosted LLM cost is continuous
batching. PagedAttention (vLLM) keeps the GPU saturated by processing
many sequences concurrently and allocating KV cache in fixed-size
"pages" so memory fragmentation doesn't bottleneck concurrency.

The math: a 7B model on an A100 80GB can sustain ~3000-4000 output
tokens/sec aggregate at ~64 concurrent sequences. Pushed to 200 RPS
with average 400 output tokens that's 80,000 tok/sec needed across the
fleet — typically 4-6 A100s with vLLM, vs 20+ with a naive batching
approach.

## Production

Three knobs that move throughput:

1. **`max_num_seqs`.** Concurrent sequences. Raise until KV cache is
   the bottleneck.
2. **`max_model_len`.** Max sequence length. Pad-to-max wastes KV
   cache; set this conservatively to the p99 of your actual sequences.
3. **Tensor parallelism vs replication.** TP shards a model across N
   GPUs to fit larger weights or reduce per-token latency; replication
   serves N independent instances for higher throughput. For 7B,
   replication is usually the right answer.

```python
# vLLM serving config
engine_args = AsyncEngineArgs(
    model="meta-llama/Llama-3.1-8B-Instruct",
    max_num_seqs=128,
    max_model_len=8192,
    gpu_memory_utilization=0.92,
    enable_prefix_caching=True,  # huge win for system-prompt-heavy workloads
)
```

`enable_prefix_caching` deserves special mention: if your workload
shares a long system prompt, prefix caching reuses the prefill KV
cache across requests, often cutting time-to-first-token by 60-80%.

## Examples

| Workload shape                | Optimal config                          |
|-------------------------------|-----------------------------------------|
| Short prompts, short outputs  | High max_num_seqs, smaller max_model_len |
| Long context, RAG             | Prefix caching ON, lower max_num_seqs   |
| Streaming chat                | Continuous batching, p99 latency SLA    |
| Bulk batch enrichment         | Static large-batch, throughput priority |

The pattern: inference economics are dominated by GPU-hour cost ÷
tokens/sec. Continuous batching plus prefix caching plus right-sized
concurrency wins on every dimension that matters.
