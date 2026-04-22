#!/usr/bin/env bash
# Thin wrapper — implementation: scripts/shell/gate.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/shell/gate.sh" "$@"
