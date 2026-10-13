#ifndef SAVE_GEN3_SLOT_H
#define SAVE_GEN3_SLOT_H

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace Save
{
    // The same GBA 128 KiB container is used by Ruby/Sapphire/Emerald and FireRed/LeafGreen.
    // This host-testable scanner owns slot validity, generation-3 identity, and active-slot choice.
    // Both the save picker and trainer constructors must agree on the selected slot.
    constexpr size_t GEN3_IMAGE_BYTES = 0x20000;
    constexpr size_t GEN3_SLOT_BYTES = 14 * 0x1000;
    constexpr size_t GEN3_SECTOR_BYTES = 0x1000;
    constexpr size_t GEN3_SECTOR_COUNT = 14;
    constexpr uint32_t GEN3_SECTOR_MAGIC = 0x08012025;

    enum class Gen3Kind { Unknown, RSE, FRLG };

    struct Gen3Slot
    {
        bool valid = false;
        size_t base = 0;
        uint32_t counter = 0;
        uint32_t marker = 0;
        std::array<size_t, GEN3_SECTOR_COUNT> offsets{};
    };

    inline uint16_t gen3Read16(const std::vector<uint8_t> &bytes, size_t offset) noexcept
    {
        return static_cast<uint16_t>(bytes[offset] | (uint16_t(bytes[offset + 1]) << 8));
    }

    inline uint32_t gen3Read32(const std::vector<uint8_t> &bytes, size_t offset) noexcept
    {
        return uint32_t(bytes[offset]) | (uint32_t(bytes[offset + 1]) << 8) |
               (uint32_t(bytes[offset + 2]) << 16) | (uint32_t(bytes[offset + 3]) << 24);
    }

    inline Gen3Slot inspectGen3Slot(const std::vector<uint8_t> &bytes, size_t base) noexcept
    {
        Gen3Slot slot{};
        slot.base = base;
        if (bytes.size() != GEN3_IMAGE_BYTES || base > bytes.size() - GEN3_SLOT_BYTES)
            return slot;

        std::array<bool, GEN3_SECTOR_COUNT> seen{};
        for (size_t physical = 0; physical < GEN3_SECTOR_COUNT; ++physical)
        {
            const size_t offset = base + physical * GEN3_SECTOR_BYTES;
            if (gen3Read32(bytes, offset + 0xFF8) != GEN3_SECTOR_MAGIC)
                return slot;
            const uint16_t section = gen3Read16(bytes, offset + 0xFF4);
            if (section >= GEN3_SECTOR_COUNT || seen[section])
                return slot;
            seen[section] = true;
            slot.offsets[section] = offset;
        }
        const size_t small = slot.offsets[0];
        slot.counter = gen3Read32(bytes, small + 0xFFC);
        slot.marker = gen3Read32(bytes, small + 0xAC);
        slot.valid = true;
        return slot;
    }

    // Prefer a complete slot to a torn/partially written slot, even when the partial one
    // advertises a newer counter. 0xFFFFFFFF marks an erased slot, not a new save.
    inline Gen3Slot selectGen3Slot(const std::vector<uint8_t> &bytes) noexcept
    {
        const Gen3Slot a = inspectGen3Slot(bytes, 0);
        const Gen3Slot b = inspectGen3Slot(bytes, 0xE000);
        if (!a.valid) return b;
        if (!b.valid) return a;
        if (a.counter == 0xFFFFFFFFu && b.counter != 0xFFFFFFFFu) return b;
        if (b.counter == 0xFFFFFFFFu && a.counter != 0xFFFFFFFFu) return a;
        return a.counter >= b.counter ? a : b;
    }

    inline Gen3Kind gen3Kind(const Gen3Slot &slot) noexcept
    {
        if (!slot.valid) return Gen3Kind::Unknown;
        return slot.marker == 1 ? Gen3Kind::FRLG : Gen3Kind::RSE;
    }
}

#endif // SAVE_GEN3_SLOT_H
