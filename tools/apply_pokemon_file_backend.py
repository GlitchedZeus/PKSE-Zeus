#!/usr/bin/env python3
"""One-shot exact patch for issue #103 Bank-safe native imports.

Standalone files commonly use the shorter box-record form while PKSE's unified Bank deliberately
stores party-sized records for formats whose accessors require the party tail. This patch keeps the
Bank format untouched: Gen 1/2 locale-sized records and Gen 3's already-supported short PK3 stay as
is; later short records are promoted once, with a recalculated party tail, before Bank insertion.
"""

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


header_path = Path("include/Trainer/PokemonFile.h")
header = header_path.read_text(encoding="utf-8")
header = replace_once(
    header,
    '''        /// Read and parse one native Pokemon entity from disk.\n        LoadResult load(const std::string &path);\n\n        /// Read, validate and place one native Pokemon entity into the first free Bank slot.\n''',
    '''        /// Read and parse one native Pokemon entity from disk.\n        LoadResult load(const std::string &path);\n\n        /// Return an entity safe for PKSE's unified Bank representation. Native box-sized files\n        /// are promoted to the Bank's party-sized record where required, with the party tail\n        /// recalculated from the stored data. Gen 1/2 locale-sized records and Gen 3's existing\n        /// short-record Bank path remain byte-preserving.\n        std::unique_ptr<Pokemon::Pokemon> prepareForBank(const Pokemon::Pokemon &pokemon,\n                                                         std::string *error = nullptr);\n\n        /// Read, validate and place one native Pokemon entity into the first free Bank slot.\n''',
    "PokemonFile header Bank-normalization API",
)
header_path.write_text(header, encoding="utf-8")


cpp_path = Path("src/Trainer/PokemonFile.cpp")
cpp = cpp_path.read_text(encoding="utf-8")
helper = r'''
        std::byte *encryptBankRecord(GameVersion group, std::span<const std::byte> data,
                                     uint32_t encryptionConstant)
        {
            switch (group)
            {
            case GameVersion::RBY:
            case GameVersion::GSC:
            {
                auto *result = new std::byte[data.size()];
                std::memcpy(result, data.data(), data.size());
                return result;
            }
            case GameVersion::FRLG:
            case GameVersion::RSE:
                return Encryption::encryptArray3FRLG(data);
            case GameVersion::DP:
            case GameVersion::PT:
            case GameVersion::HGSS:
                return Encryption::encryptArray4HGSS(data);
            case GameVersion::BW:
            case GameVersion::B2W2:
                return Encryption::encryptArray5B2W2(data);
            case GameVersion::XY:
            case GameVersion::ORAS:
                return Encryption::encryptArray6ORAS(data);
            case GameVersion::SM:
            case GameVersion::USUM:
                return Encryption::encryptArray7USUM(data);
            case GameVersion::GG:
                return Encryption::encryptArray7LGPE(data, encryptionConstant);
            case GameVersion::SWSH:
                return Encryption::encryptArray8SWSH(data, encryptionConstant);
            case GameVersion::BDSP:
                return Encryption::encryptArray8BDSP(data, encryptionConstant);
            case GameVersion::PLA:
                return Encryption::encryptArray8LA(data, encryptionConstant);
            case GameVersion::SV:
                return Encryption::encryptArray9SV(data, encryptionConstant);
            case GameVersion::ZA:
                return Encryption::encryptArray9LZA(data, encryptionConstant);
            default:
                return nullptr;
            }
        }

'''
cpp = replace_once(
    cpp,
    '        std::string extensionForGroup(GameVersion group)\n',
    helper + '        std::string extensionForGroup(GameVersion group)\n',
    "Bank-record encryption helper insertion",
)

