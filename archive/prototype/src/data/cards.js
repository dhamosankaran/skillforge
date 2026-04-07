// ═══════════════════════════════════════════════════════════════
// SKILLFORGE — Card Data (Extracted & Anonymized Sample)
// Full 177+ cards would be extracted from JSX files via script
// This contains representative cards for the prototype
// ═══════════════════════════════════════════════════════════════

export const CATEGORIES = {
  "Transformer Fundamentals": {
    icon: "🧠", color: "#6366F1", accent: "#4F46E5", slug: "transformers",
    cards: [
      {
        id: "tf-1",
        q: "Explain the Mixture of Experts (MoE) architecture. How does Mixtral 8x7B achieve near-70B quality at 13B inference cost?",
        a: "MoE Architecture:\n\n🏗️ CORE CONCEPT:\n• Instead of one massive dense model, MoE has multiple smaller 'expert' sub-networks\n• A Router/Gating network decides which experts process each token\n• Only a subset of experts activate per token (sparse activation)\n\n📐 MIXTRAL 8x7B BREAKDOWN:\n• 8 expert networks, each ~7B parameters\n• Total params: ~47B (8 × 7B)\n• Router selects TOP-2 experts per token\n• Active params per token: ~13B (2 × 7B)\n• Result: 70B-quality output at 13B compute cost\n\n🔄 HOW ROUTING WORKS:\n1. Input token → Router network (small linear layer)\n2. Router outputs probability distribution over 8 experts\n3. Top-K (usually 2) experts selected\n4. Each selected expert processes the token independently\n5. Outputs weighted by router probabilities and combined\n\n💡 KEY BENEFITS:\n• Compute efficiency: Only fraction of params active\n• Specialization: Experts learn different domains\n• Scalability: Add experts without proportional compute increase",
        expertExp: "At a Fortune 100 financial institution, we evaluated MoE models for our multi-domain AI platform. The key insight: MoE models excel when your workload spans multiple domains (trading, compliance, customer service) because different experts naturally specialize. We benchmarked Mixtral 8x7B against GPT-4 on our internal financial Q&A suite — Mixtral achieved 89% of GPT-4's accuracy at 35% of the inference cost, saving approximately $180K/month at our scale of 50K daily queries.",
        aiRefExp: "In a typical enterprise deployment, MoE architectures shine for multi-tenant platforms serving diverse query types. Key metrics to expect: 40-60% cost reduction vs equivalent dense models, 2-3x throughput improvement, with minimal quality degradation (typically 85-92% of dense model quality). The main challenge is memory — the full model must be loaded even though only 2 experts activate per token. Solutions include expert offloading to CPU/disk for less-used experts, or using frameworks like vLLM that handle MoE scheduling efficiently.",
        difficulty: "Hard",
        tags: ["Transformers", "MoE", "Architecture"],
        quiz: {
          question: "In Mixtral 8x7B, how many expert parameters are active during inference for each token?",
          options: ["All 47B", "~13B (2 of 8 experts)", "~6B (1 of 8 experts)", "~26B (4 of 8 experts)"],
          correct: 1,
          explanation: "Mixtral uses top-2 routing — for each token, the router selects 2 of 8 experts. Each expert is ~7B params, so ~13B params are active per token (plus shared attention layers)."
        }
      }
    ]
  },
  "Prompt Engineering": {
    icon: "✏️", color: "#8B5CF6", accent: "#6D28D9", slug: "prompt-eng",
    cards: [
      {
        id: "pe-1",
        q: "Map out ALL prompt engineering techniques from basic to advanced. Which to use when?",
        a: "Hierarchy of techniques:\n\n🟢 Basic:\n• Zero-shot: Direct instruction, no examples\n• Few-shot: Include 3-5 examples in prompt\n• Role/Persona: 'You are a senior financial analyst...'\n\n🟡 Intermediate:\n• Chain-of-Thought (CoT): 'Let\\'s think step by step'\n• Self-Consistency: Sample multiple CoT paths, majority vote\n• ReAct: Interleave Reasoning + Acting with tools\n\n🔴 Advanced:\n• Tree-of-Thought (ToT): Explore branching reasoning paths\n• Skeleton-of-Thought: Parallel outline then detail expansion\n• Meta-Prompting: LLM generates/optimizes its own prompt\n• DSPy: Programmatic prompt optimization with signatures\n\n⚡ Production:\n• Prompt Chaining: Multi-step pipeline of prompts\n• Automatic Prompt Engineering (APE): LLM-generated prompts\n• Constitutional AI prompting: Self-critique and revision",
        expertExp: "At a Fortune 100 financial institution, we built a prompt engineering framework with tiered techniques. Tier 1 (simple tasks like classification): Zero-shot with structured output. Tier 2 (analysis): Few-shot CoT with financial examples. Tier 3 (complex reasoning): Tree-of-Thought with self-consistency voting. This reduced prompt iteration time from weeks to days and improved consistency by 45%.",
        aiRefExp: "In enterprise prompt engineering, the key pattern is matching technique complexity to task complexity. Start simple (zero-shot), measure quality, and escalate only when needed. Most production systems use: Gate Pattern (classify input → route to specialized prompt) + Template Pattern (variables injected at runtime) + Guard Pattern (input/output validation). Expect 2-3 weeks of prompt tuning per production use case, with automated eval suites of 50+ test cases each.",
        difficulty: "Medium",
        tags: ["Prompt Engineering", "Techniques"],
        quiz: {
          question: "What is the key difference between Chain-of-Thought and Tree-of-Thought prompting?",
          options: ["CoT uses examples, ToT doesn't", "CoT follows one reasoning path, ToT explores multiple branching paths", "ToT is faster than CoT", "CoT requires fine-tuning, ToT doesn't"],
          correct: 1,
          explanation: "CoT follows a single linear reasoning chain. ToT explores multiple possible reasoning paths (like a tree), evaluates each branch, and can backtrack."
        }
      },
      {
        id: "pe-2",
        q: "What is Context Engineering? How is it different from Prompt Engineering?",
        a: "Context Engineering is the broader discipline of managing EVERYTHING the model sees:\n\n• Prompt Engineering: Crafting the instruction/query portion\n• Context Engineering: Managing the ENTIRE context window including:\n  1. System prompt design and versioning\n  2. Dynamic context selection (which docs/history to include)\n  3. Context window budget allocation\n  4. Memory management (what to remember/forget across turns)\n  5. Tool/function descriptions optimization\n  6. RAG context placement and ordering\n  7. Few-shot example selection algorithms\n\nKey insight: With 128K+ context windows, HOW you fill the context matters more than the prompt itself.\n\nTechniques:\n• Lost-in-the-middle mitigation: Place critical info at start/end\n• Context compression: Summarize older conversation turns\n• Dynamic example selection: Retrieve most similar few-shot examples\n• Context caching: Reuse static context across requests",
        expertExp: "At a Fortune 100 financial institution, context engineering was a major architectural decision. For our regulatory Q&A system, we allocate the 128K context window as: System prompt (2K) + Regulatory framework (8K, static/cached) + Retrieved docs (40K) + Conversation history (8K, compressed) + Query (1K). We built a context manager service that dynamically adjusts allocations based on query complexity. This improved answer accuracy by 28% over naive context stuffing.",
        aiRefExp: "Context engineering becomes critical at scale. The key metric is 'context utilization efficiency' — how much of your context window contributes to answer quality. Best practices: allocate static content at the top (cached), retrieved content in the middle (dynamic), and user query at the bottom. Monitor for 'context rot' where older conversation turns degrade answer quality. Enterprise systems typically achieve 60-75% context utilization efficiency with proper engineering.",
        difficulty: "Hard",
        tags: ["Context Engineering", "Architecture"],
        quiz: {
          question: "What is the 'lost-in-the-middle' problem in LLMs?",
          options: ["Models forget their system prompt", "Models attend less to information in the middle of long contexts", "Models lose track of conversation turns", "Middle layers contribute less"],
          correct: 1,
          explanation: "Research shows LLMs attend strongly to the beginning and end of context but poorly to the middle. Mitigation: place critical info at start/end."
        }
      }
    ]
  },
  "RAG Architecture": {
    icon: "🔗", color: "#10B981", accent: "#047857", slug: "rag",
    cards: [
      {
        id: "rag-1",
        q: "Design a production-grade RAG system end-to-end. Cover every component and decision point.",
        a: "Complete RAG Pipeline:\n\n📥 INGESTION:\n1. Document Loading: PDF, HTML, DB, APIs\n2. Pre-processing: Table extraction, image OCR, metadata enrichment\n3. Chunking: Recursive text splitting, semantic chunking\n4. Embedding: OpenAI ada-002, Cohere embed-v3, BGE\n5. Indexing: Vector DB + metadata store\n\n🔍 RETRIEVAL:\n1. Query understanding: Rewriting, decomposition, HyDE\n2. Hybrid search: Dense (vector) + Sparse (BM25)\n3. Re-ranking: Cross-encoder, Cohere Rerank, ColBERT\n4. Filtering: Metadata-based (date, source, access control)\n\n🧠 AUGMENTATION:\n1. Context assembly: Chunk ordering, deduplication\n2. Prompt construction: System + context + query template\n3. Context compression: LLMLingua, selective inclusion\n\n📤 GENERATION:\n1. LLM inference with guardrails\n2. Citation extraction and grounding\n3. Confidence scoring\n4. Fallback handling",
        expertExp: "At a Fortune 100 financial institution, I architected the enterprise RAG platform serving 15 internal applications. Key decisions: (1) pgvector for vector storage (reused existing PostgreSQL, saved $200K/year vs managed vector DB), (2) Hybrid search with BM25 + ada-002 embeddings with RRF fusion, (3) Cohere Rerank v3 as re-ranker (improved Recall@5 from 78% to 91%). Platform handles 50K queries/day with P95 latency < 3 seconds.",
        aiRefExp: "A production RAG system typically requires 3-6 months to reach production quality. Key metrics: Retrieval accuracy (Recall@5 > 85%), answer faithfulness (> 0.90 vs source docs), latency (P95 < 5s for enterprise). Common failure modes: (1) Chunking too large (misses specific details) or too small (loses context), (2) Embedding model not tuned for domain vocabulary, (3) No re-ranking stage (reduces precision by 15-25%). Budget: $500-2K/month for a mid-scale deployment handling 10K-50K queries/day.",
        difficulty: "Hard",
        tags: ["RAG", "System Design"],
        quiz: {
          question: "What is Reciprocal Rank Fusion (RRF) in hybrid search?",
          options: ["A neural re-ranking method", "A technique to combine results from multiple retrieval methods by merging ranked lists", "A way to compress embeddings", "A chunking strategy"],
          correct: 1,
          explanation: "RRF combines ranked results from different retrieval methods (dense + sparse) by assigning scores based on rank position. Formula: RRF(d) = Σ 1/(k + rank(d)). It's simple, effective, and doesn't require training."
        }
      }
    ]
  },
  "AI Agents & MCP": {
    icon: "🤖", color: "#F59E0B", accent: "#D97706", slug: "agents",
    cards: [
      {
        id: "ai-35",
        q: "What is MCP (Model Context Protocol)? Explain the architecture, components, and why it matters for enterprise AI.",
        a: "MCP (Model Context Protocol) — The 'USB-C for AI':\n\n🎯 WHAT IT IS:\n• An open standard protocol that connects AI models to external data sources and tools\n• Created by Anthropic, now adopted across the ecosystem\n• Solves the N×M integration problem: Without MCP, N agents × M tools = N×M custom integrations. With MCP: N agents × 1 protocol × M servers = N+M integrations\n\n🏗️ ARCHITECTURE:\n• MCP Host: The AI application (Claude Desktop, IDE, custom app)\n• MCP Client: Protocol handler inside the host\n• MCP Server: Lightweight program exposing specific capabilities\n• Transport: stdio (local) or SSE/HTTP (remote)\n\n📦 WHAT SERVERS EXPOSE:\n1. Resources: Read-only data (files, DB records, API responses)\n2. Tools: Executable functions (search, calculate, create)\n3. Prompts: Reusable prompt templates\n\n🔒 SECURITY:\n• Servers run with scoped permissions\n• Human-in-the-loop for sensitive operations\n• OAuth for remote servers",
        expertExp: "At a Fortune 100 financial institution, we built 12 MCP servers for our agent platform: trade-blotter-mcp (read-only trade data), compliance-rules-mcp (regulatory lookup), market-data-mcp (real-time prices), document-store-mcp (internal docs), and 8 others. Key decision: we enforce tool-level RBAC — the trade-blotter-mcp grants READ to research agents but READ+WRITE only to reconciliation agents. This architecture reduced our integration development time from weeks per agent to days.",
        aiRefExp: "Enterprise MCP deployments typically start with 3-5 servers covering the most common data sources (internal docs, database, APIs). Key metrics: integration time drops from 2-4 weeks per agent to 2-3 days. Main challenges: (1) OAuth flow complexity for remote servers, (2) Rate limiting per-agent to prevent resource exhaustion, (3) No native pagination — large result sets require custom chunking. Best practice: build an MCP Gateway that handles auth, rate limiting, and logging for all servers centrally.",
        difficulty: "Hard",
        tags: ["MCP", "Protocol", "Enterprise"],
        quiz: {
          question: "What problem does MCP solve that direct API integrations don't?",
          options: ["Faster API calls", "The N×M integration explosion — without MCP, every agent needs custom code for every tool", "Better security", "Lower cost"],
          correct: 1,
          explanation: "Without MCP, connecting N agents to M tools requires N×M custom integrations. MCP standardizes the protocol so you only need N clients + M servers = N+M total integrations."
        }
      }
    ]
  },
  "Evaluation & Benchmarks": {
    icon: "📊", color: "#EC4899", accent: "#DB2777", slug: "evaluation",
    cards: [
      {
        id: "ev-3",
        q: "Explain the AI vs Software paradigm shift: Why does 80-90% of AI work happen POST-deployment?",
        a: "The AI Evaluation Paradigm Shift:\n\n🔄 THE KEY INSIGHT:\n• Traditional SOFTWARE: 80-90% of work happens in DEVELOPMENT\n• AI: 80-90% of work happens POST-DEPLOYMENT\n\nWhy? Software is deterministic — test it, ship it, done. AI is non-deterministic — real users are unpredictable, models drift.\n\n📋 THE 6-STEP AI LIFECYCLE:\n🔵 DEVELOPMENT (Steps 1-3):\n1. Scope Capability & Curate Data\n2. Set Up Application (RAG, agents, guardrails)\n3. Design Evals (BEFORE deployment)\n\n🟠 DEPLOYMENT (Step 4):\n4. Deploy (starting line, NOT finish line)\n\n🟢 POST-DEPLOYMENT (Steps 5-6):\n5. Run Evals continuously in production\n6. Analyze Behavior & Spot Patterns → loop back to Step 3\n\n💡 IMPLICATIONS:\n• Staff 2:1 operations-to-development\n• Budget 70% for post-deployment\n• Evaluation never stops",
        expertExp: "At a Fortune 100 financial institution, this paradigm shift changed our team structure. We now plan: Phase 1 (Development): 30% of budget. Phase 2 (Post-Deployment): 70% of budget. Team ratio: 4 engineers build new features, 8 engineers maintain and optimize existing 47 agents. Our compliance Q&A agent went from 78% accuracy at launch to 96% today through 23 improvement cycles over 12 months.",
        aiRefExp: "The post-deployment paradigm is the #1 thing enterprises underestimate. A typical AI agent requires 6-8 improvement cycles in its first 3 months to reach production-grade quality. Budget allocation should be: 30% initial development, 20% evaluation infrastructure, 50% ongoing optimization. Key metrics to track post-deployment: task completion rate (target: >95%), faithfulness score (target: >0.90), user escalation rate (target: <5%), cost per query (track weekly for budget management).",
        difficulty: "Medium",
        tags: ["AI Lifecycle", "Evaluation", "Paradigm Shift"],
        quiz: {
          question: "In the AI development lifecycle, where does 80-90% of the work happen?",
          options: ["In initial development", "In deployment", "Post-deployment — continuous evaluation and optimization", "In data collection"],
          correct: 2,
          explanation: "AI is non-deterministic. 80-90% of work happens post-deployment: running evals, analyzing failures, tuning prompts/retrieval, updating guardrails."
        }
      }
    ]
  },
  "Security & Guardrails": {
    icon: "🛡️", color: "#DC2626", accent: "#B91C1C", slug: "security",
    cards: [
      {
        id: "sec-4",
        q: "What are the Five Imperatives for Secure AI Agent Deployment?",
        a: "Five Imperatives for Secure Agentic AI:\n\n1️⃣ REGISTER AGENTS:\n• Unique identities for every agent\n• Agent registry with owner, purpose, risk tier\n• Implementation: Agent Identity Provider (IdP)\n\n2️⃣ STRIP PRIVILEGES:\n• Just-in-time (JIT) privileges, not standing access\n• Scoped, time-limited tokens\n• Implementation: Policy-as-code (OPA/Cedar)\n\n3️⃣ TIE ACTIONS TO INTENT:\n• Every action auditable to original user intent\n• Chain: User request → Agent plan → Action → Result\n• Implementation: OpenTelemetry with custom spans\n\n4️⃣ ENFORCE AT POINT OF USE:\n• Secure the backend, not just the agent\n• Real-time policy checks on every DB/API call\n• Implementation: Database proxy with agent-aware policies\n\n5️⃣ PROOF OF CONTROL:\n• Full auditability for compliance\n• Immutable audit logs\n• Required for: SOX, GDPR, SR 11-7",
        expertExp: "At a Fortune 100 financial institution, we implemented all five imperatives: (1) 47 agents registered in our internal IdP. (2) CyberArk for JIT credentials — 60-second scoped tokens. (3) OpenTelemetry spans with 'user_intent' attributes on every action. (4) Database proxy intercepting all agent SQL queries. (5) Automated SOX compliance reports weekly. Passed 3 consecutive audits with zero findings.",
        aiRefExp: "Implementing the Five Imperatives typically takes 3-6 months for an enterprise. Priority order: Register first (week 1-2), then Enforce at Point of Use (biggest risk reduction), then Strip Privileges, then Tie to Intent, finally Proof of Control. Key metrics: time-to-register new agent (<1 day), privilege grant latency (<100ms), audit coverage (100% of actions logged). Budget: $500K-$1M for initial implementation including tooling (CyberArk/HashiCorp Vault, OPA, database proxy).",
        difficulty: "Hard",
        tags: ["Agentic Security", "Compliance", "Five Imperatives"],
        quiz: {
          question: "What does 'Tie Actions to Intent' mean in secure agent deployment?",
          options: ["Agents should only do intended actions", "Every action must be auditable back to the original user's request through a traceable chain", "Agents should understand user intent", "Actions tied to training objective"],
          correct: 1,
          explanation: "Maintaining a traceable chain: User Request → Agent Plan → Individual Action → Result. Critical for compliance and security."
        }
      }
    ]
  },
  "LangChain & LangGraph": {
    icon: "⛓️", color: "#059669", accent: "#047857", slug: "langchain",
    cards: [
      {
        id: "lc-1",
        q: "Explain the LangChain ecosystem. When to use LangChain vs LangGraph vs LangSmith?",
        a: "LangChain Ecosystem:\n\n⛓️ LANGCHAIN (The Library):\n• Abstractions for LLM interactions (ChatModels, Prompts, OutputParsers)\n• Chain composition (LCEL — LangChain Expression Language)\n• Document loaders, text splitters, vector stores\n• Use when: Building RAG pipelines, simple chains\n\n🔄 LANGGRAPH (The Orchestrator):\n• State machine framework for complex agent workflows\n• Nodes (functions) + Edges (transitions) + State\n• Human-in-the-loop via interrupt_before/interrupt_after\n• PostgreSQL checkpointing for long-running workflows\n• Use when: Multi-step agents, branching logic, HITL\n\n📊 LANGSMITH (The Observer):\n• Tracing: See every LLM call, tool use, chain step\n• Evaluation: Run test suites, compare prompt versions\n• Monitoring: Production metrics, cost tracking\n• Use when: Always — it's your observability layer\n\n🔑 DECISION MATRIX:\n• Simple RAG → LangChain only\n• Complex agent with branching → LangGraph\n• Any production system → LangSmith always",
        expertExp: "At a Fortune 100 financial institution, we use all three: LangChain for RAG pipelines (document loading, chunking, retrieval), LangGraph for our multi-agent orchestration (47 agents with human-in-the-loop approval for high-risk actions), and LangSmith for observability across everything. Key architecture decision: LangGraph's PostgreSQL checkpointing enables us to pause agent workflows for human approval and resume hours later — critical for compliance-required reviews.",
        aiRefExp: "The LangChain ecosystem has become the de facto standard for enterprise LLM applications. Typical adoption path: Start with LangChain for a RAG proof-of-concept (2-3 weeks), add LangSmith for observability (1 day), then introduce LangGraph when you need complex agent workflows (2-4 weeks). Key metric: LangSmith tracing costs ~$10-50/month for moderate usage. Common mistake: using LangGraph for simple chains — it adds unnecessary complexity. Use LCEL chains until you genuinely need state machines.",
        difficulty: "Medium",
        tags: ["LangChain", "LangGraph", "LangSmith", "Ecosystem"],
        quiz: {
          question: "When should you use LangGraph instead of a simple LangChain chain?",
          options: ["For any LLM application", "When you need stateful workflows with branching logic, human-in-the-loop, and persistence", "When you want faster inference", "When using OpenAI models specifically"],
          correct: 1,
          explanation: "LangGraph is for complex workflows that need: state management, conditional branching, human-in-the-loop interrupts, and PostgreSQL checkpointing for long-running processes."
        }
      }
    ]
  },
  "MLOps & Serving": {
    icon: "🚀", color: "#0EA5E9", accent: "#0284C7", slug: "mlops",
    cards: [
      {
        id: "ml-1",
        q: "How do you serve LLMs in production? Compare vLLM, TGI, TensorRT-LLM, and managed APIs.",
        a: "LLM Serving Options:\n\n⚡ vLLM:\n• PagedAttention for efficient memory management\n• Continuous batching for high throughput\n• Best for: Self-hosted open models (Llama, Mistral)\n• Throughput: 5-24x vs naive serving\n\n🤗 TGI (Text Generation Inference):\n• Hugging Face's serving solution\n• Built-in quantization support\n• Best for: HuggingFace model ecosystem\n\n🔥 TensorRT-LLM (NVIDIA):\n• Maximum performance on NVIDIA GPUs\n• Complex setup, vendor lock-in\n• Best for: When you need absolute maximum throughput\n\n☁️ Managed APIs:\n• OpenAI, Anthropic, Google, Bedrock\n• No infrastructure management\n• Best for: Most production use cases\n• Trade-off: Cost vs control\n\n📊 DECISION MATRIX:\n• Prototype → Managed API\n• Cost-sensitive at scale → vLLM + open model\n• NVIDIA fleet → TensorRT-LLM\n• HuggingFace models → TGI",
        expertExp: "At a Fortune 100 financial institution, we use a hybrid approach: Managed APIs (Claude via Bedrock, GPT-4 via Azure OpenAI) for customer-facing applications requiring highest quality, and vLLM serving Mixtral 8x7B on A100 instances for internal tools where cost matters more than marginal quality. The vLLM deployment handles 15K requests/day at $0.002/request vs. $0.03/request for GPT-4 — saving approximately $420/day on our internal summarization pipeline.",
        aiRefExp: "For most enterprises starting their AI journey, managed APIs are the correct first choice. Self-hosting only makes economic sense at >50K requests/day where the infrastructure cost of GPU instances (A100: ~$3/hr) is offset by the volume discount vs API pricing. The crossover point is typically $5K-10K/month in API spend. Below that, the operational burden of managing GPU infrastructure, model updates, and scaling policies isn't justified.",
        difficulty: "Hard",
        tags: ["MLOps", "Serving", "vLLM", "Infrastructure"],
        quiz: {
          question: "What is PagedAttention in vLLM and why does it matter?",
          options: ["A new attention mechanism", "Memory management that stores KV cache in non-contiguous pages, reducing memory waste by up to 55%", "A pagination UI concept", "An attention visualization tool"],
          correct: 1,
          explanation: "PagedAttention treats KV cache like OS virtual memory — storing in non-contiguous pages. This eliminates memory fragmentation, enabling 2-4x more concurrent requests."
        }
      }
    ]
  },
  "Context Engineering": {
    icon: "🔨", color: "#7C3AED", accent: "#6D28D9", slug: "context-eng",
    cards: [
      {
        id: "ce-1",
        q: "What is the Graduated Compression Pipeline for managing agent context windows?",
        a: "Graduated Compression — The Anthropic Pattern:\n\nAs context fills up, apply increasingly aggressive compression:\n\n📊 LEVEL 1 — Tool Result Offloading (Mild):\n• Store full tool outputs externally\n• Replace in context with summary + reference ID\n• Example: SQL result (5000 rows) → 'Query returned 5000 rows. Top 5: [summary]. Full result: ref_id_123'\n\n📊 LEVEL 2 — Observation Masking (Medium):\n• Remove intermediate reasoning steps\n• Keep only: input → final answer\n• Example: 10 search results → 'Found 3 relevant documents about X'\n\n📊 LEVEL 3 — Recursive Summarization (Aggressive):\n• Summarize entire conversation segments\n• 'Turns 1-15 summary: User asked about Q3 revenue. Agent retrieved 3 reports and calculated $4.2B total.'\n\n📊 LEVEL 4 — Agentic Compaction:\n• Agent has a compact_context() tool\n• Agent DECIDES when and what to compress\n• Self-aware context management\n\n💡 KEY INSIGHT:\nCompression is lossy. Each level trades recall for capacity.\nMonitor: answer quality before/after compression.",
        expertExp: "At a Fortune 100 financial institution, we implemented all 4 levels for our research agent. Level 1 alone recovered 40% of context window by offloading SQL query results to a cache with summaries. The key lesson: Level 3 (recursive summarization) must preserve entity references and numerical values, or the agent loses critical context. We track 'context quality score' — the % of questions the agent can still answer correctly after each compression level. Target: >90% at Level 2, >75% at Level 3.",
        aiRefExp: "Graduated compression is essential for production agents with long-running sessions (>20 turns). Implementation priority: Start with Level 1 (tool result offloading) — it's the highest ROI with lowest risk. Each subsequent level requires more careful monitoring. Key metric: 'compression ratio' — how many tokens saved vs. answer quality degradation. Typical results: Level 1 saves 30-50% tokens with <2% quality loss. Level 3 saves 70-80% but can cause 10-15% quality loss if not tuned carefully.",
        difficulty: "Hard",
        tags: ["Context Engineering", "Anthropic", "Compression"],
        quiz: {
          question: "In the Graduated Compression Pipeline, what does Level 4 'Agentic Compaction' mean?",
          options: ["Manual compression by engineers", "The agent has a compact_context() tool and DECIDES when and what to compress", "Automatic truncation at token limits", "Using a smaller model for compression"],
          correct: 1,
          explanation: "Agentic Compaction gives the agent self-awareness of its context — it can call compact_context() to proactively manage its own context window before hitting limits."
        }
      }
    ]
  },
  "System Design & Leadership": {
    icon: "🏗️", color: "#14B8A6", accent: "#0D9488", slug: "system-design",
    cards: [
      {
        id: "ls-1",
        q: "What is the 7-Layer AI Platform Reference Architecture?",
        a: "The 7-Layer AI Platform Stack:\n\n🔵 L1 — EXPERIENCE LAYER:\n• Web/Mobile UI, SSE/WebSocket for streaming\n• Auth (OAuth/OIDC), API Gateway\n\n🟢 L2 — API & ROUTING LAYER:\n• Model Router (selects optimal model per query)\n• Semantic Cache (avoid duplicate LLM calls)\n• Rate Limiting, Request Queuing\n\n🟡 L3 — GUARDRAILS LAYER:\n• Input Guards: PII detection, injection prevention\n• Output Guards: Hallucination check, toxicity filter\n• Compliance Rules: Domain-specific validators\n\n🔴 L4 — ORCHESTRATION LAYER:\n• Agent frameworks (LangGraph, CrewAI, Autogen)\n• Multi-agent coordination\n• Human-in-the-loop checkpoints\n• Tool/MCP server integration\n\n🟣 L5 — KNOWLEDGE LAYER:\n• Vector databases (pgvector, Pinecone)\n• Knowledge graphs (Neo4j)\n• Document stores (S3, GCS)\n• RAG pipeline components\n\n⚫ L6 — MODEL LAYER:\n• Foundation models (GPT-4, Claude, Gemini)\n• Fine-tuned domain models\n• Embedding models\n\n⬡ L7 — INFRASTRUCTURE LAYER:\n• GPU clusters, Kubernetes, Terraform\n• CI/CD, monitoring (LangSmith, W&B)\n• Cost management, auto-scaling",
        expertExp: "At a Fortune 100 financial institution, this 7-layer architecture is our actual production stack supporting 47 agents. Key insight: layers 2-3 (routing + guardrails) took 40% of our development effort but are the most critical for enterprise deployment. Without robust guardrails, the platform couldn't pass our internal security review. The model router alone saved $180K/year by routing simple queries to Haiku and complex ones to Opus.",
        aiRefExp: "The 7-layer architecture is a reference model — most enterprises implement 4-5 layers initially and expand. Recommended starting layers: L1 (Experience), L4 (Orchestration), L5 (Knowledge), L6 (Model). Add L2 (Routing) when you have multiple models, L3 (Guardrails) before any customer-facing deployment, and L7 (Infrastructure) when you self-host models. Typical build time: 6-12 months for a full production implementation with a team of 8-15 engineers.",
        difficulty: "Hard",
        tags: ["Architecture", "System Design", "Reference Architecture"],
        quiz: {
          question: "Which layer in the 7-Layer AI Platform handles model selection and semantic caching?",
          options: ["L1 - Experience Layer", "L2 - API & Routing Layer", "L4 - Orchestration Layer", "L6 - Model Layer"],
          correct: 1,
          explanation: "L2 (API & Routing Layer) contains the Model Router and Semantic Cache. The router selects the optimal model based on query complexity, cost, and latency requirements."
        }
      }
    ]
  },
  "Architecture Patterns": {
    icon: "🏛️", color: "#F97316", accent: "#EA580C", slug: "arch-patterns",
    cards: [
      {
        id: "ap-1",
        q: "Explain Event Sourcing and CQRS. When should you use them together?",
        a: "Event Sourcing + CQRS:\n\n📦 EVENT SOURCING:\n• Store state changes as a sequence of events (facts)\n• Current state = replay all events from the beginning\n• Events are immutable, append-only\n• Example: BankAccount events: [Opened($0), Deposited($100), Withdrawn($30)] → Balance: $70\n\n🔀 CQRS (Command Query Responsibility Segregation):\n• Separate Write model (Commands) from Read model (Queries)\n• Write side: Validates and stores events\n• Read side: Maintains optimized read projections\n• Can use different databases for each side\n\n🤝 WHY TOGETHER:\n• Event Sourcing provides the event log\n• CQRS provides optimized read views from those events\n• Write: Append events to event store\n• Read: Project events into denormalized read models\n\n✅ WHEN TO USE:\n• Audit trail requirements (financial, healthcare)\n• Complex domain with multiple read patterns\n• Event-driven microservices\n\n❌ WHEN NOT TO USE:\n• Simple CRUD applications\n• When eventual consistency is unacceptable",
        expertExp: "At a Fortune 100 financial institution, we implemented Event Sourcing + CQRS for our trade reconciliation platform. Every trade event (created, modified, settled, disputed) is stored as an immutable event. Read projections serve different consumers: the trading desk sees real-time positions, compliance sees audit trails, and risk management sees exposure calculations. The event store holds 2.3 billion events with 99.7% system uptime.",
        aiRefExp: "Event Sourcing + CQRS is one of the most powerful architectural patterns for financial systems but also one of the most complex to implement. Expect 3-6 months of development for a production system. Key challenges: (1) Event schema evolution — you'll need event upcasting as your domain evolves, (2) Projection rebuilds can take hours with large event stores, (3) Eventual consistency requires careful UX design. Tools: Axon Framework (Java), EventStoreDB, or custom implementation on top of Kafka/PostgreSQL.",
        difficulty: "Hard",
        tags: ["Event Sourcing", "CQRS", "Architecture"],
        quiz: {
          question: "What is the key benefit of Event Sourcing for financial systems?",
          options: ["Faster queries", "Complete, immutable audit trail — you can reconstruct the exact state at any point in time", "Simpler code", "Lower storage costs"],
          correct: 1,
          explanation: "Event Sourcing stores every state change as an immutable event. For financial/compliance systems, this provides a complete audit trail and the ability to replay history."
        }
      }
    ]
  },
  "Cloud & DevOps": {
    icon: "☁️", color: "#0891B2", accent: "#0E7490", slug: "cloud-devops",
    cards: [
      {
        id: "cd-1",
        q: "Explain Kubernetes architecture and key components. When to use K8s vs simpler alternatives?",
        a: "Kubernetes Architecture:\n\n🔵 CONTROL PLANE:\n• API Server: Central management point (RESTful API)\n• etcd: Distributed key-value store (cluster state)\n• Scheduler: Assigns pods to nodes based on resources\n• Controller Manager: Reconciliation loops (desired vs actual state)\n\n🟢 WORKER NODES:\n• Kubelet: Agent on each node, manages pods\n• Container Runtime: Docker, containerd, CRI-O\n• Kube-proxy: Network rules, service discovery\n\n📦 KEY ABSTRACTIONS:\n• Pod: Smallest deployable unit (1+ containers)\n• Service: Stable network endpoint for pods\n• Deployment: Declarative pod management + rolling updates\n• StatefulSet: For stateful applications (databases)\n• Ingress: HTTP routing and TLS termination\n• ConfigMap/Secret: Configuration management\n\n✅ USE K8s WHEN:\n• 10+ microservices\n• Multi-team development\n• Complex scaling requirements\n• Multi-cloud/hybrid strategy\n\n❌ SIMPLER ALTERNATIVES:\n• 1-3 services → Docker Compose\n• Serverless workloads → AWS Lambda/Cloud Run\n• Static sites → Vercel/Netlify",
        expertExp: "At a Fortune 100 financial institution, we run our AI platform on EKS (Elastic Kubernetes Service) with 3 node groups: CPU nodes for API services, GPU nodes (p4d.24xlarge) for model inference, and spot instances for batch processing. Key architecture decision: separate namespaces per team with resource quotas — prevents one team's runaway pod from starving others. Our cluster handles 150K pods across 200 nodes with 99.95% availability.",
        aiRefExp: "For AI/ML platforms, Kubernetes provides critical capabilities: GPU scheduling, auto-scaling based on inference queue depth, and blue-green deployments for model updates. However, the operational complexity is significant — budget 1-2 dedicated platform engineers for a production K8s cluster. For smaller teams (<10 engineers), consider managed alternatives: ECS Fargate (AWS), Cloud Run (GCP), or Azure Container Apps — they provide 80% of K8s benefits at 20% of the operational cost.",
        difficulty: "Hard",
        tags: ["Kubernetes", "DevOps", "Infrastructure"],
        quiz: {
          question: "What is the role of etcd in Kubernetes?",
          options: ["Container runtime", "Distributed key-value store that holds ALL cluster state and configuration", "Network proxy", "Log aggregator"],
          correct: 1,
          explanation: "etcd is the single source of truth for all cluster state. Every object (pods, services, configs) is stored in etcd. If etcd fails, the cluster loses its brain."
        }
      }
    ]
  },
  "API & Security Patterns": {
    icon: "🔐", color: "#BE185D", accent: "#9D174D", slug: "api-security",
    cards: [
      {
        id: "as-1",
        q: "Explain OAuth 2.0 flows. Which flow for which use case?",
        a: "OAuth 2.0 Flows:\n\n🔑 AUTHORIZATION CODE FLOW:\n• For: Server-side web apps\n• User → Auth Server → Code → Your Server → Token\n• Most secure — tokens never exposed to browser\n• Use PKCE extension for additional security\n\n📱 AUTHORIZATION CODE + PKCE:\n• For: SPAs and mobile apps\n• Same as above + code_verifier/code_challenge\n• Prevents authorization code interception\n• NOW RECOMMENDED for ALL client types\n\n🖥️ CLIENT CREDENTIALS:\n• For: Service-to-service (no user involved)\n• Your Service → Auth Server → Token\n• Machine-to-machine authentication\n\n❌ IMPLICIT FLOW (DEPRECATED):\n• Was for: Browser-based apps\n• Token directly in URL fragment\n• Security risk — use Auth Code + PKCE instead\n\n🔄 DEVICE AUTHORIZATION:\n• For: Input-limited devices (Smart TV, CLI)\n• Device shows code → User enters on phone → Token\n\n📊 DECISION MATRIX:\n• Web app with backend → Authorization Code\n• SPA/React app → Authorization Code + PKCE\n• Microservice → Client Credentials\n• CLI tool → Device Authorization",
        expertExp: "At a Fortune 100 financial institution, we enforce Authorization Code + PKCE for all applications (even server-side, as defense-in-depth). Client Credentials for service-to-service with automatic token rotation every 4 hours. Key incident: a developer team used Implicit flow for an internal dashboard — our security scan caught it and mandated migration to PKCE within 2 weeks. We integrated with Okta as our authorization server, supporting 15K+ internal users and 47 AI agent service accounts.",
        aiRefExp: "OAuth 2.0 implementation typically takes 1-2 weeks for basic flows, 4-6 weeks for a full enterprise setup including token refresh, rotation, scoped permissions, and audit logging. Key metrics: token lifetime should be 15-60 minutes (access) and 7-30 days (refresh). Monitor for: token reuse across different IPs (potential theft), excessive token refresh (potential automated attack), and failed authorization attempts (brute force). Budget: $0 for open-source (Keycloak) to $5-50K/year for managed (Auth0, Okta enterprise).",
        difficulty: "Medium",
        tags: ["OAuth", "Security", "Authentication"],
        quiz: {
          question: "Why is the Implicit flow deprecated and what replaced it?",
          options: ["It was too slow", "Tokens exposed in URL fragments are a security risk — replaced by Authorization Code + PKCE", "It didn't support refresh tokens", "It only worked with OAuth 1.0"],
          correct: 1,
          explanation: "Implicit flow returns tokens directly in the URL fragment, visible in browser history and logs. Authorization Code + PKCE keeps tokens server-side and prevents code interception attacks."
        }
      }
    ]
  },
  "Design Patterns": {
    icon: "🎨", color: "#84CC16", accent: "#65A30D", slug: "design-patterns",
    cards: [
      {
        id: "dp-1",
        q: "Explain the Strategy Pattern. When to use it and how does it compare to if/else chains?",
        a: "Strategy Pattern:\n\n🎯 INTENT:\n• Define a family of algorithms, encapsulate each one, and make them interchangeable\n• Let the algorithm vary independently from clients that use it\n\n🏗️ STRUCTURE:\n• Context: Holds a reference to a Strategy\n• Strategy Interface: Common interface for all algorithms\n• Concrete Strategies: Individual algorithm implementations\n\n📝 EXAMPLE — Payment Processing:\n• Strategy Interface: PaymentStrategy.process(amount)\n• Concrete: CreditCardPayment, PayPalPayment, CryptoPayment\n• Context: PaymentProcessor.setStrategy(strategy).pay(amount)\n\n✅ WHEN TO USE:\n• Multiple algorithms for the same task\n• Need to switch algorithms at runtime\n• Avoid complex conditional statements\n• Open/Closed Principle: Add new strategies without modifying existing code\n\n❌ WHEN NOT TO USE:\n• Only 2-3 simple variations (if/else is fine)\n• Strategies never change at runtime\n\n🔄 VS IF/ELSE:\n• If/else: Tight coupling, violates Open/Closed\n• Strategy: Loose coupling, each algorithm is independent\n• Strategy enables dependency injection and testing",
        expertExp: "At a Fortune 100 financial institution, we use the Strategy Pattern extensively in our AI platform. The Model Router IS a Strategy Pattern: ModelStrategy interface with implementations like ClaudeHaikuStrategy, GPT4Strategy, MixtralStrategy. The router selects the strategy based on query complexity, cost budget, and latency requirements. Adding a new model (e.g., Gemini) means adding ONE class — no changes to existing routing logic. This pattern has allowed us to swap models 12 times in 6 months without touching the core orchestration code.",
        aiRefExp: "The Strategy Pattern is one of the most frequently used patterns in AI/ML systems. Common applications: model selection (different models for different tasks), embedding strategies (different embedding models for different data types), chunking strategies (fixed-size vs semantic vs document-aware), and evaluation strategies (different metrics for different use cases). It's particularly powerful when combined with a factory or configuration-based selection. Best practice: include a 'metrics' method on each strategy that reports cost, latency, and quality for A/B comparison.",
        difficulty: "Medium",
        tags: ["Design Patterns", "Strategy", "GoF"],
        quiz: {
          question: "What principle does the Strategy Pattern primarily support?",
          options: ["Single Responsibility", "Open/Closed Principle — new strategies can be added without modifying existing code", "Liskov Substitution", "Interface Segregation"],
          correct: 1,
          explanation: "Strategy Pattern is a textbook example of the Open/Closed Principle — the system is open for extension (add new strategies) but closed for modification (existing strategies and the context remain unchanged)."
        }
      }
    ]
  }
};

