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

- Use AWS CLI credentials with EC2 permissions (the demo IAM user from step 1 only has ECR and S3 permissions). Configure the CLI and set your AWS region:
  ```bash
  aws configure
  export AWS_DEFAULT_REGION=us-east-1  # change to your region
  ```
- The following commands use the default VPC and create an Ubuntu 24.04 `t3.medium` instance, a key pair, and a security group. SSH is limited to your current public IP; the app port is public:
  ```bash
  KEY_NAME=medical-diagnostics-demo
  aws ec2 create-key-pair --key-name "$KEY_NAME" --query KeyMaterial --output text > "$KEY_NAME.pem"
  chmod 400 "$KEY_NAME.pem"

  VPC_ID=$(aws ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)
  SG_ID=$(aws ec2 create-security-group \
    --group-name medical-diagnostics-demo \
    --description "Medical diagnostics demo instance" \
    --vpc-id "$VPC_ID" \
    --query GroupId --output text)
  MY_IP=$(curl -fsS https://checkip.amazonaws.com | tr -d '\n')
  aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 22 --cidr "$MY_IP/32"
  aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 8501 --cidr 0.0.0.0/0

  # t3.medium is recommended. On a Free Tier account, list the allowed types and pick one:
  #   aws ec2 describe-instance-types --filters Name=free-tier-eligible,Values=true \
  #     --query 'InstanceTypes[].InstanceType' --output text
  # Use an x86 type (not t4g, which is ARM) because the AMI below is amd64.
  # On Free Tier, c7i-flex.large (4 GiB) or m7i-flex.large (8 GiB) is closest to t3.medium.
  INSTANCE_TYPE=t3.medium

  AMI_ID=$(aws ssm get-parameter \
    --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
    --query Parameter.Value --output text)
  INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --count 1 \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=medical-diagnostics-demo}]' \
    --query 'Instances[0].InstanceId' --output text)
  aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
  PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
  echo "Instance: $INSTANCE_ID  Public IP: $PUBLIC_IP"
  ```
- Connect over SSH and install Docker:
  ```bash
  ssh -i "$KEY_NAME.pem" "ubuntu@$PUBLIC_IP"
  ```
  Then run these commands on the EC2 instance:
  ```bash
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker ubuntu
  ```
  Reconnect over SSH for the Docker group change to take effect.
- These commands assume a default VPC. For another VPC, set `VPC_ID` to that VPC's ID and add `--subnet-id <subnet-id>` to `run-instances`. Keep the `.pem` file private; rerun the launch commands only after choosing new names or cleaning up the existing resources.

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
