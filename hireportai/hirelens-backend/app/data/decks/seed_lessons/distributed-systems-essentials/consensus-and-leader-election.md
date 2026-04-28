---
slug: consensus-and-leader-election
title: Consensus and Leader Election
display_order: 0
quiz_items:
  - question: 'Why does Raft require a majority quorum for both elections and log commits, and what concrete failure does that prevent?'
    answer: 'A majority (N/2 + 1) on each operation guarantees that any two committed states must overlap on at least one node — that overlap node holds the truth and can serialize any future leader. Without it, two minority partitions could each elect a leader and commit conflicting writes; on heal, neither side knows which timeline survived (split-brain). Majority quorum makes split-brain impossible by construction.'
    question_type: free_text
    difficulty: hard
    display_order: 0
  - question: 'In Raft, which event triggers a follower to become a candidate?'
    answer: 'The election timeout fires without receiving a heartbeat from the current leader'
    question_type: mcq
    distractors:
      - 'A client sends a write request directly to the follower'
      - 'The follower observes a higher log index in another replica'
      - 'The cluster configuration changes by adding a new member'
    difficulty: medium
    display_order: 1
---
## Concept

Consensus is the protocol by which a group of nodes agrees on an
ordered log of operations even when some of them are dead, slow, or
lying. Raft and Paxos both reduce the problem to two questions: who is
the leader, and which log entries are durable.

Raft's design choice that pays back forever: separate the term
(monotonic election counter) from the log index. A candidate becomes
leader when it wins a majority vote in a new term; a log entry is
"committed" when a majority of replicas have stored it.

## Production

Three pitfalls dominate operating Raft-based systems:

1. **Asymmetric network partitions.** If A can talk to B but not C, and
   B can talk to both, the lonely node A may stay convinced it's
   leader. Pre-vote or check-quorum mitigates this — the candidate
   pings a majority before incrementing the term.
2. **Disk fsync latency.** Raft's safety hinges on the leader
   persisting log entries before acknowledging. A slow disk on the
   leader stalls the whole cluster; production deploys use NVMe.
3. **Membership changes.** Adding/removing nodes mid-flight is the
   one operation Raft does poorly out of the box; joint consensus is
   subtle, easy to mis-implement.

```python
# Pseudocode — the heart of follower → candidate transition.
async def follower_loop(self):
    while True:
        timeout = jittered(150, 300)  # ms
        msg = await self.recv(timeout)
        if msg is None:
            self.term += 1
            self.role = "candidate"
            await self.start_election()
            return
```

## Examples

| System    | Consensus       | Notes                                |
|-----------|-----------------|--------------------------------------|
| etcd      | Raft            | Backbone of Kubernetes control plane |
| Spanner   | Multi-Paxos     | Per-Paxos-group; TrueTime for order  |
| Kafka     | KRaft (Raft)    | Replaced ZooKeeper; per-partition    |
| Consul    | Raft            | Service discovery + KV               |

Production lesson: never run a 2-node Raft cluster. Quorum is 2 of 2 —
a single node failure halts the cluster. Three nodes tolerate one
failure; five tolerate two.
