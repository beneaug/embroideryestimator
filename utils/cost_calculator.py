from dataclasses import dataclass
from typing import Dict, List
import math

@dataclass
class ThreadPrices:
    POLYNEON_5500: float = 9.69
    POLYNEON_1100: float = 3.19
    BOBBIN_PRICE: float = 35.85 / 144  # Price per bobbin
    BOBBIN_LENGTH: float = 124  # yards per bobbin
    FOAM_SHEET: float = 2.45

class CostCalculator:
    def __init__(self):
        self.prices = ThreadPrices()
        self.HOOPING_TIME = 45/60  # 45 seconds converted to minutes

    def calculate_thread_cost(self, thread_length: float, quantity: int, active_heads: int = 15, num_colors: int = 1) -> Dict:
        """Calculate thread costs including buffer"""
        pieces_per_cycle = min(active_heads, quantity)
        total_cycles = math.ceil(quantity / pieces_per_cycle)

        # Calculate thread per piece with 5% buffer
        thread_per_piece = thread_length * 1.05
        total_thread = thread_per_piece * quantity

        # Calculate spools needed per head (one spool per color per head minimum)
        spools_per_color = math.ceil(total_thread / (active_heads * 5500))
        spools_per_head = max(spools_per_color, 1) * num_colors
        thread_cost = spools_per_head * self.prices.POLYNEON_5500 * active_heads

        # Calculate bobbin usage
        bobbins_needed = math.ceil(quantity * thread_length / self.prices.BOBBIN_LENGTH)
        bobbin_cost = bobbins_needed * self.prices.BOBBIN_PRICE

        return {
            "thread_cost": thread_cost,
            "bobbin_cost": bobbin_cost,
            "total_spools": spools_per_head * active_heads,
            "spools_per_head": spools_per_head,
            "total_bobbins": bobbins_needed,
            "cycles": total_cycles,
            "pieces_per_cycle": pieces_per_cycle
        }

    def calculate_foam_cost(self, width_mm: float, height_mm: float, quantity: int) -> Dict:
        """Calculate foam costs based on design dimensions"""
        # Convert mm to inches and add 0.5" padding
        width_inches = (width_mm / 25.4) + 1
        height_inches = (height_mm / 25.4) + 1

        # Calculate pieces per sheet (18x12 inches)
        pieces_per_sheet_h = math.floor(18 / width_inches) * math.floor(12 / height_inches)
        pieces_per_sheet_v = math.floor(18 / height_inches) * math.floor(12 / width_inches)
        pieces_per_sheet = max(pieces_per_sheet_h, pieces_per_sheet_v)

        sheets_needed = math.ceil(quantity / pieces_per_sheet)
        total_cost = sheets_needed * self.prices.FOAM_SHEET

        return {
            "sheets_needed": sheets_needed,
            "pieces_per_sheet": pieces_per_sheet,
            "total_cost": total_cost,
            "foam_unit_cost": self.prices.FOAM_SHEET
        }

    def calculate_runtime(self, stitch_count: int, thread_weight: int, quantity: int, active_heads: int = 15) -> Dict:
        """Calculate estimated runtime in minutes considering parallel processing"""
        # Base stitch rate based on thread weight
        rpm = 750 if thread_weight == 40 else 400

        # Calculate pieces per cycle and total cycles
        pieces_per_cycle = min(active_heads, quantity)
        total_cycles = math.ceil(quantity / pieces_per_cycle)
        remaining_pieces = quantity % pieces_per_cycle
        last_cycle_pieces = remaining_pieces if remaining_pieces > 0 else pieces_per_cycle

        # Calculate time components per cycle
        stitch_time = stitch_count / rpm  # Time to stitch one piece
        hooping_time_per_cycle = self.HOOPING_TIME * pieces_per_cycle  # Time to hoop all pieces in a cycle

        # Time per cycle is the maximum of stitching time and hooping time
        cycle_time = max(stitch_time, hooping_time_per_cycle)

        # Calculate buffer time (5% of cycle time)
        buffer_time = cycle_time * 0.05

        # Calculate last cycle time
        last_cycle_hooping = self.HOOPING_TIME * last_cycle_pieces
        last_cycle_time = max(stitch_time, last_cycle_hooping)

        # Total runtime = full cycles with buffer + last cycle
        total_runtime = cycle_time * (total_cycles - 1)  # Full cycles
        total_runtime += buffer_time * (total_cycles - 1)  # Buffer between cycles
        total_runtime += last_cycle_time  # Last cycle (no buffer needed after)

        return {
            "total_runtime": total_runtime,
            "stitch_time": stitch_time,
            "hooping_time_per_cycle": hooping_time_per_cycle,
            "cycle_time": cycle_time,
            "buffer_time": buffer_time,
            "cycles": total_cycles,
            "pieces_per_cycle": pieces_per_cycle,
            "last_cycle_pieces": last_cycle_pieces
        }