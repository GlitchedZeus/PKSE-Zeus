#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <vector>

#include "Save/Gen3Slot.h"
#include "Save/RtcFooter.h"

using Save::Gen3Kind;
using Save::Gen3Slot;

static void put16(std::vector<uint8_t> &buf, size_t at, uint16_t val)
{
    buf[at] = static_cast<uint8_t>(val);
    buf[at + 1] = static_cast<uint8_t>(val >> 8);
}
static void put32(std::vector<uint8_t> &buf, size_t at, uint32_t val)
{
    put16(buf, at, static_cast<uint16_t>(val));
    put16(buf, at + 2, static_cast<uint16_t>(val >> 16));
}
static void writeSlot(std::vector<uint8_t> &buf, size_t base, uint32_t counter,
                      uint32_t marker, size_t rotate = 0)
{
    for (size_t p = 0; p < Save::GEN3_SECTOR_COUNT; ++p)
    {
        const size_t offset = base + p * Save::GEN3_SECTOR_BYTES;
        const uint16_t id = static_cast<uint16_t>((p + rotate) % Save::GEN3_SECTOR_COUNT);
        put16(buf, offset + 0xFF4, id);
        put32(buf, offset + 0xFF8, Save::GEN3_SECTOR_MAGIC);
        put32(buf, offset + 0xFFC, counter);
        if (id == 0) put32(buf, offset + 0xAC, marker);
    }
}
int main()
{
    int passed = 0;
    auto check = [&](bool ok, const char *desc) {
        if (!ok) { std::cerr << "FAIL " << desc << '\n'; std::abort(); }
        ++passed;
    };
    std::vector<uint8_t> buf(Save::GEN3_IMAGE_BYTES, 0);
    check(!Save::selectGen3Slot(buf).valid, "blank save refused");
    writeSlot(buf, 0, 1, 0);
    check(Save::gen3Kind(Save::selectGen3Slot(buf)) == Gen3Kind::RSE, "Ruby/Sapphire recognized");
    writeSlot(buf, 0xE000, 2, 1, 5);
    Gen3Slot slot = Save::selectGen3Slot(buf);
    check(slot.valid && slot.base == 0xE000 && slot.marker == 1, "newer rotated FRLG slot selected");
    check(Save::gen3Kind(slot) == Gen3Kind::FRLG, "FRLG recognized");
    check(slot.offsets[0] == 0xE000 + 9*0x1000, "rotated sector zero resolved");
    // A corrupt latest slot must not hide a complete earlier slot.
    put16(buf, 0xE000 + 0x1000 + 0xFF4, 5); // duplicate ID 5
    slot = Save::selectGen3Slot(buf);
    check(slot.valid && slot.base == 0, "fallback to complete slot when newest torn");
    writeSlot(buf, 0xE000, 2, 1);
    put32(buf, 0xE000 + 0xFF8, 0);
    check(Save::selectGen3Slot(buf).base == 0, "bad footer magic rejects slot");
    writeSlot(buf, 0xE000, 3, 1);
    put16(buf, 0xE000 + 0xFF4, 19);
    check(Save::selectGen3Slot(buf).base == 0, "out of bounds section ID rejected");
    writeSlot(buf, 0xE000, 0xFFFFFFFFu, 1);
    check(Save::selectGen3Slot(buf).base == 0, "erased counter sentinel loses");
    writeSlot(buf, 0xE000, 2, 1);
    writeSlot(buf, 0, 2, 0);
    check(Save::selectGen3Slot(buf).base == 0, "tie prefers A");
    writeSlot(buf, 0, 10, 0x12345678u);
    check(Save::gen3Kind(Save::selectGen3Slot(buf)) == Gen3Kind::RSE, "Emerald marker is RSE");
    check(!Save::selectGen3Slot({}).valid, "empty vector refused");
    check(!Save::selectGen3Slot(std::vector<uint8_t>(0x10000)).valid, "truncated image refused");
    check(!Save::selectGen3Slot(std::vector<uint8_t>(0x20001)).valid, "oversized image refused");
    std::vector<uint8_t> footered = buf;
    footered.resize(0x20020, 0xAB);
    check(Save::rtcFooterLength(footered.size()) == 0x20, "recognize RTC footer");
    check(Save::stripRtcFooter(footered) && footered == buf, "strip RTC footer losslessly");
    check(Save::gen3Kind(Save::selectGen3Slot(footered)) == Gen3Kind::RSE, "recognition after trim");
    std::cout << "PASS: " << passed << " Gen III structural slot/RTC tests\n";
}
