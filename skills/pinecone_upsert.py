#!/usr/bin/env /tmp/pinecone-env/bin/python3
"""
pinecone_upsert.py — Upsert session summary to Pinecone agent-memory index.
Called by save-state Step 11. Reads session log content and embeddings from args.
Usage: python3 pinecone_upsert.py <session_summary> <project_slug> <session_date>
"""

import sys, json, os
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY") or "pcsk_2n7kbA_9FVTjwimy6rtGuVX2Sz4WoSqg7zzWb7amTvnSnk3ASWytfcDLeMmfewXq2Umahh"
INDEX_NAME = "agent-memory"
MODEL_NAME = "intfloat/e5-large-v2"

def upsert_session(project_slug: str, session_date: str, session_log: str,
                   decisions: str, next_action: str, blockers: str,
                   mid_flight: str, status: str):
    pc = Pinecone(api_key=PINECONE_API_KEY)
    idx = pc.Index(INDEX_NAME)

    model = SentenceTransformer(MODEL_NAME)

    # Build the canonical session document (passage form for e5)
    doc_text = f"""Session Summary — {project_slug} — {session_date}

Status: {status}
Next Action: {next_action}
Blockers: {blockers}
Mid-Flight: {mid_flight}

Decisions:
{decisions}

Session Log:
{session_log}"""

    # Embed it
    emb = model.encode(
        ["passage: " + doc_text],
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0].tolist()

    # Upsert with composite ID for dedup
    record_id = f"session-{project_slug}-{session_date.replace(' ', '-').replace(':', '-')}"
    idx.upsert(vectors=[{
        "id": record_id,
        "values": emb,
        "metadata": {
            "project": project_slug,
            "session_date": session_date,
            "status": status,
            "next_action": next_action[:300],
            "blockers": blockers[:500],
            "doc_text": doc_text[:2000],
        }
    }])

    stats = idx.describe_index_stats()
    print(f"Pinecone upsert OK — {stats.total_vector_count} total vectors in index")
    return record_id

if __name__ == "__main__":
    args = json.loads(sys.argv[1])  # JSON blob from Step 11
    rec_id = upsert_session(**args)
    print(f"Upserted record: {rec_id}")
