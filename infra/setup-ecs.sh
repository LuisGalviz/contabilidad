#!/usr/bin/env bash
# ContaFlow – ECS + RDS one-time infrastructure setup
# Run with admin credentials: AWS_PROFILE=admin bash infra/setup-ecs.sh
set -euo pipefail

ACCOUNT_ID="317132222530"
REGION="us-east-1"
CLUSTER="contaflow"
SERVICE="contaflow-backend"
FAMILY="contaflow-backend"
IMAGE="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${SERVICE}:latest"
DB_INSTANCE="contaflow-db"
DB_NAME="contaflow"
DB_USER="contaflow"
DB_PASS="$(openssl rand -base64 32 | tr -d '/+=\n' | head -c 32)"

echo "=========================================="
echo " ContaFlow ECS infrastructure setup"
echo "=========================================="

# ── 1. IAM execution role ───────────────────────────────────────────────────
echo "[1/9] IAM execution role..."
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
  --region "$REGION" 2>/dev/null || echo "  role already exists"

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
  2>/dev/null || echo "  policy already attached"

aws iam put-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-name ssm-secrets \
  --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ssm:GetParameters\",\"ssm:GetParameter\"],\"Resource\":\"arn:aws:ssm:${REGION}:${ACCOUNT_ID}:parameter/contaflow/*\"}]}"

# ── 2. CloudWatch log group ─────────────────────────────────────────────────
echo "[2/9] CloudWatch log group..."
aws logs create-log-group \
  --log-group-name /ecs/contaflow-backend \
  --region "$REGION" 2>/dev/null || echo "  log group already exists"

aws logs put-retention-policy \
  --log-group-name /ecs/contaflow-backend \
  --retention-in-days 30 \
  --region "$REGION"

# ── 3. ECS cluster ──────────────────────────────────────────────────────────
echo "[3/9] ECS cluster..."
aws ecs create-cluster \
  --cluster-name "$CLUSTER" \
  --capacity-providers FARGATE FARGATE_SPOT \
  --region "$REGION" \
  --output json | python3 -c "import sys,json; c=json.load(sys.stdin)['cluster']; print(f\"  ARN: {c['clusterArn']}\")"

# ── 4. VPC / subnets ────────────────────────────────────────────────────────
echo "[4/9] VPC info..."
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query "Vpcs[0].VpcId" \
  --output text --region "$REGION")

SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=defaultForAz,Values=true" \
  --query "Subnets[*].SubnetId" \
  --output text --region "$REGION" | tr '\t' ',')

echo "  VPC: $VPC_ID"
echo "  Subnets: $SUBNET_IDS"

# ── 5. Security groups ──────────────────────────────────────────────────────
echo "[5/9] Security groups..."

ECS_SG=$(aws ec2 create-security-group \
  --group-name contaflow-ecs-sg \
  --description "ContaFlow ECS tasks" \
  --vpc-id "$VPC_ID" \
  --query "GroupId" --output text --region "$REGION" 2>/dev/null || \
  aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=contaflow-ecs-sg" "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[0].GroupId" --output text --region "$REGION")

RDS_SG=$(aws ec2 create-security-group \
  --group-name contaflow-rds-sg \
  --description "ContaFlow RDS" \
  --vpc-id "$VPC_ID" \
  --query "GroupId" --output text --region "$REGION" 2>/dev/null || \
  aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=contaflow-rds-sg" "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[0].GroupId" --output text --region "$REGION")

aws ec2 authorize-security-group-ingress \
  --group-id "$ECS_SG" --protocol tcp --port 8000 --cidr 0.0.0.0/0 \
  --region "$REGION" 2>/dev/null || true

aws ec2 authorize-security-group-ingress \
  --group-id "$RDS_SG" --protocol tcp --port 5432 \
  --source-group "$ECS_SG" --region "$REGION" 2>/dev/null || true

echo "  ECS SG: $ECS_SG"
echo "  RDS SG: $RDS_SG"

# ── 6. RDS subnet group ─────────────────────────────────────────────────────
echo "[6/9] RDS subnet group..."
SUBNET_ARRAY=$(echo "$SUBNET_IDS" | tr ',' ' ')
aws rds create-db-subnet-group \
  --db-subnet-group-name contaflow-subnet-group \
  --db-subnet-group-description "ContaFlow subnets" \
  --subnet-ids $SUBNET_ARRAY \
  --region "$REGION" 2>/dev/null || echo "  subnet group already exists"

# ── 7. RDS PostgreSQL ───────────────────────────────────────────────────────
echo "[7/9] RDS PostgreSQL (free tier, ~5 min)..."
aws rds create-db-instance \
  --db-instance-identifier "$DB_INSTANCE" \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version "16.4" \
  --master-username "$DB_USER" \
  --master-user-password "$DB_PASS" \
  --db-name "$DB_NAME" \
  --allocated-storage 20 \
  --storage-type gp2 \
  --vpc-security-group-ids "$RDS_SG" \
  --db-subnet-group-name contaflow-subnet-group \
  --no-publicly-accessible \
  --no-multi-az \
  --backup-retention-period 7 \
  --region "$REGION" 2>/dev/null || echo "  RDS instance already exists"

echo "  Waiting for RDS to become available (this takes 5-10 min)..."
aws rds wait db-instance-available \
  --db-instance-identifier "$DB_INSTANCE" \
  --region "$REGION"

DB_HOST=$(aws rds describe-db-instances \
  --db-instance-identifier "$DB_INSTANCE" \
  --query "DBInstances[0].Endpoint.Address" \
  --output text --region "$REGION")

DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASS}@${DB_HOST}:5432/${DB_NAME}"
echo "  Host: $DB_HOST"

# ── 8. SSM secrets ─────────────────────────────────────────────────────────
echo "[8/9] SSM Parameter Store secrets..."
APP_SECRET=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)

