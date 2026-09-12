#!/bin/sh
set -eu

echo "running migrations"
/usr/local/bin/migrate

"$@"
