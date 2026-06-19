#!/bin/zsh
set -u

MAC_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$MAC_DIR/../.." && pwd)"
exec "$ROOT/the little dachshund.app/Contents/MacOS/the little dachshund"
