# Arquitectura AWS — ContaFlow

> Fecha: junio 2026  
> Región: us-east-1 (N. Virginia)

---

## Visión general

ContaFlow tiene dos capas de infraestructura:

- **Frontend**: desplegado en Vercel (fuera de AWS), servidor de Next.js
- **Backend**: desplegado en AWS, contenedor Docker corriendo en ECS Fargate

El browser del usuario nunca habla directamente con AWS. Todas las llamadas a la API pasan primero por Vercel, que las redirige al backend. Esto evita problemas de mixed content (el browser usa HTTPS con Vercel; Vercel habla HTTP con AWS server-to-server).

```
Usuario (browser)
    │  HTTPS
    ▼
Vercel (Next.js)
    │  rewrite: /api/v1/* → BACKEND_URL/api/v1/*
    │  HTTP server-to-server
    ▼
ECS Fargate (FastAPI · puerto 8000)
    │                    │
    ▼                    ▼
RDS PostgreSQL     CloudWatch Logs
```

---

## Servicios AWS y por qué se usa cada uno

### ECR — Elastic Container Registry

Repositorio privado de imágenes Docker dentro de AWS.

**Por qué:** ECS necesita descargar la imagen del backend desde algún lugar. ECR es la opción natural porque está en la misma cuenta de AWS — la autenticación es automática mediante el rol de ejecución de ECS, sin credenciales adicionales, y la transferencia de datos entre ECR y ECS es gratuita dentro de la misma región.

**Repositorio:** `contaflow-backend`  
**Tags:** `:latest` (siempre el más reciente) + `:<git-sha>` (uno por cada deploy)

**Problema pendiente:** no hay lifecycle policy. Con cada deploy se acumula una imagen nueva con el tag del commit SHA. Hay que agregar una política que mantenga solo las últimas N imágenes para evitar costos crecientes de almacenamiento.

---

### ECS Fargate — Elastic Container Service

Servicio que corre contenedores Docker sin gestionar servidores.

**Por qué:** es la forma más simple de correr el backend en producción. Se define cuánta CPU y RAM necesita el contenedor y AWS gestiona el servidor físico, el sistema operativo y los parches de seguridad.

**Por qué Fargate y no EC2:** con EC2 habría que mantener instancias, instalar Docker, configurar el SO y aplicar parches de seguridad manualmente. Fargate es serverless — se paga por segundo de ejecución.

**Por qué no Lambda:** el backend es una API FastAPI con conexiones persistentes a PostgreSQL. Lambda está diseñado para funciones sin estado de corta duración y no es compatible sin modificaciones significativas.

**Configuración actual:**

| Parámetro | Valor |
|---|---|
| Cluster | `contaflow` |
| Servicio | `contaflow-backend` |
| CPU | 512 units (0.5 vCPU) |
| Memoria | 1024 MB |
| Desired count | 1 tarea |
| Launch type | Fargate |
| Puerto | 8000 |
| IP pública | Asignada automáticamente |

**Variables de entorno del contenedor:**

| Variable | Valor |
|---|---|
| `APP_ENV` | `production` |
| `DATABASE_URL` | connection string a RDS (desde GitHub Secret) |
| `APP_SECRET_KEY` | clave de firma de la app (desde GitHub Secret) |
| `JWT_SECRET_KEY` | clave de firma de tokens JWT (desde GitHub Secret) |

**Nota:** los secrets se pasan como env vars directamente en el task definition. Esto significa que son visibles en la consola de AWS para cualquiera con acceso a ECS. Una mejora futura sería usar AWS Secrets Manager o SSM Parameter Store.

---

### RDS PostgreSQL — Relational Database Service

Base de datos PostgreSQL gestionada por AWS.

**Por qué:** el backend necesita una base de datos relacional persistente. RDS gestiona backups automáticos, parches del motor y disponibilidad. La alternativa de correr PostgreSQL dentro del contenedor de ECS perdería todos los datos en cada deploy o reinicio.

**Por qué PostgreSQL:** el ORM del backend (SQLAlchemy con driver `asyncpg`) está configurado para Postgres, y se usan tipos específicos como `JSONB`.

