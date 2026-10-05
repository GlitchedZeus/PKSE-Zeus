#!/usr/bin/env python3
"""One-shot exact patch: native-file parsing must not misuse Bank::makePokemon()."""

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


path = Path("src/Trainer/PokemonFile.cpp")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '#include "Pokemon/Pokemon1RBY.h"\n#include "Pokemon/Pokemon2GSC.h"\n',
    '#include "Pokemon/Pokemon1RBY.h"\n'
    '#include "Pokemon/Pokemon2GSC.h"\n'
    '#include "Pokemon/Pokemon3FRLG.h"\n'
    '#include "Pokemon/Pokemon4HGSS.h"\n'
    '#include "Pokemon/Pokemon5B2W2.h"\n'
    '#include "Pokemon/Pokemon6ORAS.h"\n'
    '#include "Pokemon/Pokemon7USUM.h"\n'
    '#include "Pokemon/Pokemon7LGPE.h"\n'
    '#include "Pokemon/Pokemon8SWSH.h"\n'
    '#include "Pokemon/Pokemon8BDSP.h"\n'
    '#include "Pokemon/Pokemon8LA.h"\n'
    '#include "Pokemon/Pokemon9SV.h"\n'
    '#include "Pokemon/Pokemon9LZA.h"\n',
    "native entity includes",
)

factory = r'''
        std::unique_ptr<Pokemon::Pokemon> makeNativePokemon(GameVersion group,
                                                            std::span<const std::byte> record)
        {
            // Unlike Bank::makePokemon(), this factory intentionally accepts both native stored and
            // party lengths. The extension has already chosen the format and sizeAllowed() has
            // already rejected every other length before this is called.
            switch (group)
            {
            case GameVersion::RBY: return std::make_unique<Pokemon::Pokemon1RBY>(record);
            case GameVersion::GSC: return std::make_unique<Pokemon::Pokemon2GSC>(record);
            case GameVersion::FRLG: return std::make_unique<Pokemon::Pokemon3FRLG>(record);
            case GameVersion::HGSS: return std::make_unique<Pokemon::Pokemon4HGSS>(record);
            case GameVersion::B2W2: return std::make_unique<Pokemon::Pokemon5B2W2>(record);
            case GameVersion::ORAS: return std::make_unique<Pokemon::Pokemon6ORAS>(record);
            case GameVersion::USUM: return std::make_unique<Pokemon::Pokemon7USUM>(record);
            case GameVersion::GG: return std::make_unique<Pokemon::Pokemon7LGPE>(record);
            case GameVersion::SWSH: return std::make_unique<Pokemon::Pokemon8SWSH>(record);
            case GameVersion::BDSP: return std::make_unique<Pokemon::Pokemon8BDSP>(record);
            case GameVersion::PLA: return std::make_unique<Pokemon::Pokemon8LA>(record);
            case GameVersion::SV: return std::make_unique<Pokemon::Pokemon9SV>(record);
            case GameVersion::ZA: return std::make_unique<Pokemon::Pokemon9LZA>(record);
            default: return nullptr;
            }
        }

'''
text = replace_once(
    text,
    '        std::unique_ptr<Pokemon::Pokemon> parseUnchecked(std::span<const std::byte> bytes,\n',
    factory + '        std::unique_ptr<Pokemon::Pokemon> parseUnchecked(std::span<const std::byte> bytes,\n',
    "native entity factory insertion",
)
text = replace_once(
    text,
    '            auto pokemon = Bank::makePokemon(spec->group, bytes);\n',
    '            auto pokemon = makeNativePokemon(spec->group, bytes);\n',
    "native parser factory call",
)
path.write_text(text, encoding="utf-8")
print("Pokemon native-file factory patch applied cleanly")
