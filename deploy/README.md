# Deploying to AWS (ECR + EC2 + S3 + IAM)

```
git push main ──► GitHub Actions CD
                   ├─ CI (lint, tests, compose smoke test)
                   ├─ build images ──► Amazon ECR  (IAM user medical-diagnostics-ci)
                   └─ SSH to EC2 ──► docker compose pull && up
                                       ├─ frontend (nginx :80) ──► backend (FastAPI :8000)
                                       └─ backend ──► S3 uploads/ (IAM user medical-diagnostics-app)
                                                  ──► OpenAI API
```

## 1. Create the AWS resources (one time)

Use your own admin AWS credentials locally (`aws configure` or `aws sso login`):

```bash
AWS_REGION=us-east-1 S3_BUCKET_NAME=<globally-unique-bucket> deploy/aws/bootstrap.sh
```

This creates the following:

| Resource | Name | Purpose |
| --- | --- | --- |
| ECR repos | `medical-diagnostics-backend`, `medical-diagnostics-frontend` | Image registry, scan on push, keeps the last 20 images |
| S3 bucket | `$S3_BUCKET_NAME` | Archive of uploaded documents (`uploads/*`), public access blocked |
| IAM user | `medical-diagnostics-ci` | GitHub Actions. Can only push and pull the two ECR repos |
| IAM user | `medical-diagnostics-app` | Backend container. Can only Get/Put `s3://$S3_BUCKET_NAME/uploads/*` |

## 2. Launch and prepare the EC2 instance

1. Launch an instance with Amazon Linux 2023 (or Ubuntu) and at least 2 GB RAM (for example `t3.small`), and attach a key pair.
   If you choose Graviton (`t4g.*`), set `DOCKER_PLATFORMS=linux/arm64`.
2. Security group inbound rules:
   - `80/tcp` from wherever users connect
   - `22/tcp` for SSH. GitHub-hosted runners use changing IP ranges, so this usually has to be
     `0.0.0.0/0` with key-only auth. To lock it down, use a self-hosted runner in the VPC instead.
3. Install Docker:
   ```bash
   scp -i key.pem deploy/ec2/setup.sh ec2-user@<host>:~
   ssh -i key.pem ec2-user@<host> 'bash setup.sh'
   ```

The instance needs no AWS credentials to pull images. CD pipes a short-lived ECR login token in over SSH.

## 3. Configure GitHub secrets and variables

```bash
gh auth login                                   # once
cp deploy/github/variables.env.example deploy/github/variables.env
$EDITOR deploy/github/variables.env             # region, bucket, EC2 host, ...
deploy/github/set-secrets.sh ~/path/to/key.pem
```

The script creates the IAM access keys and pipes them straight into GitHub, so they never touch disk
or your screen. It also prompts (with hidden input) for the OpenAI key.

To set things by hand instead, go to **Settings → Secrets and variables → Actions**:

**Secrets**

| Name | Required | Value |
| --- | --- | --- |
| `AWS_ACCESS_KEY_ID` | yes | Access key of IAM user `medical-diagnostics-ci` |
| `AWS_SECRET_ACCESS_KEY` | yes | Secret key of IAM user `medical-diagnostics-ci` |
| `OPENAI_API_KEY` | yes | OpenAI API key used by the backend |
| `EC2_SSH_PRIVATE_KEY` | yes | Full contents of the EC2 key pair `.pem` |
| `APP_AWS_ACCESS_KEY_ID` | for S3 | Access key of IAM user `medical-diagnostics-app` |
| `APP_AWS_SECRET_ACCESS_KEY` | for S3 | Secret key of IAM user `medical-diagnostics-app` |
| `EC2_SSH_KNOWN_HOSTS` | recommended | Output of `ssh-keyscan -H <host>`. Pins the host key |

**Variables** (non-secret; they can also be stored as secrets with the same name)

| Name | Default | Value |
| --- | --- | --- |
| `AWS_REGION` | — (required) | e.g. `us-east-1` |
| `EC2_HOST` | — (required) | Public DNS or Elastic IP of the instance |
| `EC2_USER` | `ec2-user` | `ubuntu` on Ubuntu AMIs |
| `S3_BUCKET_NAME` | unset → S3 disabled | Bucket from step 1 |
| `ECR_BACKEND_REPOSITORY` | `medical-diagnostics-backend` | |
| `ECR_FRONTEND_REPOSITORY` | `medical-diagnostics-frontend` | |
| `DOCKER_PLATFORMS` | `linux/amd64` | `linux/arm64` for Graviton |
| `OPENAI_MODEL` | `gpt-4o-mini` | |
| `DEPLOY_PATH` | `medical-diagnostics` | Directory on the instance (relative to home) |

Both workflow jobs run in the `production` environment. That means you can store these at the environment level
and add required reviewers under **Settings → Environments → production** if you want manual approval of deploys.

## 4. Deploy

Push or merge to `main`, or push a `v1.2.3` tag. The CD workflow then:

1. Runs CI.
2. Builds both images and pushes them to ECR, tagged `<git-sha>` and `latest` (plus the version for tags).
3. Copies `docker-compose.yml`, `.env` (image references) and `app.env` (backend config and secrets,
   mode 600) to `~/medical-diagnostics` on the instance.
4. Runs `docker compose pull && docker compose up -d --wait`, then checks `/api/v1/health`.

Open `http://<EC2_HOST>/`.

**Rollback:** re-run the CD workflow for an earlier commit, or SSH in, change the tags in `.env`
to an older SHA, and run `docker compose up -d`.

## Hardening options

- **Use an IAM role instead of app keys:** attach an instance profile that has the
  `medical-diagnostics-s3-uploads` policy, and leave out `APP_AWS_*`. boto3 picks up the role automatically.
- **Use GitHub OIDC instead of CI keys:** replace the access keys in `configure-aws-credentials` with
  `role-to-assume`, so no long-lived keys are stored in GitHub.
- **HTTPS:** put an Application Load Balancer with an ACM certificate in front, or add Caddy/Traefik on the instance.
- **Rotate keys:** run `aws iam create-access-key` for the user, update the secret, then delete the old key.