// Helper: Get all cards flat
export const getAllCards = () => {
  return Object.entries(CATEGORIES).flatMap(([catName, cat]) =>
    cat.cards.map(card => ({ ...card, category: catName, categoryIcon: cat.icon, categoryColor: cat.color }))
  );
};

// Helper: Get total counts
export const getTotalCards = () => Object.values(CATEGORIES).reduce((s, c) => s + c.cards.length, 0);
export const getCategoryCount = () => Object.keys(CATEGORIES).length;

// Mock badges
export const BADGES = [
  { id: "first-card", name: "First Steps", icon: "🌱", description: "Study your first card", category: "milestone", earned: true },
  { id: "streak-7", name: "Week Warrior", icon: "🔥", description: "7-day study streak", category: "streak", earned: true },
  { id: "streak-30", name: "Monthly Master", icon: "💪", description: "30-day study streak", category: "streak", earned: false },
  { id: "rag-master", name: "RAG Architect", icon: "🔗", description: "Master all RAG cards", category: "domain", earned: false },
  { id: "security-master", name: "Security Guardian", icon: "🛡️", description: "Master all Security cards", category: "domain", earned: false },
  { id: "prompt-master", name: "Prompt Wizard", icon: "✨", description: "Master all Prompt Engineering cards", category: "domain", earned: true },
  { id: "quiz-ace", name: "Quiz Ace", icon: "🎯", description: "100% quiz accuracy in any category", category: "milestone", earned: false },
  { id: "agent-master", name: "Agent Commander", icon: "🤖", description: "Master all Agent & MCP cards", category: "domain", earned: false },
  { id: "full-stack", name: "Full Stack AI", icon: "🏆", description: "Master cards in 10+ categories", category: "milestone", earned: false },
  { id: "speed-demon", name: "Speed Demon", icon: "⚡", description: "Complete Daily 5 under 10 minutes", category: "milestone", earned: true },
];

