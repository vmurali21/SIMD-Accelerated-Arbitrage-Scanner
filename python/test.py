import sys
import os

# Add the build directory to the Python path to find the compiled .pyd module
build_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'build'))
sys.path.append(build_dir)

try:
    import fast_pricer
except ImportError as e:
    print(f"Failed to import fast_pricer: {e}")
    sys.exit(1)

def test_pricer():
    pricer = fast_pricer.HestonMonteCarloPricer()
    
    params = fast_pricer.HestonParams()
    params.S0 = 100.0
    params.V0 = 0.04
    params.r = 0.05
    params.kappa = 2.0
    params.theta = 0.04
    params.sigma = 0.1
    params.rho = -0.5
    
    K = 100.0
    T = 1.0
    num_paths = 100000
    num_steps = 100
    
    print("Pricing Option via AVX2 bindings...")
    price = pricer.price_call_avx2(params, K, T, num_paths, num_steps)
    print(f"Python Bindings Working! AVX2 Price: {price:.4f}")

if __name__ == "__main__":
    test_pricer()
