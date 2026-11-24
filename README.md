# Medical Diagnostics Support Application (demo)

Upload medical documents (PDF or TXT), then ask questions about them. The answers come from an LLM
that only uses the content of your documents. This technique is called **RAG** (Retrieval-Augmented Generation).

## How it works

```
 Streamlit UI  ──HTTP──►  FastAPI backend  ──►  OpenAI (embeddings + chat)
 (frontend)               │
                          ├──► Chroma vector DB   (stores document chunks)
                          └──► Amazon S3          (stores the original files)
```

1. **Upload:** the backend splits the file into chunks, turns each chunk into an embedding
   (a list of numbers that captures its meaning), and saves them in Chroma. The original file goes to S3.
2. **Ask:** the backend finds the chunks most similar to the question and sends them, with the question, to the LLM.
   The LLM writes the answer from those chunks.

## Project structure

```
backend/                      FastAPI API (managed with uv)
  app/main.py                 creates the app
  app/routes.py               the endpoints: /health, /upload, /query
  app/config.py               settings from environment variables
  app/services/
    document_loader.py        PDF/TXT -> text chunks
    vector_store.py           save and search chunks in Chroma
    llm_service.py            answer questions with OpenAI
    storage_service.py        save uploaded files to S3
  Dockerfile
frontend/                     Streamlit UI (managed with uv)
  app.py
  Dockerfile
docker-compose.yml            runs backend + frontend together
.github/workflows/deploy.yml  CI/CD: build, push to ECR, run on EC2
data/Diabetes.pdf             sample document to try
```

## Run locally

```bash
cp .env.example .env          # then put your OPENAI_API_KEY in .env
```

**With Docker:**

```bash
docker compose up --build
```

**Without Docker** (needs [uv](https://docs.astral.sh/uv/)), in two terminals:

```bash
cd backend  && uv run uvicorn app.main:app --reload
cd frontend && uv run streamlit run app.py
```

Then open:
- App: http://localhost:8501
- API docs: http://localhost:8000/docs

## Deploy to AWS

On every push to `main`, GitHub Actions does the following on your EC2 instance:
**get the code → log in to AWS → build the images → push them to ECR → start the app.**

### 1. AWS setup (one time)

Use the AWS Console, or these AWS CLI commands:

```bash
# Image registry (ECR)
aws ecr create-repository --repository-name medical-diagnostics-backend
aws ecr create-repository --repository-name medical-diagnostics-frontend

# S3 bucket for uploaded files (the name must be globally unique)
aws s3 mb s3://<your-bucket-name>

# IAM user that GitHub Actions and the app will use
aws iam create-user --user-name medical-diagnostics-demo
aws iam attach-user-policy --user-name medical-diagnostics-demo \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
aws iam attach-user-policy --user-name medical-diagnostics-demo \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam create-access-key --user-name medical-diagnostics-demo   # copy AccessKeyId + SecretAccessKey
```

### 2. EC2 instance

- Launch an **Ubuntu** instance (`t3.medium` recommended).
- In the security group, allow inbound port **8501** (the app) and **22** (SSH, from your IP).
- Install Docker:
  ```bash
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker ubuntu     # then log out and back in
  ```

### 3. Self-hosted GitHub runner (on the EC2 instance)

In GitHub, go to **Settings → Actions → Runners → New self-hosted runner → Linux**, and run the
commands it shows on the EC2 instance. Then make the runner start automatically:

```bash
sudo ./svc.sh install && sudo ./svc.sh start
```

### 4. GitHub secrets

In GitHub, go to **Settings → Secrets and variables → Actions → New repository secret**, and add:

| Secret | Value |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | from step 1 |
| `AWS_SECRET_ACCESS_KEY` | from step 1 |
| `AWS_REGION` | e.g. `us-east-1` |
| `S3_BUCKET_NAME` | your bucket name |
| `OPENAI_API_KEY` | your OpenAI key |
| `BASE_URL` | *optional*: OpenAI-compatible API URL. Skip it to use OpenAI directly |

### 5. Deploy

```bash
git push origin main
```

Watch it in the **Actions** tab, then open `http://<EC2-public-IP>:8501`.

> This is a demo setup. For production, you would use separate IAM users with fewer
> permissions, HTTPS, and authentication.
