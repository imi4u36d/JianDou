#!/bin/sh
set -eu

cat > /usr/share/nginx/html/runtime-config.json <<EOF
{
  "apiBaseUrl": "${JIANDOU_PUBLIC_API_BASE_URL:-/api/v2}",
  "storageBaseUrl": "${JIANDOU_PUBLIC_STORAGE_BASE_URL:-/storage}"
}
EOF
