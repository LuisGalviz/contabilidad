#!/usr/bin/env bash
# ContaFlow – abre el puerto 5432 del RDS solo para tu IP pública actual.
#
# Como la IP de desarrollo cambia (no siempre se conecta desde el mismo
# lugar), este script revoca la regla que dejó la última corrida y agrega
# una nueva para la IP de hoy — nunca deja el security group abierto a
# 0.0.0.0/0. Córrelo cada vez que vayas a usar DataGrip (o cualquier
# cliente SQL) desde una red distinta.
#
# Uso: ./infra/rds-dev-access.sh
set -euo pipefail

REGION="us-east-1"
DB_INSTANCE="contaflow-db"
STATE_FILE="$(dirname "$0")/.rds-dev-access-ip"
DESCRIPTION="dev-access-dynamic"

CURRENT_IP="$(curl -s https://checkip.amazonaws.com | tr -d '[:space:]')"
if [[ -z "$CURRENT_IP" ]]; then
  echo "No se pudo determinar la IP pública actual." >&2
  exit 1
fi

SG_ID="$(aws rds describe-db-instances \
  --db-instance-identifier "$DB_INSTANCE" \
  --region "$REGION" \
  --query "DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId" \
  --output text)"

if [[ -f "$STATE_FILE" ]]; then
  PREVIOUS_IP="$(cat "$STATE_FILE")"
  if [[ -n "$PREVIOUS_IP" && "$PREVIOUS_IP" != "$CURRENT_IP" ]]; then
    echo "Revocando acceso previo desde ${PREVIOUS_IP}/32..."
    aws ec2 revoke-security-group-ingress \
      --group-id "$SG_ID" \
      --protocol tcp --port 5432 \
      --cidr "${PREVIOUS_IP}/32" \
      --region "$REGION" 2>/dev/null || echo "  (no había regla activa para esa IP, sigo)"
  fi
fi

echo "Autorizando acceso desde ${CURRENT_IP}/32 en ${SG_ID}:5432..."
aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --ip-permissions "IpProtocol=tcp,FromPort=5432,ToPort=5432,IpRanges=[{CidrIp=${CURRENT_IP}/32,Description=${DESCRIPTION}}]" \
  --region "$REGION" 2>/dev/null || echo "  (la regla ya existía, sigo)"

echo "$CURRENT_IP" > "$STATE_FILE"

echo ""
echo "Listo. Acceso habilitado desde ${CURRENT_IP} hasta la próxima corrida de este script."
echo "Host RDS: $(aws rds describe-db-instances --db-instance-identifier "$DB_INSTANCE" --region "$REGION" --query 'DBInstances[0].Endpoint.Address' --output text):5432"
