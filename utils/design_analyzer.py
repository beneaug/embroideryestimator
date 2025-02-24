import pyembroidery
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict
import tempfile
import os

class DesignAnalyzer:
    def __init__(self):
        self.pattern = None
        self.dimensions = None
        self.stitch_count = 0
        self.color_changes = 0
        
    def analyze_file(self, file_data: bytes) -> Dict:
        """Analyze uploaded embroidery file and return design metrics"""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".dst") as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
            
        try:
            self.pattern = pyembroidery.read(tmp_path)
            os.remove(tmp_path)
            
            if not self.pattern or not hasattr(self.pattern, 'stitches'):
                raise ValueError("Invalid design file")
                
            return self._calculate_metrics()
        except Exception as e:
            raise Exception(f"Error analyzing design: {str(e)}")

    def _calculate_metrics(self) -> Dict:
        """Calculate design metrics including dimensions and thread usage"""
        stitches = np.array(self.pattern.stitches)
        x_coords = stitches[:, 0]
        y_coords = stitches[:, 1]
        
        # Calculate bounding box
        min_x, max_x = np.min(x_coords), np.max(x_coords)
        min_y, max_y = np.min(y_coords), np.max(y_coords)
        
        # Convert to mm (DST units are 0.1mm)
        width_mm = (max_x - min_x) * 0.1
        height_mm = (max_y - min_y) * 0.1
        
        # Calculate thread length
        thread_length = 0
        for i in range(1, len(stitches)):
            dx = stitches[i][0] - stitches[i-1][0]
            dy = stitches[i][1] - stitches[i-1][1]
            thread_length += np.sqrt(dx*dx + dy*dy)
            
        # Convert to yards (0.1mm to yards)
        thread_length_yards = thread_length * 0.1 / 914.4
        
        return {
            "width_mm": width_mm,
            "height_mm": height_mm,
            "stitch_count": len(stitches),
            "thread_length_yards": thread_length_yards,
            "color_changes": len(set(stitches[:, 2])) - 1
        }

    def generate_preview(self, show_foam: bool = False, foam_color: str = "#FF0000") -> plt.Figure:
        """Generate preview of the design with optional foam overlay"""
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # Plot stitches
        stitches = np.array(self.pattern.stitches)
        ax.plot(stitches[:, 0], stitches[:, 1], 'k-', linewidth=0.5)
        
        if show_foam:
            # Add foam overlay with padding
            padding = 5  # 0.5mm in DST units
            min_x, max_x = np.min(stitches[:, 0]), np.max(stitches[:, 0])
            min_y, max_y = np.min(stitches[:, 1]), np.max(stitches[:, 1])
            
            rect = plt.Rectangle((min_x - padding, min_y - padding),
                               max_x - min_x + 2*padding,
                               max_y - min_y + 2*padding,
                               facecolor=foam_color,
                               alpha=0.3)
            ax.add_patch(rect)
        
        ax.set_aspect('equal')
        ax.axis('off')
        return fig
