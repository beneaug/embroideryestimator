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

    def calculate_thread_cost(self, thread_length: float, quantity: int, active_heads: int = 15) -> Dict:
        """Calculate thread costs including buffer"""
        pieces_per_cycle = min(active_heads, quantity)
        total_cycles = math.ceil(quantity / pieces_per_cycle)

        # Calculate thread per cycle with 5% buffer
        thread_per_cycle = thread_length * pieces_per_cycle * 1.05
        total_thread = thread_per_cycle * total_cycles

        # Calculate spools needed
        spools_5500 = math.ceil(total_thread / 5500)
        thread_cost = spools_5500 * self.prices.POLYNEON_5500

        # Calculate bobbin usage
        bobbins_needed = math.ceil(quantity * thread_length / self.prices.BOBBIN_LENGTH)
        bobbin_cost = bobbins_needed * self.prices.BOBBIN_PRICE

        return {
            "thread_cost": thread_cost,
            "bobbin_cost": bobbin_cost,
            "total_spools": spools_5500,
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
            "total_cost": total_cost
        }

    def calculate_runtime(self, stitch_count: int, thread_weight: int, quantity: int, active_heads: int = 15) -> Dict:
        """Calculate estimated runtime in minutes including cycle information"""
        # Base stitch rate based on thread weight
        rpm = 750 if thread_weight == 40 else 400

        # Calculate time per piece in minutes
        time_per_piece = stitch_count / rpm

        # Calculate cycles
        pieces_per_cycle = min(active_heads, quantity)
        total_cycles = math.ceil(quantity / pieces_per_cycle)

        # Add 15% buffer between cycles
        cycle_time = time_per_piece * pieces_per_cycle
        buffer_time = cycle_time * 0.15
        total_time = (cycle_time + buffer_time) * total_cycles

        return {
            "total_runtime": total_time,
            "time_per_cycle": cycle_time,
            "buffer_per_cycle": buffer_time,
            "cycles": total_cycles,
            "pieces_per_cycle": pieces_per_cycle
        }