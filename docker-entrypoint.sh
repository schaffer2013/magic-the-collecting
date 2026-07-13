#!/usr/bin/env sh
set -eu

mkdir -p "${RAW_IMAGE_DIR:-/app/data/raw-images}"

if [ "${DB_AUTO_MIGRATE:-true}" != "false" ] && [ "${DB_AUTO_MIGRATE:-true}" != "0" ]; then
  python -m registration_service.migrate
fi

exec "$@"
