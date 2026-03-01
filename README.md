# South Park RAG App — AWS Edition

A Retrieval-Augmented Generation (RAG) web application about the TV show **South Park**, built with Flask and AWS-native services.

## Project Goal

Course assignment: build a RAG application that connects to AWS services (Bedrock, OpenSearch, S3) and uses Claude as the AI model, with a custom UI/UX layer.

The topic chosen is **South Park** — the knowledge base contains detailed information about characters, episodes, creators, the town, specials, the movie, video games, music, controversies, recurring themes, and celebrity appearances.

## Architecture

```
User Question
     │
     ▼
Flask API (/api/ask)
     │
     ├── 1. Hebrew? → Claude translates to English
     │
     ├── 2. Bedrock Knowledge Base retrieves top-5 chunks
     │       (Titan Embeddings → OpenSearch Serverless k-NN)
     │
     └── 3. Claude generates grounded answer from context
```

### AWS Services Used

| Service | Role |
|---------|------|
| **Bedrock Knowledge Base** | Automated ingestion pipeline: reads .txt files from S3, chunks them, embeds with Titan Embeddings V2 (1024-dim), and indexes into OpenSearch Serverless |
| **Bedrock Runtime** | Invokes Claude 3.5 Haiku for answer generation and Hebrew translation |
| **OpenSearch Serverless** | Vector store with k-NN index — managed entirely by the Knowledge Base |
| **S3** | Stores the source .txt documents (`s3://rag-class-docs-yrokach/data/`) |
| **EC2** | Hosts the Dockerized Flask app with Gunicorn |

### Why Not SQS / Worker?

The original assignment spec included SQS + an EC2 worker for event-driven ingestion (S3 → SQS → Worker → embed → OpenSearch). However, **Bedrock Knowledge Base** handles this entire pipeline automatically — it reads from S3, chunks, embeds, and indexes with a single "Sync" button. Adding SQS and a custom worker would duplicate what the managed service already provides, so we opted for the simpler architecture.

## Project Structure

```
rag_app_aws/
├── app.py              # Flask API: routes (/health, /api/ask)
├── bedrock_utils.py    # AWS wrappers: retrieve_from_kb(), claude_chat()
├── index.html          # Frontend UI (South Park themed)
├── style.css           # Styling (snow, mountains, character badges)
├── scripts/
│   └── smoke_test.py   # Endpoint tests (health, ask EN/HE, validation)
├── Dockerfile          # Production image with Gunicorn
├── requirements.txt    # flask, boto3, python-dotenv, gunicorn
├── .env                # AWS config (not committed)
├── .gitignore
└── .dockerignore
```

## Knowledge Base Data

12 topic files uploaded to S3, covering:

| File | Content |
|------|---------|
| `south_park_overview.txt` | Show history, creation, awards |
| `south_park_characters.txt` | Stan, Kyle, Cartman, Kenny, and more |
| `south_park_episodes.txt` | Season-by-season episode summaries |
| `south_park_iconic_episodes.txt` | Most famous episodes in detail |
| `south_park_creators.txt` | Trey Parker & Matt Stone |
| `south_park_town_and_setting.txt` | The fictional town of South Park |
| `south_park_specials_and_movie.txt` | Bigger Longer & Uncut, Paramount+ specials |
| `south_park_video_games.txt` | Stick of Truth, Fractured But Whole, etc. |
| `south_park_music.txt` | Songs, albums, musical episodes |
| `south_park_controversies_and_culture.txt` | Censorship, cultural impact |
| `south_park_recurring_themes.txt` | Satire patterns, running gags |
| `south_park_celebrities_and_guests.txt` | Celebrity appearances and parodies |

## Environment Variables

Create a `.env` file (not committed to git):

```
AWS_REGION=us-east-1
AWS_PROFILE=course          # local dev only; leave empty on EC2
KB_ID=<your-knowledge-base-id>
CLAUDE_MODEL_ID=us.anthropic.claude-3-5-haiku-20241022-v1:0
```

- **Local dev**: `AWS_PROFILE` points to a named AWS CLI profile with Bedrock permissions.
- **EC2**: credentials come from the instance's IAM role, so `AWS_PROFILE` is left empty.

## How to Run

### Local Development

```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
```

### Docker

```bash
# Build
docker build -t rag-app-aws .

# Run (pass .env at runtime — never bake secrets into the image)
docker run -p 5000:5000 --env-file .env rag-app-aws
```

### Smoke Test

```bash
python scripts/smoke_test.py http://localhost:5000
```

Tests: health check, HTML page, English question, Hebrew question, empty input validation.

### EC2 Deployment

```bash
# Build for x86 (if on Apple Silicon)
docker build --platform linux/amd64 -t yrokach/rag-app-aws .
docker push yrokach/rag-app-aws

# On EC2
docker pull yrokach/rag-app-aws
docker run -d -p 80:5000 --env-file .env --restart unless-stopped yrokach/rag-app-aws
```

## Features

- **Bilingual**: supports English and Hebrew queries (auto-detected, translated for retrieval, answered in original language)
- **Grounded answers**: Claude only uses retrieved context, no hallucination
- **Source transparency**: each answer shows the retrieved chunks with relevance scores
- **South Park themed UI**: custom sign, character badges, snow animation, mountain silhouette
- **Production-ready**: Gunicorn WSGI server, Docker containerization

## Tech Stack

- **Backend**: Python 3.12, Flask, boto3
- **LLM**: Claude 3.5 Haiku via Amazon Bedrock
- **Embeddings**: Titan Text Embeddings V2 (managed by Bedrock KB)
- **Vector Store**: Amazon OpenSearch Serverless (managed by Bedrock KB)
- **Data Store**: Amazon S3
- **Deployment**: Docker, Gunicorn, EC2
