---
slug: scaling-stateful-services
title: Scaling Stateful Services
display_order: 1
quiz_items:
  - question: 'Why is sharding by user_id usually the right primary partitioning key for a social-feed service, and when does it break?'
    answer: 'user_id co-locates a user reads alongside their writes (timeline, drafts, settings) so single-user requests stay on one shard with no cross-shard joins. It breaks when access patterns become global — search, trending, content recommendation. Those workloads need a secondary partitioning by content_id or by time-bucket, often via a separate read replica or specialized index store rather than the primary OLTP shards.'
    question_type: free_text
    difficulty: hard
    display_order: 0
  - question: 'What three layers should a stateful service ladder through as it scales from one node to many?'
    answer: 'Single primary with read replicas → consistent-hash-sharded primaries → multi-region replication. Each step adds operational complexity and weakens the consistency guarantees you can offer; only step up when the previous layer is genuinely saturated.'
    question_type: free_text
    difficulty: medium
    display_order: 1
---
## Concept

The single hardest question in system design is when to shard. Sharding
multiplies operational complexity (failover, rebalancing,
cross-shard transactions, schema migrations) and changes the
consistency story for every endpoint. The interview-quality answer is
to defer sharding until the data clearly does not fit one node.

A stateful service ladders through three layers:

1. **Single primary + read replicas.** Cheap, simple, strong
   consistency for writes. Caps at the largest box you can afford for
   the primary.
2. **Consistent-hash-sharded primaries.** Each shard has its own write
   throughput; reads stay shard-local for single-key access.
3. **Multi-region replication.** Latency optimization, disaster
   recovery; conflict resolution becomes a design surface.

## Production

Pick the partitioning key by reading the access pattern, not the
schema:

- **user_id** when most queries are scoped to one user (feeds, chat,
  email).
- **org_id / tenant_id** in B2B SaaS where users belong to one
  organization and cross-org reads are rare.
- **time bucket** for append-only timeseries (events, logs, metrics).

Cross-shard reads are the operator's nightmare — fan-out latency, hot
shards under skewed traffic, painful migrations when one tenant grows
10x. Keep them rare.

## Examples

| Service         | Partition key       | Cross-shard fallback   |
|-----------------|---------------------|------------------------|
| WhatsApp        | conversation_id     | offline message queue  |
| Stripe          | account_id          | reporting OLAP store   |
| GitHub          | repository_id       | search via Elastic     |
| Discord guilds  | guild_id            | bot index in Redis     |

The pattern: OLTP shards stay narrow and fast; cross-cutting reads go
to a denormalized read store updated via change-data-capture.
