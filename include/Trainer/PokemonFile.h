#ifndef TRAINER_POKEMON_FILE_H
#define TRAINER_POKEMON_FILE_H

#include <cstddef>
#include <memory>
#include <span>
#include <string>
#include <vector>

#include "Pokemon/Pokemon.h"

namespace Trainer::PokemonFile
{
    struct LoadResult
    {
        std::unique_ptr<Pokemon::Pokemon> pokemon;
        std::string error;

        explicit operator bool() const noexcept { return pokemon != nullptr; }
    };

    /// Native Pokemon entity extensions supported by PKSE's existing entity classes.
    /// Deliberately excludes side-game formats PKSE does not currently model as entities
    /// (Stadium, Colosseum/XD, Battle Revolution and Ranch).
    const std::vector<std::string> &extensions();

    /// Parse one native Pokemon entity. The extension selects the entity format and the size is
    /// validated before any format parser sees the bytes. The result is also checked for structural
    /// validity and native encrypt/decrypt round-trip fidelity.
    LoadResult parse(std::span<const std::byte> bytes, const std::string &fileName);

    /// Read and parse one native Pokemon entity from disk.
    LoadResult load(const std::string &path);

    /// Serialize a Pokemon to its native encrypted/on-disk entity representation. The source object
    /// is never mutated: checksum refresh happens on a clone, then the emitted bytes are reparsed and
    /// compared with that clone before they are returned.
    std::vector<std::byte> serialize(const Pokemon::Pokemon &pokemon, std::string *error = nullptr);

    /// Canonical PKHeX-compatible extension for this PKSE entity class (including PB/PA variants).
    std::string extensionFor(const Pokemon::Pokemon &pokemon);

    /// A unique default export path under sdmc:/PKSE/exports/.
    std::string defaultExportPath(const Pokemon::Pokemon &pokemon);

    /// Serialize, verify and write the entity. Parent directories are created as needed for PKSE's
    /// own default export directory. Existing files are never partially accepted as success.
    bool write(const Pokemon::Pokemon &pokemon, const std::string &path, std::string *error = nullptr);
}

#endif