**Configuración actual:**

| Parámetro | Valor |
|---|---|
| Identifier | `contaflow-db` |
| Engine | PostgreSQL 16.4 |
| Instancia | db.t3.micro |
| Storage | 20 GB gp2 |
| Backups | 1 día de retención |
| Multi-AZ | No (single-AZ) |
| Acceso público | Sí (`publicly-accessible = true`) |
| Security group | `contaflow-rds-sg` — 5432 solo desde `contaflow-ecs-sg` |

**Sobre la retención de 1 día:** el plan Free Tier actual de AWS rechaza valores mayores con `FreeTierRestrictionError`. Al salir del Free Tier conviene subirla a 7.

**Migraciones:** el contenedor no las aplica al arrancar. El deploy ejecuta `alembic upgrade head` como tarea ECS puntual antes de rotar el servicio; si falla, el deploy se aborta y el servicio anterior sigue en pie.

**Problema de seguridad:** RDS está configurado como `publicly-accessible`, lo que significa que tiene una IP pública y es accesible desde internet. Está protegido solo por usuario y contraseña. Una mejora futura sería ponerlo en una subnet privada y permitir solo conexiones desde el security group de ECS.

---

### CloudWatch Logs

Sistema centralizado de logs de AWS.

**Por qué:** cuando el contenedor en Fargate imprime algo a stdout/stderr ese output desaparece si no hay un sistema de logs. CloudWatch lo captura automáticamente gracias al driver `awslogs` configurado en el task definition. Los logs son visibles en la consola de AWS en tiempo real.

**Log group:** `/ecs/contaflow-backend`

**Problema pendiente:** el log group no tiene política de retención. Los logs se acumulan indefinidamente. AWS cobra por almacenamiento de logs después del free tier. Hay que configurar retención de 30 días.

---

### IAM — Identity and Access Management

Sistema de permisos de AWS. Controla quién puede hacer qué.

Se usan dos entidades IAM con propósitos distintos:

#### Usuario: `contaflow-backend`

Usado por GitHub Actions para hacer deploys. Sus credenciales (`AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`) están guardadas como GitHub Secrets y el CI las usa para autenticarse en AWS.

**Estado actual:** tiene `AdministratorAccess` — acceso total a toda la cuenta de AWS.

**Estado objetivo (hay que aplicar):** política mínima con solo los permisos que el CI realmente necesita:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECR",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:CreateRepository",
        "ecr:DescribeRepositories",
        "ecr:PutLifecyclePolicy",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECS",
      "Effect": "Allow",
      "Action": [
        "ecs:CreateCluster",
        "ecs:RegisterTaskDefinition",
        "ecs:RunTask",
        "ecs:DescribeServices",
        "ecs:UpdateService",
        "ecs:CreateService",
        "ecs:ListTasks",
        "ecs:DescribeTasks"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:CreateSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:DescribeNetworkInterfaces"
      ],
      "Resource": "*"
    },
    {
      "Sid": "RDS",
      "Effect": "Allow",
      "Action": ["rds:DescribeDBInstances"],
      "Resource": "*"
    },
    {
      "Sid": "IAM",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::<ACCOUNT_ID>:role/contaflow-exec-role"
    },
    {
      "Sid": "Logs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:PutRetentionPolicy"],
      "Resource": "arn:aws:logs:us-east-1:<ACCOUNT_ID>:log-group:/ecs/contaflow-backend"
    }
  ]
}
```

#### Rol: `contaflow-exec-role`

Usado por ECS **en runtime**, mientras el contenedor está corriendo. Nadie lo asume manualmente — lo asume automáticamente el servicio `ecs-tasks.amazonaws.com`.

**Trust policy:**
```json
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "ecs-tasks.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

**Política adjunta:** `AmazonECSTaskExecutionRolePolicy` (AWS managed)
- Permite descargar imágenes de ECR
- Permite escribir logs a CloudWatch

