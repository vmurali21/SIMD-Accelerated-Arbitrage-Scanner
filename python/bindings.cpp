#include <pybind11/pybind11.h>
#include "heston.hpp"

namespace py = pybind11;

PYBIND11_MODULE(fast_pricer, m) {
    m.doc() = "SIMD-Accelerated Options Arbitrage Scanner - Fast Pricer Module";

    py::class_<HestonParams>(m, "HestonParams")
        .def(py::init<>())
        .def_readwrite("S0", &HestonParams::S0)
        .def_readwrite("V0", &HestonParams::V0)
        .def_readwrite("r", &HestonParams::r)
        .def_readwrite("kappa", &HestonParams::kappa)
        .def_readwrite("theta", &HestonParams::theta)
        .def_readwrite("sigma", &HestonParams::sigma)
        .def_readwrite("rho", &HestonParams::rho);

    py::class_<HestonMonteCarloPricer>(m, "HestonMonteCarloPricer")
        .def(py::init<>())
        .def("price_call_scalar", &HestonMonteCarloPricer::price_call_scalar, 
             py::arg("params"), py::arg("K"), py::arg("T"), py::arg("num_paths"), py::arg("num_steps"))
        .def("price_call_avx2", &HestonMonteCarloPricer::price_call_avx2,
             py::arg("params"), py::arg("K"), py::arg("T"), py::arg("num_paths"), py::arg("num_steps"));
}
