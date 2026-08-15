#pragma once
#include <vector>
#include <cstddef>
#include "prng.hpp"

struct HestonParams {
    float S0;     // Initial stock price
    float V0;     // Initial variance
    float r;      // Risk-free rate
    float kappa;  // Mean reversion speed
    float theta;  // Long-term variance
    float sigma;  // Volatility of variance
    float rho;    // Correlation
};

class HestonMonteCarloPricer {
    std::vector<float> Z1_buffer;
    std::vector<float> Z2_buffer;
    std::vector<float> final_lnS;
    FastPRNG prng;

    void generate_paths(size_t num_paths, size_t num_steps);

public:
    HestonMonteCarloPricer();

    // Zero-allocation path generation
    float price_call_scalar(const HestonParams& params, float K, float T, size_t num_paths, size_t num_steps);
    
    // AVX2 implementation
    float price_call_avx2(const HestonParams& params, float K, float T, size_t num_paths, size_t num_steps);
};
