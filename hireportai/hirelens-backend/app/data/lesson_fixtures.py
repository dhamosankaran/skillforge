"""Fixture-data loader for slice 6.3 lesson UX (read-only).

Spec: docs/specs/phase-6/03-lesson-ux.md §4.1 + §7.

Per D-2 / D-9: per-instance Pydantic models built at module import.
No JSON, no factory functions, no parse step. Schema drift surfaces
at import time, not at request time.

**Retirement (slice 6.4):** delete this file in the same commit that
swaps `app/services/lesson_service.py` from the loader call to a DB
query. The route Pydantic shape stays unchanged across the swap, so
FE need not redeploy.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.deck import DeckResponse
from app.schemas.lesson import LessonResponse
from app.schemas.quiz_item import QuizItemResponse

_NOW = datetime(2026, 4, 27, 0, 0, 0, tzinfo=timezone.utc)

_DECKS: dict[str, DeckResponse] = {
    "deck-fixture-transformer-llm-internals": DeckResponse(
        id="deck-fixture-transformer-llm-internals",
        slug="transformer-llm-internals",
        title="Transformer LLM Internals",
        description=(
            "How modern transformer-based LLMs are built and run, from "
            "tokenization through attention to inference."
        ),
        display_order=0,
        icon=None,
        persona_visibility="both",
        tier="foundation",
        created_at=_NOW,
        updated_at=_NOW,
        archived_at=None,
    ),
    "deck-fixture-agentic-systems-mcp": DeckResponse(
        id="deck-fixture-agentic-systems-mcp",
        slug="agentic-systems-mcp",
        title="Agentic Systems & MCP",
        description="Tool-calling agents and the Model Context Protocol.",
        display_order=1,
        icon=None,
        persona_visibility="interview_prepper",
        tier="premium",
        created_at=_NOW,
        updated_at=_NOW,
        archived_at=None,
    ),
}

_LESSONS: dict[str, LessonResponse] = {
    "lesson-fixture-attention-mechanism": LessonResponse(
        id="lesson-fixture-attention-mechanism",
        deck_id="deck-fixture-transformer-llm-internals",
        slug="attention-mechanism",
        title="The Attention Mechanism",
        concept_md=(
            "## Concept\n\n"
            "Attention is how a transformer **routes information** between "
            "tokens. Each token computes a query, key, and value vector; the "
            "attention score between two tokens is the scaled dot-product of "
            "their query and key.\n\n"
            "Self-attention lets a token see all other tokens in the same "
            "sequence. Cross-attention lets a decoder token see encoder "
            "tokens — the asymmetric flow that powers translation and "
            "encoder-decoder summarization.\n\n"
            "Multi-head attention runs several attention computations in "
            "parallel, each with its own learned projections, then "
            "concatenates the results."
        ),
        production_md=(
            "## Production\n\n"
            "Use a battle-tested implementation rather than rolling your own:\n\n"
            "```bash\n"
            "pip install torch transformers\n"
            "```\n\n"
            "Then call the high-level API rather than reimplementing scaled "
            "dot-product attention. Custom kernels (FlashAttention, "
            "xFormers) only matter at scale."
        ),
        examples_md=(
            "## Examples\n\n"
            "Self vs cross attention at a glance:\n\n"
            "| Variant | Query source | Key/Value source | Typical use |\n"
            "|---------|--------------|------------------|-------------|\n"
            "| Self | same sequence | same sequence | encoder, decoder |\n"
            "| Cross | decoder | encoder | translation, summarization |\n"
        ),
        display_order=0,
        version=1,
        version_type="initial",
        published_at=_NOW,
        generated_by_model=None,
        source_content_id=None,
        quality_score=None,
        created_at=_NOW,
        updated_at=_NOW,
        archived_at=None,
    ),
    "lesson-fixture-tokenization-bpe": LessonResponse(
        id="lesson-fixture-tokenization-bpe",
        deck_id="deck-fixture-transformer-llm-internals",
        slug="tokenization-byte-pair-encoding",
        title="Tokenization & Byte-Pair Encoding",
        concept_md=(
            "## Concept\n\n"
            "Tokenization splits text into the discrete units a language "
            "model actually sees. Byte-Pair Encoding (BPE) starts from "
            "individual bytes and iteratively merges the most frequent "
            "adjacent pair into a new symbol until a target vocabulary "
            "size is reached.\n\n"
            "Modern LLMs use BPE variants (GPT-style) or SentencePiece "
            "with unigram language-model training. The choice affects "
            "downstream behavior on rare words, code, and non-Latin "
            "scripts."
        ),
        production_md=(
            "## Production\n\n"
            "Train a BPE tokenizer on your domain corpus:\n\n"
            "```python\n"
            "from tokenizers import ByteLevelBPETokenizer\n\n"
            "tok = ByteLevelBPETokenizer()\n"
            "tok.train(['corpus.txt'], vocab_size=32_000, min_frequency=2)\n"
            "tok.save('tokenizer.json')\n"
            "```\n\n"
            "Install the dependency first:\n\n"
            "```bash\n"
            "pip install tokenizers\n"
            "```"
        ),
        examples_md=(
            "## Examples\n\n"
            "Common pitfalls:\n\n"
            "1. Training on cleaned-then-untokenized text and inferring on "
            "raw text (whitespace and casing drift).\n"
            "2. Forgetting to reserve special tokens for padding, BOS, "
            "EOS, and instruction templates.\n"
            "3. Vocabulary too small — long-tail merges blow up sequence "
            "length and inference cost."
        ),
        display_order=1,
        version=1,
        version_type="initial",
        published_at=_NOW,
        generated_by_model=None,
        source_content_id=None,
        quality_score=None,
        created_at=_NOW,
        updated_at=_NOW,
        archived_at=None,
    ),
    "lesson-fixture-mcp-tool-calling-loop": LessonResponse(
        id="lesson-fixture-mcp-tool-calling-loop",
        deck_id="deck-fixture-agentic-systems-mcp",
        slug="mcp-tool-calling-loop",
        title="The MCP Tool-Calling Loop",
        concept_md=(
            "## Concept\n\n"
            "An MCP host runs a loop: send the conversation to the model, "
            "receive a response that may include tool calls, execute the "
            "tools, append results to the conversation, and repeat until "
            "the model emits a final answer."
        ),
        production_md=(
            "## Production\n\n"
            "Cap the loop iteration count and total tokens budget — "
            "without limits a misbehaving agent can spin indefinitely."
        ),
        examples_md=(
            "## Examples\n\n"
            "A read → search → write loop is the canonical research "
            "pattern."
        ),
        display_order=0,
        version=1,
        version_type="initial",
        published_at=_NOW,
        generated_by_model=None,
        source_content_id=None,
        quality_score=None,
        created_at=_NOW,
        updated_at=_NOW,
        archived_at=None,
    ),
}

_QUIZ_ITEMS: dict[str, QuizItemResponse] = {
    "quiz-fixture-attention-1": QuizItemResponse(
        id="quiz-fixture-attention-1",
        lesson_id="lesson-fixture-attention-mechanism",
        question="In one sentence, what is the role of the query vector in attention?",
        answer=(
            "The query vector represents what the current token is looking "
            "for; its dot product with each key produces the attention "
            "scores."
        ),
        question_type="free_text",
        distractors=None,
        difficulty="easy",
        display_order=0,
        version=1,
        superseded_by_id=None,
        retired_at=None,
        generated_by_model=None,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    "quiz-fixture-attention-2": QuizItemResponse(
        id="quiz-fixture-attention-2",
        lesson_id="lesson-fixture-attention-mechanism",
        question="Which statement best describes cross-attention?",
        answer="Decoder queries attend over encoder keys and values.",
        question_type="mcq",
        distractors=[
            "Decoder queries attend over decoder keys and values.",
            "Encoder queries attend over decoder keys and values.",
            "Queries and keys come from the same projection matrix.",
        ],
        difficulty="medium",
        display_order=1,
        version=1,
        superseded_by_id=None,
        retired_at=None,
        generated_by_model=None,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    "quiz-fixture-attention-3": QuizItemResponse(
        id="quiz-fixture-attention-3",
        lesson_id="lesson-fixture-attention-mechanism",
        question=(
            "Complete the line so the snippet computes scaled dot-product "
            "attention scores: `scores = (Q @ K.transpose(-2, -1)) / ___`"
        ),
        answer="math.sqrt(d_k)",
        question_type="code_completion",
        distractors=None,
        difficulty="hard",
        display_order=2,
        version=1,
        superseded_by_id=None,
        retired_at=None,
        generated_by_model=None,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    "quiz-fixture-bpe-1": QuizItemResponse(
        id="quiz-fixture-bpe-1",
        lesson_id="lesson-fixture-tokenization-bpe",
        question="What does the BPE training loop merge at each step?",
        answer="The most frequent adjacent pair of existing symbols.",
        question_type="free_text",
        distractors=None,
        difficulty="easy",
        display_order=0,
        version=1,
        superseded_by_id=None,
        retired_at=None,
        generated_by_model=None,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    "quiz-fixture-bpe-2": QuizItemResponse(
        id="quiz-fixture-bpe-2",
        lesson_id="lesson-fixture-tokenization-bpe",
        question=(
            "Why does training on cleaned text and inferring on raw text "
            "degrade quality?"
        ),
        answer=(
            "The tokenizer never saw the casing and whitespace patterns "
            "of the inference distribution, so common words split into "
            "rare subtokens and the model behaves out-of-domain."
        ),
        question_type="free_text",
        distractors=None,
        difficulty="medium",
        display_order=1,
        version=1,
        superseded_by_id=None,
        retired_at=None,
        generated_by_model=None,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    "quiz-fixture-mcp-1": QuizItemResponse(
        id="quiz-fixture-mcp-1",
        lesson_id="lesson-fixture-mcp-tool-calling-loop",
        question="Why must an MCP host cap loop iterations?",
        answer="To prevent a misbehaving agent from spinning indefinitely.",
        question_type="mcq",
        distractors=[
            "To force the model to use every available tool.",
            "Because MCP refuses tool calls beyond the first.",
            "Loop caps are required by the JSON-RPC transport.",
        ],
        difficulty="medium",
        display_order=0,
        version=1,
        superseded_by_id=None,
        retired_at=None,
        generated_by_model=None,
        created_at=_NOW,
        updated_at=_NOW,
    ),
}


def list_decks() -> list[DeckResponse]:
    """All non-archived decks, ordered by display_order then id."""
    return sorted(
        (d for d in _DECKS.values() if d.archived_at is None),
        key=lambda d: (d.display_order, d.id),
    )


def get_deck(deck_id: str) -> DeckResponse | None:
    """Single non-archived deck or None."""
    deck = _DECKS.get(deck_id)
    if deck is None or deck.archived_at is not None:
        return None
    return deck


def list_lessons(deck_id: str) -> list[LessonResponse]:
    """Active lessons for a deck, ordered by display_order then id.

    Returns an empty list when the deck has no lessons. Returns an
    empty list when the deck does not exist (route handler decides
    whether to 404 by checking the deck separately via `get_deck`).
    """
    return sorted(
        (
            lsn
            for lsn in _LESSONS.values()
            if lsn.deck_id == deck_id and lsn.archived_at is None
        ),
        key=lambda lsn: (lsn.display_order, lsn.id),
    )


def get_lesson(lesson_id: str) -> LessonResponse | None:
    """Single non-archived lesson or None."""
    lesson = _LESSONS.get(lesson_id)
    if lesson is None or lesson.archived_at is not None:
        return None
    return lesson


def list_quiz_items(lesson_id: str) -> list[QuizItemResponse]:
    """Active quiz items for a lesson, ordered by display_order then id."""
    return sorted(
        (
            qi
            for qi in _QUIZ_ITEMS.values()
            if qi.lesson_id == lesson_id and qi.retired_at is None
        ),
        key=lambda qi: (qi.display_order, qi.id),
    )