// Mock daily activity data for heatmap (last 90 days)
export const generateMockActivity = () => {
  const activity = {};
  const today = new Date();
  for (let i = 0; i < 120; i++) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    const key = date.toISOString().split('T')[0];
    const rand = Math.random();
    if (rand > 0.3) {
      activity[key] = Math.floor(Math.random() * 45) + 5;
    }
  }
  return activity;
};

// Mock user stats
export const MOCK_USER_STATS = {
  totalXp: 4850,
  currentStreak: 23,
  longestStreak: 31,
  level: 12,
  totalCardsMastered: 42,
  totalReviews: 318,
  totalStudyMinutes: 1640,
  dailyActivity: generateMockActivity(),
};

// Mock ATS data
export const MOCK_ATS_REPORT = {
  overallScore: 62,
  keywordMatch: {
    matched: ["RAG", "LangChain", "Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "React", "TypeScript", "REST API", "Microservices"],
    missing: ["MCP", "A2A", "LangGraph", "Agentic AI", "vLLM", "FSRS", "AgentOps", "Model Armor", "RLHF", "DPO"],
    partial: ["Vector DB", "Prompt Engineering", "Fine-tuning", "MLOps", "Context Engineering"]
  },
  skillGaps: [
    { skill: "Agentic AI & MCP/A2A", priority: "critical", matchedCards: ["ai-35"] },
    { skill: "AI Security & Guardrails", priority: "critical", matchedCards: ["sec-4"] },
    { skill: "Context Engineering", priority: "high", matchedCards: ["ce-1"] },
    { skill: "LLM Serving & Optimization", priority: "high", matchedCards: ["ml-1"] },
    { skill: "Evaluation Frameworks", priority: "medium", matchedCards: ["ev-3"] },
  ],
};
