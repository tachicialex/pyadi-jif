import adijif
import pprint

clk = adijif.ad9545(solver="gekko")

clk.avoid_min_max_PLL_rates = True
clk.minimize_input_dividers = True

input_refs = [1, 10e6, 0, 0]
output_clocks = [30720000, 0, 0 , 0, 0, 0, 0 ,0 ,0, 0]

input_refs = list(map(int, input_refs))  # force to be ints
output_clocks = list(map(int, output_clocks))  # force to be ints

clk.set_requested_clocks(input_refs, output_clocks)

clk.solve()

o = clk.get_config()

pprint.pprint(o)