aws ssm put-parameter --name "/contaflow/DATABASE_URL"   --value "$DATABASE_URL"  --type SecureString --overwrite --region "$REGION"
aws ssm put-parameter --name "/contaflow/APP_SECRET_KEY" --value "$APP_SECRET"    --type SecureString --overwrite --region "$REGION"
aws ssm put-parameter --name "/contaflow/JWT_SECRET_KEY" --value "$JWT_SECRET"    --type SecureString --overwrite --region "$REGION"
echo "  Secrets stored in /contaflow/*"

# ── 9. Task definition + ECS service ───────────────────────────────────────
echo "[9/9] Task definition and ECS service..."
aws ecs register-task-definition \
  --family "$FAMILY" \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 512 \
  --memory 1024 \
  --execution-role-arn "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole" \
  --region "$REGION" \
  --container-definitions "[
    {
      \"name\": \"contaflow-backend\",
      \"image\": \"${IMAGE}\",
      \"portMappings\": [{\"containerPort\": 8000, \"protocol\": \"tcp\"}],
      \"essential\": true,
      \"secrets\": [
        {\"name\": \"DATABASE_URL\",   \"valueFrom\": \"/contaflow/DATABASE_URL\"},
        {\"name\": \"APP_SECRET_KEY\", \"valueFrom\": \"/contaflow/APP_SECRET_KEY\"},
        {\"name\": \"JWT_SECRET_KEY\", \"valueFrom\": \"/contaflow/JWT_SECRET_KEY\"}
      ],
      \"environment\": [
        {\"name\": \"APP_ENV\",   \"value\": \"production\"},
        {\"name\": \"APP_DEBUG\", \"value\": \"false\"}
      ],
      \"logConfiguration\": {
        \"logDriver\": \"awslogs\",
        \"options\": {
          \"awslogs-group\": \"/ecs/contaflow-backend\",
          \"awslogs-region\": \"${REGION}\",
          \"awslogs-stream-prefix\": \"ecs\"
        }
      },
      \"healthCheck\": {
        \"command\": [\"CMD-SHELL\", \"python3 -c 'import urllib.request; urllib.request.urlopen(\\\"http://localhost:8000/health\\\")' || exit 1\"],
        \"interval\": 30,
        \"timeout\": 10,
        \"retries\": 3,
        \"startPeriod\": 60
      }
    }
  ]" --output json | python3 -c "import sys,json; td=json.load(sys.stdin)['taskDefinition']; print(f\"  Task def: {td['family']}:{td['revision']}\")"

aws ecs create-service \
  --cluster "$CLUSTER" \
  --service-name "$SERVICE" \
  --task-definition "$FAMILY" \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_IDS}],securityGroups=[${ECS_SG}],assignPublicIp=ENABLED}" \
  --health-check-grace-period-seconds 90 \
  --region "$REGION" \
  --output json | python3 -c "import sys,json; s=json.load(sys.stdin)['service']; print(f\"  Service ARN: {s['serviceArn']}\")"

echo ""
echo "=========================================="
echo " Setup complete!"
echo " Cluster : $CLUSTER"
echo " Service : $SERVICE"
echo " DB Host : $DB_HOST"
echo " Logs    : /ecs/contaflow-backend (CloudWatch)"
echo ""
echo " Task public IP visible en:"
echo "   aws ecs list-tasks --cluster $CLUSTER --region $REGION"
echo " -> aws ecs describe-tasks --cluster $CLUSTER --tasks <task-id> --region $REGION"
echo "=========================================="
