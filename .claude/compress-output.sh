#!/bin/bash
# Token compression helper - filters CLI output to reduce noise
# Usage: command | compress-output.sh [type]
# Types: test, git, npm, cargo, logs, default

type="${1:-default}"
input=$(cat)

case "$type" in
  test)
    # pytest/test output: show only failures and summary
    echo "$input" | grep -E "(FAILED|ERROR|passed|failed|error)" | tail -20
    ;;
  git)
    # git output: show only changed files
    echo "$input" | grep -E "^\s*(M|A|D|U|\?\?)" | head -30
    ;;
  npm)
    # npm output: show only errors and final status
    echo "$input" | grep -E "(error|ERR|added|removed|up to date)" | tail -10
    ;;
  cargo)
    # cargo output: show only warnings/errors and finished line
    echo "$input" | grep -E "(warning|error|Finished|Compiling)" | tail -15
    ;;
  logs)
    # log output: show only errors and exceptions
    echo "$input" | grep -E "(ERROR|WARN|Exception|error:|failed)" | tail -25
    ;;
  *)
    # default: show last 10 lines (fallback for unrecognized output)
    echo "$input" | tail -10
    ;;
esac