prepare = r'''
    std::unique_ptr<Pokemon::Pokemon> prepareForBank(const Pokemon::Pokemon &pokemon, std::string *error)
    {
        const GameVersion bankGroup = Bank::groupAsBanked(pokemon.getGameGroup());
        if (bankGroup == GameVersion::Invalid)
        {
            if (error) *error = "Pokemon format cannot be stored in the PKSE Bank";
            return nullptr;
        }

        // Gen 1/2 have locale-dependent native lengths that the Bank tags explicitly preserve.
        // Gen 3 already has a dedicated 80-byte depositedSpan() path in Bank.cpp. Keep those
        // byte-preserving instead of manufacturing a different native representation.
        if (bankGroup == GameVersion::RBY || bankGroup == GameVersion::GSC ||
            bankGroup == GameVersion::FRLG)
        {
            auto copy = pokemon.clone();
            if (!copy && error) *error = "Pokemon entity does not support cloning";
            else if (error) error->clear();
            return copy;
        }

        const size_t bankSize = Bank::recordSizeFor(bankGroup);
        if (bankSize == 0)
        {
            if (error) *error = "PKSE Bank has no record size for this Pokemon format";
            return nullptr;
        }
        if (pokemon.getDataSize() == bankSize)
        {
            auto copy = pokemon.clone();
            if (!copy && error) *error = "Pokemon entity does not support cloning";
            else if (error) error->clear();
            return copy;
        }
        if (pokemon.getDataSize() > bankSize)
        {
            if (error) *error = "Pokemon record is larger than the PKSE Bank format";
            return nullptr;
        }

        // The native file is a stored/box record. Build the Bank's party-sized representation from
        // the already-validated DECRYPTED stored bytes, then let the existing entity class calculate
        // the party-only level/stats tail. Padding encrypted bytes would be wrong because every
        // generation encrypts that tail as part of its native record.
        std::vector<std::byte> padded(bankSize, std::byte{0});
        const auto source = pokemon.getData();
        std::memcpy(padded.data(), source.data(), source.size());

        std::byte *encrypted = encryptBankRecord(bankGroup, padded, pokemon.encryptionConstant());
        if (!encrypted)
        {
            if (error) *error = "Pokemon format has no Bank promotion serializer";
            return nullptr;
        }

        auto promoted = Bank::makePokemon(
            bankGroup, std::span<const std::byte>(encrypted, bankSize));
        delete[] encrypted;
        if (!promoted)
        {
            if (error) *error = "could not construct party-sized Pokemon record for the Bank";
            return nullptr;
        }

        promoted->recalculateStats();
        promoted->refreshChecksum();
        if (!promoted->isStructurallyValid())
        {
            if (error) *error = "party-sized Bank record failed structural/checksum validation";
            return nullptr;
        }

        // Prove the promoted entity can still pass the same native serializer/reparse contract as a
        // directly loaded file before exposing it to Storage.
        std::string verifyError;
        if (serialize(*promoted, &verifyError).empty())
        {
            if (error) *error = "Bank promotion round-trip failed: " + verifyError;
            return nullptr;
        }

        if (error) error->clear();
        return promoted;
    }

'''
cpp = replace_once(
    cpp,
    '    std::vector<std::byte> serialize(const Pokemon::Pokemon &pokemon, std::string *error)\n',
    prepare + '    std::vector<std::byte> serialize(const Pokemon::Pokemon &pokemon, std::string *error)\n',
    "prepareForBank implementation insertion",
)
cpp_path.write_text(cpp, encoding="utf-8")


adapter_path = Path("src/Trainer/PokemonFileBank.cpp")
adapter = adapter_path.read_text(encoding="utf-8")
adapter = replace_once(
    adapter,
    '''        LoadResult loaded = load(path);\n        if (!loaded)\n        {\n            if (error) *error = loaded.error;\n            return false;\n        }\n\n        for (size_t box = 0; box < bank.boxes.size(); ++box)\n''',
    '''        LoadResult loaded = load(path);\n        if (!loaded)\n        {\n            if (error) *error = loaded.error;\n            return false;\n        }\n\n        std::string bankError;\n        auto bankPokemon = prepareForBank(*loaded.pokemon, &bankError);\n        if (!bankPokemon)\n        {\n            if (error) *error = bankError.empty() ? "could not normalize Pokemon for Bank storage" : bankError;\n            return false;\n        }\n\n        for (size_t box = 0; box < bank.boxes.size(); ++box)\n''',
    "Bank import normalization",
)
adapter = replace_once(
    adapter,
    '                bank.boxes[box][slot] = std::move(loaded.pokemon);\n',
    '                bank.boxes[box][slot] = std::move(bankPokemon);\n',
    "Bank import insertion object",
)
adapter_path.write_text(adapter, encoding="utf-8")


check_path = Path("tools/check_pokemon_file_contract.py")
check = check_path.read_text(encoding="utf-8")
check = replace_once(
    check,
    'HEADER = (ROOT / "include/Trainer/PokemonFile.h").read_text(encoding="utf-8")\n',
    'HEADER = (ROOT / "include/Trainer/PokemonFile.h").read_text(encoding="utf-8")\n'
    'BANK_ADAPTER = (ROOT / "src/Trainer/PokemonFileBank.cpp").read_text(encoding="utf-8")\n',
    "contract Bank adapter source",
)
check = replace_once(
    check,
    '''assert "std::free(raw);" in CPP, "readAllBytes() buffer must be released with free()"\nassert "bool supportsFileName(const std::string &fileName);" in HEADER\nassert "bool importIntoBank(Bank &bank" in HEADER\n\nprint(f"Pokemon file contract OK: {len(advertised)} native extensions")\n''',
    '''assert "std::free(raw);" in CPP, "readAllBytes() buffer must be released with free()"\nassert "bool supportsFileName(const std::string &fileName);" in HEADER\nassert "bool importIntoBank(Bank &bank" in HEADER\nassert "prepareForBank(const Pokemon::Pokemon &pokemon" in HEADER\nassert "Bank::recordSizeFor(bankGroup)" in CPP\nassert "promoted->recalculateStats();" in CPP\nassert "promoted->refreshChecksum();" in CPP\nassert "serialize(*promoted, &verifyError)" in CPP\nassert "prepareForBank(*loaded.pokemon, &bankError)" in BANK_ADAPTER\n\nprint(f"Pokemon file contract OK: {len(advertised)} native extensions")\n''',
    "contract Bank normalization assertions",
)
check_path.write_text(check, encoding="utf-8")

print("Pokemon file Bank-normalization patch applied cleanly")
