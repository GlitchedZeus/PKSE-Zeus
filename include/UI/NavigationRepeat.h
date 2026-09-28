#ifndef UI_NAVIGATION_REPEAT_H
#define UI_NAVIGATION_REPEAT_H

#include <cstdint>

namespace UI
{
    /**
     * Frame-based repeat for directional navigation.
     *
     * pressed is edge-triggered input and held is the current held state. After the initial
     * delay, held directions are emitted at a steady interval so long lists can be scrolled without
     * repeatedly tapping the D-pad or stick.
     */
    class NavigationRepeat
    {
    public:
        static constexpr int INITIAL_DELAY_FRAMES = 18;
        static constexpr int REPEAT_INTERVAL_FRAMES = 4;

        std::uint64_t apply(std::uint64_t pressed, std::uint64_t held,
                            std::uint64_t repeatableMask)
        {
            const std::uint64_t repeatableHeld = held & repeatableMask;
            if (repeatableHeld == 0 || repeatableHeld != heldDirections)
            {
                heldDirections = repeatableHeld;
                heldFrames = 0;
                return pressed;
            }

            ++heldFrames;
            if (heldFrames >= INITIAL_DELAY_FRAMES &&
                (heldFrames - INITIAL_DELAY_FRAMES) % REPEAT_INTERVAL_FRAMES == 0)
            {
                return pressed | repeatableHeld;
            }
            return pressed;
        }

        void reset()
        {
            heldDirections = 0;
            heldFrames = 0;
        }

    private:
        std::uint64_t heldDirections = 0;
        int heldFrames = 0;
    };

    struct AnalogNavigationSample
    {
        std::uint64_t down = 0;
        std::uint64_t held = 0;
    };

    /**
     * Convert the left stick into one stable logical D-pad direction.
     *
     * Hysteresis prevents drift around the deadzone, and dominant-axis locking prevents diagonal
     * noise from alternating row/column movement. A deliberate turn still switches once the new
     * axis clearly wins.
     */
    class AnalogNavigation
    {
    public:
        static constexpr int PRESS_THRESHOLD = 16000;
        static constexpr int RELEASE_THRESHOLD = 9000;
        static constexpr int AXIS_SWITCH_MARGIN = 4000;

        AnalogNavigationSample sample(int x, int y,
                                      std::uint64_t up, std::uint64_t down,
                                      std::uint64_t left, std::uint64_t right)
        {
            const std::uint64_t previous = heldDirection;
            const Candidate candidate = dominantCandidate(x, y, up, down, left, right);

            if (heldDirection != 0)
            {
                const int currentStrength =
                    directionStrength(heldDirection, x, y, up, down, left, right);
                if (currentStrength < RELEASE_THRESHOLD)
                {
                    heldDirection =
                        candidate.strength >= PRESS_THRESHOLD ? candidate.direction : 0;
                }
                else if (candidate.direction != 0 && candidate.direction != heldDirection &&
                         candidate.strength >= PRESS_THRESHOLD &&
                         candidate.strength >= currentStrength + AXIS_SWITCH_MARGIN)
                {
                    heldDirection = candidate.direction;
                }
            }
            else if (candidate.strength >= PRESS_THRESHOLD)
            {
                heldDirection = candidate.direction;
            }

            return {heldDirection & ~previous, heldDirection};
        }

        void reset() { heldDirection = 0; }

    private:
        struct Candidate
        {
            std::uint64_t direction = 0;
            int strength = 0;
        };

        static int magnitude(int value) { return value < 0 ? -value : value; }

        static Candidate dominantCandidate(int x, int y,
                                           std::uint64_t up, std::uint64_t down,
                                           std::uint64_t left, std::uint64_t right)
        {
            const int horizontal = magnitude(x);
            const int vertical = magnitude(y);
            if (horizontal > vertical)
                return {x < 0 ? left : right, horizontal};
            if (vertical > 0)
                return {y < 0 ? down : up, vertical};
            return {};
        }

        static int directionStrength(std::uint64_t direction, int x, int y,
                                     std::uint64_t up, std::uint64_t down,
                                     std::uint64_t left, std::uint64_t right)
        {
            if (direction == left)
                return -x;
            if (direction == right)
                return x;
            if (direction == up)
                return y;
            if (direction == down)
                return -y;
            return 0;
        }

        std::uint64_t heldDirection = 0;
    };

    /**
     * Shared controller-navigation path. The rest of PKSE continues to consume ordinary D-pad
     * button bits, so adding stick support here does not duplicate navigation logic in every dialog.
     */
    class ControllerNavigation
    {
    public:
        std::uint64_t apply(std::uint64_t digitalPressed, std::uint64_t digitalHeld,
                            int stickX, int stickY,
                            std::uint64_t up, std::uint64_t down,
                            std::uint64_t left, std::uint64_t right)
        {
            const AnalogNavigationSample analog =
                analogNavigation.sample(stickX, stickY, up, down, left, right);
            const std::uint64_t mask = up | down | left | right;
            return navigationRepeat.apply(digitalPressed | analog.down,
                                          digitalHeld | analog.held, mask);
        }

        void reset()
        {
            analogNavigation.reset();
            navigationRepeat.reset();
        }

    private:
        AnalogNavigation analogNavigation;
        NavigationRepeat navigationRepeat;
    };
}

#endif
