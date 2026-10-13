#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
compiler="${CXX:-g++}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
flags=(-std=c++20 -Wall -Wextra -Werror -pedantic -O1 -g -Iinclude)
if [[ "${GEN3_SANITIZE:-0}" == "1" ]]; then
    flags+=(-fsanitize=address,undefined -fno-omit-frame-pointer)
fi
"$compiler" "${flags[@]}" tests/test_gen3_slot.cpp -o "$tmp/test_gen3_slot"
"$tmp/test_gen3_slot"
