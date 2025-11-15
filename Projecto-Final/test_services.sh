#!/usr/bin/env bash
set -euo pipefail


AIRFLOW_URL=${AIRFLOW_URL:-http://localhost:8080}
MLFLOW_URL=${MLFLOW_URL:-http://localhost:5001}     # <-- AJUSTADO A 5001
MINIO_API_URL=${MINIO_API_URL:-http://localhost:9000}
MINIO_CONSOLE_URL=${MINIO_CONSOLE_URL:-http://localhost:9001}

RAW_DB_CONT=${RAW_DB_CONT:-raw-db}
RAW_DB=${RAW_DB:-raw_data}
RAW_USER=${RAW_USER:-raw_user}

CLEAN_DB_CONT=${CLEAN_DB_CONT:-clean-db}
CLEAN_DB=${CLEAN_DB:-clean_data}
CLEAN_USER=${CLEAN_USER:-clean_user}

AIRFLOW_WS=${AIRFLOW_WS:-airflow-webserver}
AIRFLOW_SCHED=${AIRFLOW_SCHED:-airflow-scheduler}
MLFLOW_CONT=${MLFLOW_CONT:-mlflow}
MINIO_CONT=${MINIO_CONT:-minio}

echo -e "Verificando servicios Proyecto 3..."

GREEN='\033[0;32m'; RED='\033[0;31m'; YEL='\033[1;33m'; DIM='\033[2m'; NC='\033[0m'
ok(){   echo -e "${GREEN}✔ $1${NC}"; }
warn(){ echo -e "${YEL}⚠ $1${NC}"; }
fail(){ echo -e "${RED}✗ $1${NC}"; }


check_container () {
  local name=$1
  printf "%-28s" "Container ${name}"
  if docker compose ps --format '{{.Name}}:{{.State}}' | grep -q "^${name}:"; then
    local state
    state=$(docker compose ps --format '{{.Name}}:{{.State}}' | awk -F: -v c="$name" '$1==c{print $2}')
    if [[ "$state" == "running" || "$state" == "healthy" ]]; then ok "$state"; else warn "$state"; fi
  else
    fail "not found"
  fi
}

http_code () {
  # $1=url  $2=method(GET|POST)
  local url="$1" method="${2:-GET}"
  if [[ "$method" == "POST" ]]; then
    curl -sS -o /dev/null -w "%{http_code}" -X POST "$url" || echo 000
  else
    curl -sS -o /dev/null -w "%{http_code}" "$url" || echo 000
  fi
}

print_http () {
  # $1=label  $2=code  $3=expected
  local label="$1" code="$2" expected="${3:-200}"
  if [[ "$code" == "$expected" ]]; then
    printf "%-25s ${GREEN}✓ HTTP %s${NC}\n" "$label" "$code"
  elif [[ "$code" == "000" || "$code" == "000000" ]]; then
    printf "%-25s ${RED}✗ HTTP %s (no conecta)${NC}\n" "$label" "$code"
  else
    printf "%-25s ${YEL}! HTTP %s (esperado %s)${NC}\n" "$label" "$code" "$expected"
  fi
}

check_http () {
  # $1=label  $2=url  $3=expected  $4=method
  local label="$1" url="$2" expected="$3" method="${4:-GET}"
  local code
  code=$(http_code "$url" "$method")
  print_http "$label" "$code" "$expected"
}

psql_raw ()   { docker compose exec -T "$RAW_DB_CONT"   psql -U "$RAW_USER"   -d "$RAW_DB"   -v ON_ERROR_STOP=1 -c "$1"; }
psql_clean () { docker compose exec -T "$CLEAN_DB_CONT" psql -U "$CLEAN_USER" -d "$CLEAN_DB" -v ON_ERROR_STOP=1 -c "$1"; }


echo -e "${DIM}Comprobando servicios...${NC}"

echo "Containers"
check_container "$RAW_DB_CONT"
check_container "$CLEAN_DB_CONT"
check_container "$MINIO_CONT"
check_container "$MLFLOW_CONT"
check_container "$AIRFLOW_WS"
check_container "$AIRFLOW_SCHED"
echo

echo "HTTP endpoints"
check_http "Airflow UI"      "${AIRFLOW_URL}/health"                   "200" "GET"
check_http "MLflow UI"       "${MLFLOW_URL}/"                          "200" "GET"
check_http "MinIO API"       "${MINIO_API_URL}/minio/health/ready"     "200" "GET"
check_http "MinIO Console"   "${MINIO_CONSOLE_URL}/"                   "200" "GET"
echo

echo "Airflow sanity"
printf "%-28s" "DAGs present"
if docker compose exec -T "$AIRFLOW_WS" airflow dags list | grep -E '1_raw_batch_ingest_15k|2_clean_build|train_and_register' >/dev/null; then
  ok "found expected DAGs"
else
  fail "expected DAGs not found"
fi
echo

echo "Postgres RAW"
if psql_raw "SELECT COUNT(*) AS total_raw FROM diabetic_raw;" >/dev/null 2>&1; then
  psql_raw "SELECT COUNT(*) AS total_raw FROM diabetic_raw;"
  psql_raw "SELECT batch_id, COUNT(*) AS rows FROM diabetic_raw GROUP BY batch_id ORDER BY batch_id;"
else
  fail "RAW queries failed"
fi
echo

echo "Postgres CLEAN"
if psql_clean "SELECT COUNT(*) AS total_clean FROM clean_data.diabetic_clean;" >/dev/null 2>&1; then
  psql_clean "SELECT COUNT(*) AS total_clean FROM clean_data.diabetic_clean;"
  psql_clean "SELECT batch_id, split, COUNT(*) AS rows FROM clean_data.diabetic_clean GROUP BY batch_id, split ORDER BY batch_id, split;"
  psql_clean "SELECT split, COUNT(*) AS rows, ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER(),2) AS pct FROM clean_data.diabetic_clean GROUP BY split ORDER BY split;"
else
  fail "CLEAN queries failed (¿schema/table creados?)"
fi
echo

echo "MLflow"

printf "%-28s" "UI reachable"
check_http "MLflow UI" "${MLFLOW_URL}" "200" "GET"
echo

echo "MinIO"
printf "%-28s" "Health /ready"
if docker compose exec -T "$MINIO_CONT" curl -s -f http://localhost:9000/minio/health/ready >/dev/null; then
  ok "ready"
else
  fail "not ready"
fi
echo

echo "Done"
read -p "Terminado. Presiona Enter para salir..."
