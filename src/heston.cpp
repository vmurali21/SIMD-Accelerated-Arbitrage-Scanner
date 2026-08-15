#include "heston.hpp"
#include <immintrin.h>
#include <cmath>
#include <algorithm>
#include <iostream>

HestonMonteCarloPricer::HestonMonteCarloPricer() : prng(42) {}

void HestonMonteCarloPricer::generate_paths(size_t num_paths, size_t num_steps) {
    size_t total_size = num_paths * num_steps;
    
    // Zero-allocation on hot path via reserve/resize
    if (Z1_buffer.size() < total_size) {
        Z1_buffer.resize(total_size);
        Z2_buffer.resize(total_size);
    }
    if (final_lnS.size() < num_paths) {
        final_lnS.resize(num_paths);
    }

    // Fill buffers with Gaussians.
    // Layout: Z1_buffer[step * num_paths + p] ensures contiguous memory access 
    // across paths during the time-stepping loop.
    for (size_t step = 0; step < num_steps; ++step) {
        for (size_t p = 0; p < num_paths; p += 2) {
            float n1, n2, n3, n4;
            prng.next_gaussian_pair(n1, n2);
            prng.next_gaussian_pair(n3, n4);
            
            Z1_buffer[step * num_paths + p] = n1;
            Z2_buffer[step * num_paths + p] = n2;
            if (p + 1 < num_paths) {
                Z1_buffer[step * num_paths + p + 1] = n3;
                Z2_buffer[step * num_paths + p + 1] = n4;
            }
        }
    }
}

float HestonMonteCarloPricer::price_call_scalar(const HestonParams& params, float K, float T, size_t num_paths, size_t num_steps) {
    generate_paths(num_paths, num_steps);

    float dt = T / num_steps;
    float sqrt_dt = std::sqrt(dt);
    float sqrt_1_rho2 = std::sqrt(1.0f - params.rho * params.rho);

    for (size_t p = 0; p < num_paths; ++p) {
        float lnS = std::log(params.S0);
        float V = params.V0;

        for (size_t step = 0; step < num_steps; ++step) {
            float Z1 = Z1_buffer[step * num_paths + p];
            float Z2 = Z2_buffer[step * num_paths + p];

            float dW1 = Z1 * sqrt_dt;
            float dW2 = (params.rho * Z1 + sqrt_1_rho2 * Z2) * sqrt_dt;

            float sqrtV = std::sqrt(std::max(V, 0.0f));

            // Log-Euler for S
            lnS += (params.r - 0.5f * V) * dt + sqrtV * dW1;

            // Full truncation Euler for V
            V += params.kappa * (params.theta - std::max(V, 0.0f)) * dt + params.sigma * sqrtV * dW2;
            V = std::max(V, 0.0f);
        }
        final_lnS[p] = lnS;
    }

    // Payoff calculation
    float sum_payoffs = 0.0f;
    for (size_t p = 0; p < num_paths; ++p) {
        float ST = std::exp(final_lnS[p]);
        sum_payoffs += std::max(ST - K, 0.0f);
    }

    return std::exp(-params.r * T) * (sum_payoffs / num_paths);
}

float HestonMonteCarloPricer::price_call_avx2(const HestonParams& params, float K, float T, size_t num_paths, size_t num_steps) {
    // Ensure multiple of 8 paths for AVX2
    num_paths = (num_paths / 8) * 8;
    generate_paths(num_paths, num_steps);

    float dt = T / num_steps;
    __m256 dt_vec = _mm256_set1_ps(dt);
    __m256 sqrt_dt_vec = _mm256_set1_ps(std::sqrt(dt));
    __m256 kappa_vec = _mm256_set1_ps(params.kappa);
    __m256 theta_vec = _mm256_set1_ps(params.theta);
    __m256 sigma_vec = _mm256_set1_ps(params.sigma);
    __m256 r_vec = _mm256_set1_ps(params.r);
    __m256 rho_vec = _mm256_set1_ps(params.rho);
    __m256 sqrt_1_rho2_vec = _mm256_set1_ps(std::sqrt(1.0f - params.rho * params.rho));
    __m256 zero_vec = _mm256_setzero_ps();
    __m256 half_vec = _mm256_set1_ps(0.5f);

    for (size_t p = 0; p < num_paths; p += 8) {
        __m256 lnS = _mm256_set1_ps(std::log(params.S0));
        __m256 V = _mm256_set1_ps(params.V0);

        for (size_t step = 0; step < num_steps; ++step) {
            __m256 Z1 = _mm256_loadu_ps(&Z1_buffer[step * num_paths + p]);
            __m256 Z2 = _mm256_loadu_ps(&Z2_buffer[step * num_paths + p]);

            __m256 dW1 = _mm256_mul_ps(Z1, sqrt_dt_vec);
            __m256 dW2_base = _mm256_add_ps(_mm256_mul_ps(rho_vec, Z1), _mm256_mul_ps(sqrt_1_rho2_vec, Z2));
            __m256 dW2 = _mm256_mul_ps(dW2_base, sqrt_dt_vec);

            __m256 sqrtV = _mm256_sqrt_ps(V);

            // lnS = lnS + (r - 0.5*V)*dt + sqrtV * dW1
            __m256 drift = _mm256_mul_ps(_mm256_sub_ps(r_vec, _mm256_mul_ps(half_vec, V)), dt_vec);
            __m256 diffusion = _mm256_mul_ps(sqrtV, dW1);
            lnS = _mm256_add_ps(lnS, _mm256_add_ps(drift, diffusion));

            // V = V + kappa*(theta - V)*dt + sigma * sqrtV * dW2
            __m256 V_drift = _mm256_mul_ps(kappa_vec, _mm256_mul_ps(_mm256_sub_ps(theta_vec, V), dt_vec));
            __m256 V_diff = _mm256_mul_ps(sigma_vec, _mm256_mul_ps(sqrtV, dW2));
            V = _mm256_add_ps(V, _mm256_add_ps(V_drift, V_diff));

            // V = max(V, 0)
            V = _mm256_max_ps(V, zero_vec);
        }
        
        _mm256_storeu_ps(&final_lnS[p], lnS);
    }

    float sum_payoffs = 0.0f;
    for (size_t p = 0; p < num_paths; ++p) {
        float ST = std::exp(final_lnS[p]);
        sum_payoffs += std::max(ST - K, 0.0f);
    }

    return std::exp(-params.r * T) * (sum_payoffs / num_paths);
}
