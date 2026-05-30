#!/usr/bin/env bash
set -euo pipefail

FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
QA_SEED_USER="${QA_SEED_USER:-compose-qa-seed}"
QA_SEED_PASSWORD="${QA_SEED_PASSWORD:-local-qa-seed-12345}"
QA_SEED_DISPLAY_NAME="${QA_SEED_DISPLAY_NAME:-Compose QA Seed}"
QA_SEED_INCLUDE_UNKNOWN="${QA_SEED_INCLUDE_UNKNOWN:-true}"

COOKIE_JAR="$(mktemp "${TMPDIR:-/tmp}/studyflow-qa-seed-cookies.XXXXXX")"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/studyflow-qa-seed-files.XXXXXX")"

cleanup() {
  rm -f "$COOKIE_JAR"
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

json_escape() {
  python3 -c 'import json, sys; print(json.dumps(sys.argv[1]))' "$1"
}

register_user() {
  local payload
  payload="$(
    printf '{"username":%s,"password":%s,"display_name":%s,"email":%s}' \
      "$(json_escape "$QA_SEED_USER")" \
      "$(json_escape "$QA_SEED_PASSWORD")" \
      "$(json_escape "$QA_SEED_DISPLAY_NAME")" \
      "$(json_escape "$QA_SEED_USER@example.com")"
  )"

  local status
  status="$(
    curl -sS -o "$WORK_DIR/register-response.json" -w "%{http_code}" \
      -X POST "$BACKEND_URL/api/auth/register" \
      -H "content-type: application/json" \
      -d "$payload"
  )"

  if [[ "$status" == "201" ]]; then
    echo "Registered local QA user: $QA_SEED_USER"
    return
  fi

  if [[ "$status" == "409" ]]; then
    echo "Using existing local QA user: $QA_SEED_USER"
    return
  fi

  echo "Register failed with HTTP $status" >&2
  sed -n '1,20p' "$WORK_DIR/register-response.json" >&2
  exit 1
}

login_user() {
  local payload
  payload="$(
    printf '{"username":%s,"password":%s}' \
      "$(json_escape "$QA_SEED_USER")" \
      "$(json_escape "$QA_SEED_PASSWORD")"
  )"

  local status
  status="$(
    curl -sS -o "$WORK_DIR/login-response.json" -w "%{http_code}" \
      -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
      -X POST "$FRONTEND_URL/api/auth/login" \
      -H "content-type: application/json" \
      -d "$payload"
  )"

  if [[ "$status" != "200" ]]; then
    echo "Login through frontend proxy failed with HTTP $status" >&2
    sed -n '1,20p' "$WORK_DIR/login-response.json" >&2
    exit 1
  fi

  echo "Logged in through frontend proxy."
}

write_seed_file() {
  local filename="$1"
  local content="$2"
  printf '%s\n' "$content" > "$WORK_DIR/$filename"
}

upload_with_type() {
  local filename="$1"
  local material_type="$2"
  local status

  status="$(
    curl -sS -o "$WORK_DIR/$filename.response.json" -w "%{http_code}" \
      -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
      -X POST "$FRONTEND_URL/api/materials/upload" \
      -F "file=@$WORK_DIR/$filename;type=text/plain" \
      -F "material_type=$material_type"
  )"

  if [[ "$status" != "201" && "$status" != "200" ]]; then
    echo "Upload failed for $filename ($material_type) with HTTP $status" >&2
    sed -n '1,40p' "$WORK_DIR/$filename.response.json" >&2
    exit 1
  fi

  echo "Uploaded $filename as $material_type"
}

upload_without_type() {
  local filename="$1"
  local status

  status="$(
    curl -sS -o "$WORK_DIR/$filename.response.json" -w "%{http_code}" \
      -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
      -X POST "$FRONTEND_URL/api/materials/upload" \
      -F "file=@$WORK_DIR/$filename;type=text/plain"
  )"

  if [[ "$status" != "201" && "$status" != "200" ]]; then
    echo "Upload failed for $filename without material_type with HTTP $status" >&2
    sed -n '1,40p' "$WORK_DIR/$filename.response.json" >&2
    exit 1
  fi

  echo "Uploaded $filename without material_type for legacy/unknown label QA"
}

print_materials_summary() {
  echo
  echo "Bounded /api/materials response:"
  curl -sS -c "$COOKIE_JAR" -b "$COOKIE_JAR" "$FRONTEND_URL/api/materials"
  echo
}

require_command curl
require_command python3

cat <<EOF
Seeding local Compose QA materials.
Frontend URL: $FRONTEND_URL
Backend URL:  $BACKEND_URL
User:         $QA_SEED_USER

This creates local/internal QA files only. It does not run OCR, edital analysis,
question generation, simulado execution, progress mutation, or scheduling.
EOF

register_user
login_user

write_seed_file "qa-edital.txt" "Edital de QA. Conteúdo mínimo para validar classificação como edital."
write_seed_file "qa-material-estudo.txt" "Material de estudo de QA. Conteúdo mínimo para validar agrupamento."
write_seed_file "qa-prova-anterior.txt" "Prova anterior de QA. Conteúdo mínimo para validar agrupamento."
write_seed_file "qa-bibliografia.txt" "Bibliografia de QA. Conteúdo mínimo para validar agrupamento."
write_seed_file "qa-anotacao.txt" "Anotação de QA. Conteúdo mínimo para validar agrupamento."
write_seed_file "qa-tipo-nao-informado.txt" "Material legado de QA. Conteúdo mínimo para validar tipo não informado."

upload_with_type "qa-edital.txt" "edital"
upload_with_type "qa-material-estudo.txt" "study_material"
upload_with_type "qa-prova-anterior.txt" "previous_exam"
upload_with_type "qa-bibliografia.txt" "bibliography"
upload_with_type "qa-anotacao.txt" "note"

if [[ "$QA_SEED_INCLUDE_UNKNOWN" == "true" ]]; then
  upload_without_type "qa-tipo-nao-informado.txt"
fi

print_materials_summary

cat <<EOF

Next browser QA routes:
- $FRONTEND_URL/materials
- $FRONTEND_URL/editais
- $FRONTEND_URL/study
- $FRONTEND_URL/pscpp
- $FRONTEND_URL/materials/upload

Note: rerunning this script creates additional QA materials for the same user.
Use docker compose down -v only when you intentionally want to delete the
persistent local QA volume.
EOF
