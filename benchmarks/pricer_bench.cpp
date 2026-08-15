#include <benchmark/benchmark.h>
#include "heston.hpp"

static void BM_HestonScalar(benchmark::State& state) {
    HestonParams params{100.0f, 0.04f, 0.05f, 2.0f, 0.04f, 0.1f, -0.5f};
    HestonMonteCarloPricer pricer;
    for (auto _ : state) {
        benchmark::DoNotOptimize(pricer.price_call_scalar(params, 100.0f, 1.0f, 100000, 100));
    }
}
BENCHMARK(BM_HestonScalar)->Unit(benchmark::kMillisecond);

static void BM_HestonAVX2(benchmark::State& state) {
    HestonParams params{100.0f, 0.04f, 0.05f, 2.0f, 0.04f, 0.1f, -0.5f};
    HestonMonteCarloPricer pricer;
    for (auto _ : state) {
        benchmark::DoNotOptimize(pricer.price_call_avx2(params, 100.0f, 1.0f, 100000, 100));
    }
}
BENCHMARK(BM_HestonAVX2)->Unit(benchmark::kMillisecond);
