#!/bin/bash
# Thin wrapper — implementation: scripts/shell/test_api_complete.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/shell/test_api_complete.sh" "$@"
