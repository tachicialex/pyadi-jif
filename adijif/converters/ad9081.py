"""AD9081 high speed MxFE clocking model."""
from abc import ABCMeta, abstractmethod
from typing import Any, Dict, List, Union

from ..solvers import GEKKO, CpoModel, CpoSolveResult  # type: ignore
from .ad9081_util import _load_rx_config_modes, _load_tx_config_modes
from .converter import converter


class ad9081_core(converter, metaclass=ABCMeta):
    """AD9081 high speed MxFE model.

    This model supports both direct clock configurations and on-board
    generation

    Clocking: AD9081 can internally generate or leverage external clocks. The
    high speed clock within the system is referred to as the DAC clock and
    the ADC clock will be a divided down version of the clock:
        adc_clock  == dac_clock / L, where L = 1,2,3,4


    For internal generation, the DAC clock is generated through an integer PLL
    through the following relation:
        dac_clock == ((m_vco * n_vco) / R * ref_clock) / D

    For external clocks, the clock must be provided at the DAC clock rate

    Once we have the DAC clock the data rates can be directly evaluated into
    each JESD framer:

    rx_baseband_sample_rate = (dac_clock / L) / datapath_decimation
    tx_baseband_sample_rate = dac_clock / datapath_interpolation

    """

    device_clock_available = None  # FIXME
    device_clock_ranges = None  # FIXME

    model: Union[GEKKO, CpoModel] = None

    name = "AD9081"

    # Integrated PLL constants
    l_available = [1, 2, 3, 4]
    l = 1  # pylint:  disable=E741
    m_vco_available = [5, 7, 8, 11]  # 8 is nominal
    m_vco = 8
    n_vco_available = [*range(2, 50 + 1)]
    n_vco = 2
    r_available = [1, 2, 3, 4]
    r = 1
    d_available = [1, 2, 3, 4]
    d = 1
    # Integrated PLL limits
    pfd_min = 25e6
    pfd_max = 750e6
    vco_min = 6e9
    vco_max = 12e9

    # JESD parameters
    available_jesd_modes = ["jesd204b", "jesd204c"]
    M_available = [1, 2, 3, 4, 6, 8, 12, 16]
    L_available = [1, 2, 3, 4, 6, 8]
    N_available = [12, 16]
    Np_available = [12, 16, 24]
    F_available = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32]
    S_available = [1, 2, 4, 8]
    # FIXME
    K_available = [4, 8, 12, 16, 20, 24, 28, 32]
    CS_available = [0, 1, 2, 3]
    CF_available = [0]
    # FIXME

    # Clocking constraints
    clocking_option_available = ["integrated_pll", "direct"]
    _clocking_option = "integrated_pll"
    bit_clock_min_available = {"jesd204b": 1.5e9, "jesd204c": 6e9}
    bit_clock_max_available = {"jesd204b": 15.5e9, "jesd204c": 24.75e9}

    config = {}  # type: ignore

    device_clock_max = 12e9
    _model_type = "adc"

    def _check_valid_internal_configuration(self) -> None:
        # FIXME
        pass

    def get_config(self, solution: CpoSolveResult = None) -> Dict:
        """Extract configurations from solver results.

        Collect internal converter configuration and output clock definitions
        leading to connected devices (clock chips, FPGAs)

        Args:
            solution (CpoSolveResult): CPlex solution. Only needed for CPlex solver

        Returns:
            Dict: Dictionary of clocking rates and dividers for configuration
        """
        # FIXME
        return {"clocking_option": self.clocking_option}

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by get_required_clocks

        Returns:
            List[str]: List of strings of clock names in order
        """
        clk = (
            "ad9081_dac_clock" if self.clocking_option == "direct" else "ad9081_pll_ref"
        )
        return [clk, "ad9081_sysref"]

    @property
    @abstractmethod
    def _converter_clock_config(self) -> None:
        """Define source clocking relation based on ADC, DAC, or both.

        Raises:
            NotImplementedError: Method not implemented
        """
        raise NotImplementedError

    def _pll_config(self, rxtx: bool = False) -> Dict:

        self._converter_clock_config()  # type: ignore

        self.config["m_vco"] = self._convert_input([5, 7, 8, 11], "m_vco")
        self.config["n_vco"] = self._convert_input([*range(2, 51)], "n_vco")
        self.config["r"] = self._convert_input([1, 2, 3, 4], "r")
        self.config["d"] = self._convert_input([1, 2, 3, 4], "d")

        self.config["ref_clk"] = self._add_intermediate(
            self.config["converter_clk"]
            * self.config["d"]
            * self.config["r"]
            / (self.config["m_vco"] * self.config["n_vco"])
        )
        # if self.solver == "gekko":
        #     self.config["ref_clk"] = self.model.Var(
        #         integer=True,
        #         lb=1e6,
        #         ub=self.device_clock_max,
        #         value=self.device_clock_max,
        #     )
        # elif self.solver == "CPLEX":
        #     # self.config["ref_clk"] = integer_var(
        #     #     int(1e6), int(self.device_clock_max), "ref_clk"
        #     # )
        #     self.config["ref_clk"] = (
        #         self.config["converter_clk"]
        #         * self.config["d"]
        #         * self.config["r"]
        #         / (self.config["m_vco"] * self.config["n_vco"])
        #     )
        # else:
        #     raise Exception("Unknown solver")

        self.config["vco"] = self._add_intermediate(
            self.config["ref_clk"]
            * self.config["m_vco"]
            * self.config["n_vco"]
            / self.config["r"],
        )

        # if self.solver == "gekko":
        #     self.config["vco"] = self.model.Intermediate(
        #         self.config["ref_clk"]
        #         * self.config["m_vco"]
        #         * self.config["n_vco"]
        #         / self.config["r"],
        #     )
        # elif self.solver == "CPLEX":
        #     self.config["vco"] = (
        #         self.config["ref_clk"]
        #         * self.config["m_vco"]
        #         * self.config["n_vco"]
        #         / self.config["r"]
        #     )
        # else:
        #     raise Exception("Unknown solver: %s" % self.solver)

        self._add_equation(
            [
                self.config["vco"] >= self.vco_min,
                self.config["vco"] <= self.vco_max,
                self.config["ref_clk"] / self.config["r"] <= self.pfd_max,
                self.config["ref_clk"] / self.config["r"] >= self.pfd_min,
                # self.config["converter_clk"] <= self.device_clock_max,
                self.config["converter_clk"]
                >= (
                    self.converter_clock_min
                    if not rxtx
                    else self.dac.converter_clock_min  # type: ignore
                ),
                self.config["converter_clk"]
                <= (
                    self.converter_clock_max
                    if not rxtx
                    else self.dac.converter_clock_max  # type: ignore
                ),
            ]
        )

        return self.config["ref_clk"]

    def get_required_clocks(self) -> List:
        """Generate list required clocks.

        For AD9081 this will contain [converter clock, sysref requirement SOS]

        Returns:
            List: List of solver variables, equations, and constants

        Raises:
            Exception: If direct clocking is used. Not yet implemented
        """
        # SYSREF
        self.config = {}
        self.config["lmfc_divisor_sysref"] = self._convert_input(
            [*range(1, 21)], "lmfc_divisor_sysref"
        )

        if self.solver == "gekko":
            self.config["sysref"] = self.model.Intermediate(
                self.multiframe_clock  # type: ignore
                / (
                    self.config["lmfc_divisor_sysref"]
                    * self.config["lmfc_divisor_sysref"]
                )
            )
        elif self.solver == "CPLEX":
            self.config["sysref"] = self.multiframe_clock / (
                self.config["lmfc_divisor_sysref"] * self.config["lmfc_divisor_sysref"]
            )

        # Device Clocking
        if self.clocking_option == "direct":
            raise Exception("Not implemented yet")
            # adc_clk = self.sample_clock * self.datapath_decimation
        else:
            clk = self._pll_config()  # type: ignore

        # Objectives
        # self.model.Obj(self.config["sysref"])  # This breaks many searches
        # self.model.Obj(-1*self.config["lmfc_divisor_sysref"])

        return [clk, self.config["sysref"]]


class ad9081_rx(ad9081_core):
    """AD9081 Receive model."""

    _model_type = "adc"

    converter_clock_min = 1.45e9
    converter_clock_max = 4e9

    sample_clock_min = 312.5e6 / 16
    sample_clock_max = 4e9

    quick_configuration_modes = _load_rx_config_modes()

    decimation_available = [
        1,
        2,
        3,
        4,
        6,
        8,
        9,
        12,
        16,
        18,
        24,
        32,
        36,
        48,
        64,
        72,
        96,
        144,
    ]
    decimation = 1

    def __init__(
        self, model: Union[GEKKO, CpoModel] = None, solver: str = None
    ) -> None:
        """Initialize AD9081 clocking model for RX.

        This is a common class used to handle RX constraints
        together.

        Args:
            model (GEKKO,CpoModel): Solver model
            solver (str): Solver name (gekko or CPLEX)
        """
        if solver:
            self.solver = solver
        if model:
            self.model = model
        self.set_quick_configuration_mode("0")

    def _converter_clock_config(self) -> None:
        """RX specific configuration of internall PLL config.

        This method will update the config struct to include
        the RX clocking constraints

        Raises:
            Exception: If solver is not valid
        """
        adc_clk = self.decimation * self.sample_clock
        self.config["l"] = self._convert_input([1, 2, 3, 4], "l")
        self.config["adc_clk"] = self._convert_input(adc_clk)

        if self.solver == "gekko":
            self.config["converter_clk"] = self.model.Intermediate(
                self.config["adc_clk"] * self.config["l"]
            )
        elif self.solver == "CPLEX":
            self.config["converter_clk"] = self.config["adc_clk"] * self.config["l"]
        else:
            raise Exception(f"Unknown solver {self.solver}")


class ad9081_tx(ad9081_core):
    """AD9081 Transmit model."""

    _model_type = "dac"

    converter_clock_min = 2.9e9
    converter_clock_max = 12e9

    sample_clock_min = 2.9e9 / (6 * 24)  # with max interpolation
    sample_clock_max = 12e9

    quick_configuration_modes = _load_tx_config_modes()

    interpolation_available = [
        1,
        2,
        3,
        4,
        6,
        8,
        9,
        12,
        16,
        18,
        24,
        32,
        36,
        48,
        64,
        72,
        96,
        144,
    ]
    interpolation = 1

    def __init__(
        self, model: Union[GEKKO, CpoModel] = None, solver: str = None
    ) -> None:
        """Initialize AD9081 clocking model for TX.

        This is a common class used to handle TX constraints
        together.

        Args:
            model (GEKKO,CpoModel): Solver model
            solver (str): Solver name (gekko or CPLEX)
        """
        if solver:
            self.solver = solver
        if model:
            self.model = model
        self.set_quick_configuration_mode("0")

    def _converter_clock_config(self) -> None:
        """TX specific configuration of internall PLL config.

        This method will update the config struct to include
        the TX clocking constraints

        Raises:
            Exception: If solver is not valid
        """
        dac_clk = self.interpolation * self.sample_clock
        self.config["dac_clk"] = self._convert_input(dac_clk)
        if self.solver == "gekko":
            self.config["converter_clk"] = self.model.Intermediate(
                self.config["dac_clk"]
            )
        elif self.solver == "CPLEX":
            self.config["converter_clk"] = self.config["dac_clk"]
        else:
            raise Exception(f"Unknown solver {self.solver}")


class ad9081(ad9081_core):
    """AD9081 combined transmit and receive model."""

    converter_clock_min = ad9081_rx.converter_clock_min
    converter_clock_max = ad9081_rx.converter_clock_max
    quick_configuration_modes: Dict[str, Any] = {}

    def __init__(
        self, model: Union[GEKKO, CpoModel] = None, solver: str = None
    ) -> None:
        """Initialize AD9081 clocking model for TX and RX.

        This is a common class used to handle TX and RX constraints
        together.

        Args:
            model (GEKKO,CpoModel): Solver model
            solver (str): Solver name (gekko or CPLEX)
        """
        if solver:
            self.solver = solver
        self.adc = ad9081_rx(model, solver=self.solver)
        self.dac = ad9081_tx(model, solver=self.solver)
        self.model = model

    def validate_config(self) -> None:
        """Validate device configurations including JESD and clocks of both ADC and DAC.

        This check only is for static configuration that does not include
        variables which are solved.
        """
        self.adc.validate_config()
        self.dac.validate_config()

    def _get_converters(self) -> List[Union[converter, converter]]:
        return [self.adc, self.dac]

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by get_required_clocks

        Returns:
            List[str]: List of strings of clock names in order
        """
        clk = (
            "ad9081_dac_clock"
            if self.adc.clocking_option == "direct"
            else "ad9081_pll_ref"
        )
        return [clk, "ad9081_adc_sysref", "ad9081_dac_sysref"]

    def _converter_clock_config(self) -> None:
        adc_clk = self.adc.decimation * self.adc.sample_clock
        dac_clk = self.dac.interpolation * self.dac.sample_clock
        l = dac_clk / adc_clk
        if l not in self.adc.l_available:
            raise Exception(
                f"ADC clock must be DAC clock/L where L={self.adc.l_available}."
                + f" Got {l}"
            )

        self.config["dac_clk"] = self._convert_input(dac_clk)
        self.config["adc_clk"] = self._convert_input(adc_clk)
        if self.solver == "gekko":
            self.config["converter_clk"] = self.model.Intermediate(
                self.config["dac_clk"]
            )
        elif self.solver == "CPLEX":
            self.config["converter_clk"] = self.config["dac_clk"]
        else:
            raise Exception(f"Unknown solver {self.solver}")

    def get_required_clocks(self) -> List:
        """Generate list required clocks.

        For AD9081 this will contain [converter clock, sysref requirement SOS]

        Returns:
            List: List of solver variables, equations, and constants

        Raises:
            Exception: If direct clocking is used. Not yet implemented
        """
        # SYSREF
        self.config = {}
        self.config["adc_lmfc_divisor_sysref"] = self._convert_input(
            [*range(1, 21)], "adc_lmfc_divisor_sysref"
        )
        self.config["dac_lmfc_divisor_sysref"] = self._convert_input(
            [*range(1, 21)], "dac_lmfc_divisor_sysref"
        )

        if self.solver == "gekko":
            self.config["sysref_adc"] = self.model.Intermediate(
                self.adc.multiframe_clock
                / (
                    self.config["adc_lmfc_divisor_sysref"]
                    * self.config["adc_lmfc_divisor_sysref"]
                )
            )
            self.config["sysref_dac"] = self.model.Intermediate(
                self.dac.multiframe_clock
                / (
                    self.config["dac_lmfc_divisor_sysref"]
                    * self.config["dac_lmfc_divisor_sysref"]
                )
            )
        elif self.solver == "CPLEX":
            self.config["sysref_adc"] = self.adc.multiframe_clock / (
                self.config["adc_lmfc_divisor_sysref"]
                * self.config["adc_lmfc_divisor_sysref"]
            )
            self.config["sysref_dac"] = self.dac.multiframe_clock / (
                self.config["dac_lmfc_divisor_sysref"]
                * self.config["dac_lmfc_divisor_sysref"]
            )
        else:
            raise Exception(f"Unknown solver {self.solver}")

        # Device Clocking
        if self.clocking_option == "direct":
            raise Exception("Not implemented yet")
            # adc_clk = self.sample_clock * self.datapath_decimation
        else:
            clk = self._pll_config(rxtx=True)

        # Objectives
        # self.model.Obj(self.config["sysref"])  # This breaks many searches
        # self.model.Obj(-1*self.config["lmfc_divisor_sysref"])

        return [clk, self.config["sysref_adc"], self.config["sysref_dac"]]
