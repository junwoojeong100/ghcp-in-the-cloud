#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP}"
: "${IMAGE_NAME:?Set IMAGE_NAME to an image accessible by Azure}"
: "${FOUNDRY_RESOURCE:?Set FOUNDRY_RESOURCE}"

if [[ -z "${ANTHROPIC_FOUNDRY_API_KEY:-}" ]]; then
  read -rsp "Microsoft Foundry API key: " ANTHROPIC_FOUNDRY_API_KEY
  printf '\n'
  export ANTHROPIC_FOUNDRY_API_KEY
fi
if [[ -z "${DEMO_PASSWORD:-}" ]]; then
  read -rsp "Password for the demo UI (user: demo): " DEMO_PASSWORD
  printf '\n'
  export DEMO_PASSWORD
fi

parameters_file="$(mktemp)"
chmod 600 "$parameters_file"
trap 'rm -f "$parameters_file"; unset ANTHROPIC_FOUNDRY_API_KEY DEMO_PASSWORD' EXIT

python3 - "$parameters_file" <<'PY'
import json
import os
import sys

parameters = {
    "imageName": {"value": os.environ["IMAGE_NAME"]},
    "foundryResource": {"value": os.environ["FOUNDRY_RESOURCE"]},
    "foundryApiKey": {"value": os.environ["ANTHROPIC_FOUNDRY_API_KEY"]},
    "demoPassword": {"value": os.environ["DEMO_PASSWORD"]},
}
with open(sys.argv[1], "w", encoding="utf-8") as file:
    json.dump(
        {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
            "contentVersion": "1.0.0.0",
            "parameters": parameters,
        },
        file,
    )
PY

az deployment group create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file "$(dirname "${BASH_SOURCE[0]}")/../infra/aca/main.bicep" \
  --parameters "@$parameters_file"
