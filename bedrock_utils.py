"""
Thin wrappers around AWS Bedrock services:
  - retrieve_from_kb  → Bedrock Knowledge Base (vector search)
  - claude_chat       → Claude 3.5 Sonnet via Bedrock Runtime
  - upload_to_s3      → S3 put-object
  - sync_knowledge_base → trigger KB re-ingestion after new uploads
"""

import json
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_PROFILE = os.getenv("AWS_PROFILE")
KB_ID = os.getenv("KB_ID")
CLAUDE_MODEL_ID = os.getenv("CLAUDE_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "data")
DS_ID = os.getenv("DS_ID", "")

_session_kwargs = {"region_name": AWS_REGION}
if AWS_PROFILE:
    _session_kwargs["profile_name"] = AWS_PROFILE

session = boto3.Session(**_session_kwargs)

bedrock_agent_rt = session.client("bedrock-agent-runtime")
bedrock_rt = session.client("bedrock-runtime")
s3_client = session.client("s3")
bedrock_agent = session.client("bedrock-agent")


# --- Bedrock Knowledge Base retrieval ---

def retrieve_from_kb(query: str, k: int = 5) -> list[dict]:
    """Retrieve the top-k chunks from the Bedrock Knowledge Base."""
    resp = bedrock_agent_rt.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": k}
        },
    )
    results = []
    for r in resp.get("retrievalResults", []):
        text = r.get("content", {}).get("text", "")
        score = r.get("score", 0.0)
        uri = (r.get("location", {}).get("s3Location", {}).get("uri", "")
               or r.get("location", {}).get("uri", ""))
        results.append({"text": text, "score": round(float(score), 4), "uri": uri})
    return results


# --- Claude chat via Bedrock Runtime ---

def claude_chat(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """Send a prompt to Claude via Bedrock and return the text response."""
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ],
    }
    if system:
        body["system"] = system

    resp = bedrock_rt.invoke_model(
        modelId=CLAUDE_MODEL_ID,
        body=json.dumps(body),
    )
    payload = json.loads(resp["body"].read())
    parts = payload.get("content", [])
    return "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()


# --- S3 upload ---

def upload_to_s3(file_bytes: bytes, filename: str) -> str:
    """Upload a file to the S3 data folder and return the S3 key."""
    key = f"{S3_PREFIX}/{filename}" if S3_PREFIX else filename
    s3_client.put_object(Bucket=S3_BUCKET, Key=key, Body=file_bytes)
    return key


# --- Knowledge Base sync ---

def sync_knowledge_base() -> str | None:
    """Trigger a KB re-ingestion job. Returns the ingestion job ID or None."""
    if not DS_ID:
        return None
    resp = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=KB_ID,
        dataSourceId=DS_ID,
    )
    return resp.get("ingestionJob", {}).get("ingestionJobId")
