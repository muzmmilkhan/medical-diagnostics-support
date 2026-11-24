#!/usr/bin/env bash
# One-time AWS setup: ECR repositories, S3 bucket, and two least-privilege IAM users.
#   <prefix>-ci  : used by GitHub Actions to push images to ECR (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)
#   <prefix>-app : used by the backend on EC2 to write uploads to S3 (APP_AWS_ACCESS_KEY_ID / ...)
#
# Usage (with admin AWS credentials configured locally):
#   AWS_REGION=us-east-1 S3_BUCKET_NAME=my-unique-bucket deploy/aws/bootstrap.sh
# Safe to re-run: existing resources are kept, policies are updated.
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION, e.g. us-east-1}"
: "${S3_BUCKET_NAME:?Set S3_BUCKET_NAME (must be globally unique)}"
PREFIX=${PREFIX:-medical-diagnostics}
BACKEND_REPO=${ECR_BACKEND_REPOSITORY:-$PREFIX-backend}
FRONTEND_REPO=${ECR_FRONTEND_REPOSITORY:-$PREFIX-frontend}
CI_USER=${CI_USER:-$PREFIX-ci}
APP_USER=${APP_USER:-$PREFIX-app}

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account $ACCOUNT_ID, region $AWS_REGION"

echo "==> ECR repositories"
LIFECYCLE='{"rules":[{"rulePriority":1,"description":"Keep the 20 most recent images","selection":{"tagStatus":"any","countType":"imageCountMoreThan","countNumber":20},"action":{"type":"expire"}}]}'
for repo in "$BACKEND_REPO" "$FRONTEND_REPO"; do
  if aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$repo" >/dev/null 2>&1; then
    echo "  exists:  $repo"
  else
    aws ecr create-repository --region "$AWS_REGION" --repository-name "$repo" \
      --image-scanning-configuration scanOnPush=true >/dev/null
    echo "  created: $repo"
  fi
  aws ecr put-lifecycle-policy --region "$AWS_REGION" --repository-name "$repo" \
    --lifecycle-policy-text "$LIFECYCLE" >/dev/null
done

echo "==> S3 bucket"
if aws s3api head-bucket --bucket "$S3_BUCKET_NAME" >/dev/null 2>&1; then
  echo "  exists:  $S3_BUCKET_NAME"
else
  if [ "$AWS_REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$S3_BUCKET_NAME" --region "$AWS_REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$S3_BUCKET_NAME" --region "$AWS_REGION" \
      --create-bucket-configuration "LocationConstraint=$AWS_REGION" >/dev/null
  fi
  echo "  created: $S3_BUCKET_NAME"
fi
aws s3api put-public-access-block --bucket "$S3_BUCKET_NAME" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "==> IAM users and policies"
ensure_user() {
  if aws iam get-user --user-name "$1" >/dev/null 2>&1; then
    echo "  exists:  $1"
  else
    aws iam create-user --user-name "$1" >/dev/null
    echo "  created: $1"
  fi
}

ECR_ARN="arn:aws:ecr:$AWS_REGION:$ACCOUNT_ID:repository"
CI_POLICY=$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "EcrAuth", "Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*" },
    {
      "Sid": "EcrPushPull",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:CompleteLayerUpload",
        "ecr:DescribeImages", "ecr:DescribeRepositories", "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload", "ecr:PutImage", "ecr:UploadLayerPart"
      ],
      "Resource": ["$ECR_ARN/$BACKEND_REPO", "$ECR_ARN/$FRONTEND_REPO"]
    }
  ]
}
JSON
)

APP_POLICY=$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "UploadsReadWrite",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::$S3_BUCKET_NAME/uploads/*"
    }
  ]
}
JSON
)

ensure_user "$CI_USER"
aws iam put-user-policy --user-name "$CI_USER" --policy-name "$PREFIX-ecr-push" \
  --policy-document "$CI_POLICY"
ensure_user "$APP_USER"
aws iam put-user-policy --user-name "$APP_USER" --policy-name "$PREFIX-s3-uploads" \
  --policy-document "$APP_POLICY"

cat <<DONE

Done. Next:
  1. Put these in deploy/github/variables.env:
       AWS_REGION=$AWS_REGION
       S3_BUCKET_NAME=$S3_BUCKET_NAME
       ECR_BACKEND_REPOSITORY=$BACKEND_REPO
       ECR_FRONTEND_REPOSITORY=$FRONTEND_REPO
  2. Run deploy/github/set-secrets.sh <ec2-key.pem>. It creates access keys for
     $CI_USER and $APP_USER and stores them directly in GitHub Secrets.
DONE
