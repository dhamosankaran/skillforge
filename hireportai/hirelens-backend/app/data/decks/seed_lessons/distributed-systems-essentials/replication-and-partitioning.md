---
slug: replication-and-partitioning
title: Replication and Partitioning
display_order: 1
quiz_items:
  - question: 'A team is choosing between leader-follower (single primary) and multi-leader (multi-primary) replication. What is the single most important question to ask before deciding?'
    answer: 'How will writes from different leaders be reconciled when they conflict? Multi-leader replication only works if you have a defensible answer — last-write-wins, CRDTs, application-level merge logic. If the answer is "we will avoid conflicts" the architecture is fragile; if the answer is "conflicts are impossible by partitioning" you actually want sharded leader-follower, not multi-leader.'
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: 'What is the simplest reason to prefer range partitioning over hash partitioning?'
    answer: 'Range partitioning preserves the natural ordering of keys, which is essential when reads are dominated by range scans (timeseries, logs, ordered IDs). Hash partitioning gives better load distribution but makes range queries fan out across all shards.'
    question_type: free_text
    difficulty: easy
    display_order: 1
---
## Concept

Replication and partitioning are the two axes of distributed data
storage. Replication is about copies — multiple nodes hold the same
data, for durability and read scaling. Partitioning is about splits —
each node holds a different slice of the data, for write scaling.

Most production systems do both: each partition (shard) is replicated
across N nodes, and the cluster has many partitions. The replication
strategy within a partition is usually leader-follower (one writer);
the partitioning strategy across the cluster is hash, range, or
directory-based.

## Production

The decision tree:

- **Leader-follower replication** is the default. Strong consistency on
  writes, easy mental model for reads (with optional read-your-writes).
- **Multi-leader replication** is for offline-first apps and
  geo-distributed writes — almost never the right choice for
  server-side OLTP. Requires real conflict-resolution logic.
- **Leaderless (Dynamo-style)** is for very high write throughput with
  weak consistency tolerance — Cassandra, DynamoDB, ScyllaDB. The
  application has to handle quorum reads and read-repair.

For partitioning:

- **Hash** for even load on uniform-access data.
- **Range** for ordered scans and timeseries.
- **Directory** when access patterns are skewed — keep a metadata table
  that maps key → shard and rebalance hot keys explicitly.

## Examples

| System    | Replication      | Partitioning  |
|-----------|------------------|---------------|
| Postgres  | Leader-follower  | (single node) |
| MongoDB   | Replica set      | Hash or range |
| Cassandra | Leaderless       | Hash          |
| TiDB      | Raft per region  | Range         |
| DynamoDB  | Leaderless       | Hash          |

The reason real systems combine these: a single-shard replica set
gives strong consistency at small scale; sharded replica sets give
write throughput; leaderless gives ultra-high availability at the cost
of operator-visible inconsistency windows.
