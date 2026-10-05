#include "Trainer/PokemonFile.h"

#include <utility>

#include "Trainer/Bank.h"

namespace Trainer::PokemonFile
{
    bool importIntoBank(Bank &bank, const std::string &path, size_t *outBox,
                        size_t *outSlot, std::string *error)
    {
        LoadResult loaded = load(path);
        if (!loaded)
        {
            if (error) *error = loaded.error;
            return false;
        }

        for (size_t box = 0; box < bank.boxes.size(); ++box)
        {
            for (size_t slot = 0; slot < Bank::BANK_SLOTS_PER_BOX; ++slot)
            {
                if (bank.boxes[box][slot])
                    continue;

                bank.boxes[box][slot] = std::move(loaded.pokemon);
                bank.currentBox = static_cast<uint16_t>(box);
                if (outBox) *outBox = box;
                if (outSlot) *outSlot = slot;
                if (error) error->clear();
                return true;
            }
        }

        if (error) *error = "Bank is full";
        return false;
    }
}