**Historia:** el rol original `ecsTaskExecutionRole` tenía una trust policy corrupta que no se podía actualizar sin `iam:UpdateAssumeRolePolicy`. Se creó este rol nuevo desde cero para evitar ese problema.

---

### VPC y red

Se usa la **Default VPC** de AWS en us-east-1. Es la opción más simple para empezar — AWS la crea automáticamente con subnets públicas en cada zona de disponibilidad, sin configuración adicional.

**Implicación:** tanto ECS como RDS tienen IPs públicas. Esto simplifica la configuración pero expone los servicios a internet. En una arquitectura más madura, ECS y RDS estarían en subnets privadas con un load balancer como único punto de entrada.

**Security Group:** `contaflow-ecs-sg`

| Dirección | Protocolo | Puerto | Origen |
|---|---|---|---|
| Ingress | TCP | 8000 | 0.0.0.0/0 (cualquier IP) |
| Egress | Todo | Todo | 0.0.0.0/0 |

---

## Flujo de un deploy

```
git push master
      │
      ▼
GitHub Actions (CI/CD)
  │
  ├─ Job: backend  → ruff + mypy + pytest
  ├─ Job: frontend → type-check + lint + build
  │
  └─ Job: deploy-backend  (solo si master y no PR)
        │
        ├─ docker build → imagen production
        ├─ docker push → ECR :latest + :<sha>
        ├─ aws ecs register-task-definition (nueva revisión)
        ├─ aws ecs update-service → reemplaza el contenedor en ejecución
        ├─ aws ecs wait services-stable
        ├─ detecta la IP pública de la nueva tarea (ENI → EC2 describe-network-interfaces)
        └─ actualiza BACKEND_URL en Vercel (proyecto `contabilidad`) y redespliega el frontend
```

El deploy es **rolling** — ECS lanza el nuevo contenedor, espera que esté healthy, y solo entonces detiene el anterior. Con `desired_count=1` hay un breve momento de downtime durante el cambio.

**Por qué el paso de `BACKEND_URL`:** no hay load balancer delante de ECS, así que cada tarea nueva recibe una IP pública distinta (ver sección VPC más abajo). El frontend en Vercel usa `BACKEND_URL` como destino del rewrite `/api/v1/*` (`frontend/next.config.ts`). Sin actualizarla en cada deploy, la IP queda obsoleta y todas las llamadas a la API devuelven 502 hasta el siguiente deploy manual. Este paso automatiza esa actualización — es un parche sobre la arquitectura actual, no la solución de raíz (que sería un Application Load Balancer con DNS estable delante de ECS).

**Permisos IAM adicionales que requiere este paso** (sobre la política mínima ya descrita más abajo): `ecs:ListTasks`, `ecs:DescribeTasks`, `ec2:DescribeNetworkInterfaces`.

**Secrets de GitHub Actions adicionales:** `VERCEL_TOKEN` (token de acceso personal de Vercel con permiso sobre el proyecto `contabilidad`).

---

## Costos estimados

| Servicio | Costo/mes | Free tier |
|---|---|---|
| ECS Fargate (0.5 vCPU · 1 GB · 24/7) | ~$5 | Gratis 12 meses (límites menores) |
| RDS db.t3.micro + 20 GB | ~$14 | Gratis 12 meses |
| ECR storage | ~$0.10/GB | 500 MB gratis |
| CloudWatch Logs | ~$0.03/GB almacenado | 5 GB gratis |
| Transferencia de datos | Mínima | 1 GB gratis |

**Total estimado fuera de free tier:** ~$19-25/mes

---

## Pendientes de seguridad y costos

| # | Problema | Impacto | Dificultad |
|---|---|---|---|
| 1 | `AdministratorAccess` en usuario CI | Crítico (seguridad) | Baja |
| 2 | ECR sin lifecycle policy | Medio (costo creciente) | Baja |
| 3 | CloudWatch sin retención | Bajo (costo creciente) | Baja |
| 4 | RDS `publicly-accessible` | Medio (seguridad) | Media |
| 5 | Secrets en env vars del task | Bajo (visibles en consola) | Media |
