# flake8: noqa

import pytest

import adijif


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_adrv9009_rx_ad9528_solver_compact(solver):
    vcxo = 122.88e6

    sys = adijif.system("adrv9009_rx", "ad9528", "xilinx", vcxo, solver=solver)

    # Get Converter clocking requirements
    sys.converter.sample_clock = 122.88e6
    sys.converter.L = 2
    sys.converter.M = 4
    sys.converter.N = 16
    sys.converter.Np = 16

    sys.converter.K = 32
    sys.converter.F = 4
    assert sys.converter.S == 1
    # sys.Debug_Solver = True

    assert 9830.4e6 / 2 == sys.converter.bit_clock
    assert sys.converter.multiframe_clock == 7.68e6 / 2  # LMFC
    assert sys.converter.device_clock == 9830.4e6 / 2 / 40

    # Set FPGA config
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.request_fpga_core_clock_ref = True

    # Set clock chip
    sys.clock.d = [*range(1, 257)]  # Limit output dividers

    cfg = sys.solve()
    print(cfg)

    ref = {
        "gekko": {"clock": {"r1": 2, "n2": 12, "m1": 5, "out_dividers": [6, 8, 192]}},
        "CPLEX": {"clock": {"r1": 2, "n2": 12, "m1": 5, "out_dividers": [6, 8, 192]}},
    }

    assert cfg["clock"]["r1"] == ref[solver]["clock"]["r1"]
    assert cfg["clock"]["n2"] == ref[solver]["clock"]["n2"]
    assert cfg["clock"]["m1"] == ref[solver]["clock"]["m1"]
    assert (
        cfg["clock"]["output_clocks"]["ADRV9009_fpga_ref_clk"]["rate"] == 122880000.0
    )  # 98304000
    for div in cfg["clock"]["out_dividers"]:
        assert div in ref[solver]["clock"]["out_dividers"]


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_adrv9009_tx_ad9528_solver_compact(solver):
    vcxo = 122.88e6

    sys = adijif.system("adrv9009_tx", "ad9528", "xilinx", vcxo, solver=solver)

    # Get Converter clocking requirements
    sys.converter.sample_clock = 122.88e6
    sys.converter.L = 2
    sys.converter.M = 4
    sys.converter.N = 16
    sys.converter.Np = 16

    sys.converter.K = 32
    sys.converter.F = 4
    assert sys.converter.S == 1
    # sys.Debug_Solver = True

    assert 9830.4e6 / 2 == sys.converter.bit_clock
    assert sys.converter.multiframe_clock == 7.68e6 / 2  # LMFC
    assert sys.converter.device_clock == 9830.4e6 / 2 / 40

    # Set FPGA config
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.request_fpga_core_clock_ref = True

    # Set clock chip
    sys.clock.d = [*range(1, 257)]  # Limit output dividers

    cfg = sys.solve()
    print(cfg)

    ref = {
        "gekko": {"clock": {"r1": 2, "n2": 12, "m1": 5, "out_dividers": [6, 8, 192]}},
        "CPLEX": {"clock": {"r1": 2, "n2": 12, "m1": 5, "out_dividers": [6, 8, 192]}},
    }

    assert cfg["clock"]["r1"] == ref[solver]["clock"]["r1"]
    assert cfg["clock"]["n2"] == ref[solver]["clock"]["n2"]
    assert cfg["clock"]["m1"] == ref[solver]["clock"]["m1"]
    assert (
        cfg["clock"]["output_clocks"]["ADRV9009_fpga_ref_clk"]["rate"] == 122880000.0
    )  # 98304000
    for div in cfg["clock"]["out_dividers"]:
        assert div in ref[solver]["clock"]["out_dividers"]
