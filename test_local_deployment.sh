#!/bin/bash
# Thin wrapper — implementation: scripts/shell/test_local_deployment.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/shell/test_local_deployment.sh" "$@"
