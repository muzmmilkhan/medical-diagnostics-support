# Deploying to AWS (ECR + EC2 + S3 + IAM) with a self-hosted runner

```
git push main ──► GitHub Actions CD (jobs run on the self-hosted runner on EC2)
                   ├─ CI (lint, tests, isolated compose smoke test)
                   ├─ build images ──► Amazon ECR       (IAM user medical-diagnostics-ci)
                   └─ deploy: docker compose pull && up (runs locally on the instance)
                                ├─ frontend (nginx :80) ──► backend (FastAPI :8000)
                                └─ backend ──► S3 uploads/ (IAM user medical-diagnostics-app)
                                           ──► OpenAI API
```

The runner only makes **outbound** HTTPS connections to GitHub, so no inbound SSH from GitHub is
needed, and GitHub stores no SSH key.

## 1. Create the AWS resources (one time)

Use your own admin AWS credentials locally (`aws configure` or `aws sso login`):

```bash
AWS_REGION=us-east-1 S3_BUCKET_NAME=<globally-unique-bucket> deploy/aws/bootstrap.sh
```

| Resource | Name | Purpose |
| --- | --- | --- |
| ECR repos | `medical-diagnostics-backend`, `medical-diagnostics-frontend` | Image registry, scan on push, keeps the last 20 images |
| S3 bucket | `$S3_BUCKET_NAME` | Archive of uploaded documents (`uploads/*`), public access blocked |
| IAM user | `medical-diagnostics-ci` | GitHub Actions. Can only push and pull the two ECR repos |
| IAM user | `medical-diagnostics-app` | Backend container. Can only Get/Put `s3://$S3_BUCKET_NAME/uploads/*` |

## 2. Launch the EC2 instance

- **AMI:** Amazon Linux 2023 (or Ubuntu).
- **Size:** at least `t3.medium` (4 GB). The runner also builds images and runs the tests, which a
  `t3.small` will struggle with. Use 30 GB or more of gp3 disk for images and build cache.
- **CPU:** if you pick Graviton (`t4g.*`, `m7g.*`), set the variable `DOCKER_PLATFORMS=linux/arm64`.
  The images are built on the runner, so a native build is fastest.
- **Security group, inbound:**
  - `80/tcp` from your users
  - `22/tcp` from **your IP only**, for admin access (or use SSM Session Manager and skip it)
  - Nothing is needed for GitHub.
- **Outbound:** allow HTTPS (the default allows everything). The runner needs github.com,
  `*.actions.githubusercontent.com`, ECR, S3 and api.openai.com.

## 3. Install Docker and the runner on the instance

```bash
# Copy the scripts and install Docker, Compose, Buildx and git
scp -i key.pem deploy/ec2/setup.sh deploy/ec2/install-runner.sh ec2-user@<host>:~
ssh -i key.pem ec2-user@<host> 'bash setup.sh'

# Get a one-hour registration token (run this on your laptop, inside the repo)
TOKEN=$(gh api -X POST "repos/{owner}/{repo}/actions/runners/registration-token" --jq .token)
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)

# Register the runner as a systemd service, labelled "production"
ssh -i key.pem ec2-user@<host> "RUNNER_TOKEN=$TOKEN bash install-runner.sh $REPO"
```

Check **Settings → Actions → Runners**. The runner should show as *Idle* with the labels
`self-hosted, Linux, X64, production`. It updates itself automatically.

### Which jobs run where

| Jobs | Default `runs-on` | Override with repository variable |
| --- | --- | --- |
| CI (backend, frontend, docker) and image publish | `["self-hosted","linux"]` | `CI_RUNS_ON` |
| Deploy | `["self-hosted","linux","production"]` | `DEPLOY_RUNS_ON` |

With a single runner on the EC2 instance, every job runs there. To keep builds off the production
box, register a second runner (for example with `RUNNER_LABELS=builder`) and set
`CI_RUNS_ON=["self-hosted","linux","builder"]`. To use GitHub-hosted runners for CI, set `CI_RUNS_ON="ubuntu-latest"`.

The CI smoke test uses its own compose project name and ports (18080/18000), so it can run
next to the live stack without touching its containers or the `vector_db` volume.

## 4. Configure GitHub secrets and variables

```bash
cp deploy/github/variables.env.example deploy/github/variables.env
$EDITOR deploy/github/variables.env              # region, bucket, ...
deploy/github/set-secrets.sh
```

