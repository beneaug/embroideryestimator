import pandas as pd
from typing import List
from datetime import datetime
from .database import Job, MaterialUsage, CostBreakdown

def export_to_excel(jobs: List[Job], filename: str) -> bytes:
    """Export jobs data to Excel file"""
    # Create DataFrames for each type of data
    jobs_data = []
    materials_data = []
    costs_data = []

    for job in jobs:
        # Basic job information
        job_dict = {
            'Job ID': job.id,
            'Created At': job.created_at,
            'Design Name': job.design_name,
            'Stitch Count': job.stitch_count,
            'Thread Length (yards)': job.thread_length_yards,
            'Dimensions': f"{job.width_mm:.1f}mm × {job.height_mm:.1f}mm",
            'Thread Weight': job.thread_weight,
            'Color Changes': job.color_changes,
            'Quantity': job.quantity,
            'Active Heads': job.active_heads,
            'Total Runtime (min)': job.total_runtime,
            'Pieces per Cycle': job.pieces_per_cycle,
            'Total Cycles': job.total_cycles,
            'Use Foam': job.use_foam,
            'Use Coloreel': job.use_coloreel,
            'Complexity Score': job.complexity_score
        }
        jobs_data.append(job_dict)

        # Materials usage
        for material in job.materials:
            material_dict = {
                'Job ID': job.id,
                'Material Type': material.material_type,
                'Quantity': material.quantity,
                'Unit': material.unit,
                'Unit Cost': material.unit_cost
            }
            materials_data.append(material_dict)

        # Cost breakdown
        for cost in job.costs:
            cost_dict = {
                'Job ID': job.id,
                'Cost Type': cost.cost_type,
                'Amount': cost.amount,
                'Details': str(cost.details) if cost.details else ''
            }
            costs_data.append(cost_dict)

    # Create Excel writer object
    output = pd.ExcelWriter(filename, engine='openpyxl')

    # Convert to DataFrames and write to Excel
    pd.DataFrame(jobs_data).to_excel(output, sheet_name='Jobs', index=False)
    pd.DataFrame(materials_data).to_excel(output, sheet_name='Materials', index=False)
    pd.DataFrame(costs_data).to_excel(output, sheet_name='Costs', index=False)

    # Save to bytes
    output.close()
    with open(filename, 'rb') as f:
        return f.read()

def export_to_csv(jobs: List[Job]) -> bytes:
    """Export jobs data to CSV file"""
    # Create a flattened version of the data
    flattened_data = []
    
    for job in jobs:
        # Get cost breakdown
        costs = {c.cost_type: c.amount for c in job.costs}
        
        row = {
            'Job ID': job.id,
            'Created At': job.created_at,
            'Design Name': job.design_name,
            'Stitch Count': job.stitch_count,
            'Thread Length (yards)': job.thread_length_yards,
            'Width (mm)': job.width_mm,
            'Height (mm)': job.height_mm,
            'Thread Weight': job.thread_weight,
            'Color Changes': job.color_changes,
            'Quantity': job.quantity,
            'Active Heads': job.active_heads,
            'Total Runtime (min)': job.total_runtime,
            'Pieces per Cycle': job.pieces_per_cycle,
            'Total Cycles': job.total_cycles,
            'Thread Cost': costs.get('thread', 0),
            'Bobbin Cost': costs.get('bobbin', 0),
            'Foam Cost': costs.get('foam', 0),
            'Total Cost': costs.get('total', 0),
            'Use Foam': job.use_foam,
            'Use Coloreel': job.use_coloreel,
            'Complexity Score': job.complexity_score
        }
        flattened_data.append(row)
    
    # Convert to DataFrame and return CSV bytes
    df = pd.DataFrame(flattened_data)
    return df.to_csv(index=False).encode('utf-8')
