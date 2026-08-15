#include <benchmark/benchmark.h>

extern int dummy_function();

static void BM_DummyFunction(benchmark::State& state) {
    for (auto _ : state) {
        benchmark::DoNotOptimize(dummy_function());
    }
}
BENCHMARK(BM_DummyFunction);
