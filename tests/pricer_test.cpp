#include <gtest/gtest.h>
#include "heston.hpp"
#include <cmath>

TEST(HestonPricerTest, PriceMatchesWithinTolerance) {
    HestonParams params;
    params.S0 = 100.0f;
    params.V0 = 0.04f;
    params.r = 0.05f;
    params.kappa = 2.0f;
    params.theta = 0.04f;
    params.sigma = 0.1f;
    params.rho = -0.5f;

    float K = 100.0f;
    float T = 1.0f;
    size_t num_paths = 100000;
    size_t num_steps = 100;

    HestonMonteCarloPricer pricer;
    
    float scalar_price = pricer.price_call_scalar(params, K, T, num_paths, num_steps);
    float avx2_price = pricer.price_call_avx2(params, K, T, num_paths, num_steps);

    std::cout << "Scalar Price: " << scalar_price << std::endl;
    std::cout << "AVX2 Price: " << avx2_price << std::endl;

    // Both should be close to each other
    EXPECT_NEAR(scalar_price, avx2_price, 0.5f);
    
    // Basic Black-Scholes roughly ~10.45 for these params
    EXPECT_GT(scalar_price, 9.0f);
    EXPECT_LT(scalar_price, 12.0f);
}
