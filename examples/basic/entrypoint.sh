#!/bin/sh
set -eu

echo "waiting for the database"
/opt/app/wait-for-db

"$@"
