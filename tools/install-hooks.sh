#!/bin/sh
# Point git at the repo's tracked hooks. Run once per clone.
#
#   tools/install-hooks.sh
#
# Uses core.hooksPath so the hooks are version-controlled and everyone gets
# improvements to them, rather than each clone carrying a private copy in
# .git/hooks that silently rots.
set -e
cd "$(dirname "$0")/.."
chmod +x tools/hooks/*
git config core.hooksPath tools/hooks
echo "hooks installed (core.hooksPath = tools/hooks)"
echo "  pre-commit: requires docs/HANDOFF.md when thundera/ changes"
echo "  bypass with SKIP_DOC_CHECK=1"
