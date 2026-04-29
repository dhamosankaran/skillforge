"""Background jobs package — RQ-on-Redis workers (Phase 6 slice 6.10).

Locked decision: G2 (RQ for ingestion in slice 6.10; same primitive
reused by slice 6.14's daily Pro digest). Slice 6.10a ships the package
marker only; the worker entry point (`ingestion_worker.py`) lands with
B-083b alongside `ingestion_service`.
"""