The script creates the IAM access keys and pipes them straight into GitHub, so they never touch disk
or your screen. It also prompts (with hidden input) for the OpenAI key.

To set them by hand instead, go to **Settings → Secrets and variables → Actions**:

**Secrets**

| Name | Required | Value |
| --- | --- | --- |
| `AWS_ACCESS_KEY_ID` | yes | Access key of IAM user `medical-diagnostics-ci` |
| `AWS_SECRET_ACCESS_KEY` | yes | Secret key of IAM user `medical-diagnostics-ci` |
| `OPENAI_API_KEY` | yes | OpenAI API key used by the backend |
| `APP_AWS_ACCESS_KEY_ID` | for S3 | Access key of IAM user `medical-diagnostics-app` |
| `APP_AWS_SECRET_ACCESS_KEY` | for S3 | Secret key of IAM user `medical-diagnostics-app` |

**Variables** (non-secret; they can also be stored as secrets with the same name)

| Name | Default | Value |
| --- | --- | --- |
| `AWS_REGION` | — (required) | e.g. `us-east-1` |
| `S3_BUCKET_NAME` | unset → S3 disabled | Bucket from step 1 |
| `ECR_BACKEND_REPOSITORY` | `medical-diagnostics-backend` | |
| `ECR_FRONTEND_REPOSITORY` | `medical-diagnostics-frontend` | |
| `DOCKER_PLATFORMS` | `linux/amd64` | `linux/arm64` for Graviton |
| `OPENAI_MODEL` | `gpt-4o-mini` | |
| `CI_RUNS_ON` | `["self-hosted","linux"]` | Runner labels for CI and publish (JSON) |
| `DEPLOY_RUNS_ON` | `["self-hosted","linux","production"]` | Runner labels for deploy (JSON) |
| `DEPLOY_PATH` | `~/medical-diagnostics` | Absolute path for the live compose files |

The jobs that use secrets run in the `production` environment. You can store the secrets there, and add
required reviewers under **Settings → Environments → production** to approve each deploy.

## 5. Deploy

Push or merge to `main`, or push a `v1.2.3` tag. CD then:

1. Runs CI.
2. Builds both images and pushes them to ECR, tagged `<git-sha>` and `latest` (plus the version for tags).
3. On the production runner, writes `docker-compose.yml`, `.env` (image references) and `app.env`
   (backend config and secrets, mode 600) to `~/medical-diagnostics`. That directory is outside the runner
   workspace, so it survives workspace cleanup.
4. Runs `docker compose pull && up -d --wait`, checks `/api/v1/health`, and prunes images and build
   cache older than 7 days.

Open `http://<instance-public-dns>/`.

**Rollback:** re-run the CD workflow for an earlier commit, or SSH in, change the tags in
`~/medical-diagnostics/.env` to an older SHA, and run `docker compose up -d` in that directory.

## Self-hosted runner security

- **Keep the repository private.** A self-hosted runner executes whatever code a workflow checks out,
  and this one has Docker access (effectively root) on your production server. On a public repo,
  anyone could open a pull request that runs code on it. If the repo must be public, set
  `CI_RUNS_ON="ubuntu-latest"` so PR builds stay on GitHub-hosted runners, and set
  **Settings → Actions → General → Fork pull request workflows** to require approval.
- Only the `production` label runs deploys. Keep that label off any other runner.
- Workspaces persist between jobs. CD deletes the rendered secrets (`bundle/`) at the end of every run,
  and the ECR login is removed when the job ends.
- The runner runs as `ec2-user`, which is in the `docker` group. Don't run it as root.

## Hardening options

- **Use an IAM role instead of keys:** because the runner now lives on EC2, you can attach an
  instance profile with the ECR push policy and the `medical-diagnostics-s3-uploads` policy, then
  remove every `AWS_*` and `APP_AWS_*` secret. You'd also drop the `with:` keys from
  `configure-aws-credentials` (or remove that step).
- **HTTPS:** put an Application Load Balancer with an ACM certificate in front, or add Caddy/Traefik on the instance.
- **Rotate keys:** run `aws iam create-access-key` for the user, update the secret, then delete the old key.
- **Runner maintenance:** `sudo ~/actions-runner/svc.sh status`. Logs are in `~/actions-runner/_diag/`.
  To remove the runner, run `sudo ./svc.sh uninstall && ./config.sh remove --token <removal-token>`.
