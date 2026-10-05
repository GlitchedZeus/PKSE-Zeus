#!/usr/bin/env python3
"""Cheap source-level guardrails for the standalone Pokemon file feature.

PKSE does not currently have a unit-test runner. This check deliberately stays host-only and
verifies the easy-to-regress contract around issue #103 without needing devkitPro: every advertised
extension must have a parser spec, the Switch-era alternate extensions must remain present, and the
write path must keep its verify-before-rename safety sequence.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CPP = (ROOT / "src/Trainer/PokemonFile.cpp").read_text(encoding="utf-8")
HEADER = (ROOT / "include/Trainer/PokemonFile.h").read_text(encoding="utf-8")

specs = set(re.findall(r'\{"(\.[a-z0-9]+)",\s*GameVersion::', CPP))
extensions_block = re.search(
    r"const std::vector<std::string> &extensions\(\).*?static const std::vector<std::string> values = \{(.*?)\};",
    CPP,
    re.S,
)
assert extensions_block, "could not find PokemonFile::extensions()"
advertised = set(re.findall(r'"(\.[a-z0-9]+)"', extensions_block.group(1)))

assert advertised == specs, f"advertised extensions drifted from parser specs: {advertised ^ specs}"
expected = {
    ".pk1", ".pk2", ".pk3", ".pk4", ".pk5", ".pk6", ".pk7",
    ".pb7", ".pk8", ".pb8", ".pa8", ".pk9", ".pa9",
}
assert advertised == expected, f"unexpected native-format set: {advertised ^ expected}"

# Issue #103 is native main-series entity I/O. Side-game containers need their own entity models
# and are intentionally outside this first PR.
for unsupported in (".pkm", ".ck3", ".xk3", ".bk4", ".rk4"):
    assert unsupported not in advertised, f"side-game/ambiguous format leaked into native set: {unsupported}"

# Safety contract: source entity is cloned, checksum refreshed, emitted bytes reparsed, the actual
# temporary file read back, and only then promoted with rename().
for needle in (
    "auto copy = pokemon.clone();",
    "copy->refreshChecksum();",
    "parseUnchecked(native, extension, &verifyError)",
    'const std::string temporary = path + ".tmp";',
    "Utils::readAllBytes(temporary.c_str(), &verifySize)",
    "std::rename(temporary.c_str(), path.c_str())",
):
    assert needle in CPP, f"missing export safety step: {needle}"

assert "std::free(raw);" in CPP, "readAllBytes() buffer must be released with free()"
assert "bool supportsFileName(const std::string &fileName);" in HEADER
assert "bool importIntoBank(Bank &bank" in HEADER

print(f"Pokemon file contract OK: {len(advertised)} native extensions")
