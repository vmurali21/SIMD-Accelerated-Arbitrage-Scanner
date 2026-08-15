#pragma once
#include <cstdint>
#include <vector>
#include <cmath>
#include <numbers>

class FastPRNG {
    uint64_t s[4];

    static inline uint64_t rotl(const uint64_t x, int k) {
        return (x << k) | (x >> (64 - k));
    }

public:
    explicit FastPRNG(uint64_t seed) {
        // SplitMix64 to initialize state
        uint64_t z = seed;
        for (int i = 0; i < 4; ++i) {
            z += 0x9e3779b97f4a7c15;
            uint64_t temp = z;
            temp = (temp ^ (temp >> 30)) * 0xbf58476d1ce4e5b9;
            temp = (temp ^ (temp >> 27)) * 0x94d049bb133111eb;
            s[i] = temp ^ (temp >> 31);
        }
    }

    // Xoshiro256++ next
    inline uint64_t next() {
        const uint64_t result = rotl(s[0] + s[3], 23) + s[0];
        const uint64_t t = s[1] << 17;
        s[2] ^= s[0];
        s[3] ^= s[1];
        s[1] ^= s[2];
        s[0] ^= s[3];
        s[2] ^= t;
        s[3] = rotl(s[3], 45);
        return result;
    }

    // Uniform float in (0, 1]
    inline float next_uniform() {
        return (next() >> 40) * 0x1.0p-24f;
    }

    // Standard Normal using Box-Muller
    inline void next_gaussian_pair(float& n1, float& n2) {
        float u1 = next_uniform();
        if (u1 == 0.0f) u1 = 1e-7f; // prevent log(0)
        float u2 = next_uniform();
        float r = std::sqrt(-2.0f * std::log(u1));
        float theta = 2.0f * std::numbers::pi_v<float> * u2;
        n1 = r * std::cos(theta);
        n2 = r * std::sin(theta);
    }
};
