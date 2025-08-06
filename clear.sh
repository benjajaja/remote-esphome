#!/usr/bin/env bash
set -euo pipefail

echo "Getting retained entities..."
timeout 2 mosquitto_sub -h ops -t "homeassistant/#" -v > retained.txt && true
echo "retained devices:"
cat retained.txt
cat retained.txt |   grep -o '^homeassistant/[^ ]*' |   sort -u |   xargs -I{} mosquitto_pub -h ops -t "{}" -n -r
rm retained.txt
