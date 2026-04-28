---
slug: chunking-strategies
title: Chunking Strategies for RAG
display_order: 0
quiz_items:
  - question: 'What is the central trade-off when choosing chunk size in a RAG pipeline?'
    answer: 'Smaller chunks improve retrieval precision (the matching span is closer to the question) but reduce generation context, so the LLM has less surrounding material to ground its answer. Larger chunks do the opposite. Production systems usually pick a midpoint plus an overlap window so adjacent chunks share a few tokens of context.'
    question_type: free_text
    difficulty: easy
    display_order: 0
  - question: 'For dense English prose at a 512-token retrieval window, which chunking approach is the most defensible default?'
    answer: 'Recursive structural splitting at ~256-512 tokens with 64-token overlap'
    question_type: mcq
    distractors:
      - 'Fixed 1024-token character chunking with no overlap'
      - 'One chunk per paragraph regardless of length'
      - 'One chunk per sentence to maximize precision'
    difficulty: medium
    display_order: 1
---
## Concept

Chunking turns a corpus into the units your retriever will rank. The
fundamental tension: small chunks raise retrieval precision (the matching
span is tightly anchored to the question) but starve the generator of
surrounding context; large chunks do the opposite. Both extremes fail in
predictable ways — too small and answers hallucinate around missing
context, too large and irrelevant material drowns the prompt.

The senior-engineer move is to pick chunk boundaries that respect the
semantic units of your content. For prose: sentence + paragraph
boundaries. For code: function or block boundaries. For structured docs:
section headings.

## Production

In production, recursive structural splitters are the workhorse. Tune
two knobs together: `chunk_size` and `chunk_overlap`. Overlap protects
against the boundary problem where the answer straddles two chunks.

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    separators=["\n\n", "\n", ". ", " "],
)
chunks = splitter.split_documents(docs)
```

Watch the failure modes: tables and code blocks split mid-row destroy
retrieval; very short chunks (<50 tokens) often have such low embedding
signal that they retrieve as noise; very long chunks (>1500 tokens) push
out the question's allocation of attention.

## Examples

| Corpus type        | chunk_size | overlap | Notes                                   |
|--------------------|------------|---------|-----------------------------------------|
| English prose      | 512        | 64      | Default; tune up for narrative reasoning |
| Code documentation | 1024       | 128     | Preserve function-level context         |
| Markdown / FAQ     | 256        | 32      | Per-Q&A is often a clean unit           |
| Legal / policy     | 768        | 128     | Sentences are long; clause-level chunks |
