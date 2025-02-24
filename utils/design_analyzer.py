import pyembroidery
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict
import tempfile
import os
import math

class DesignAnalyzer:
    def __init__(self):
        self.pattern = None
        self.dimensions = None
        self.stitch_count = 0

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

    def _segment_by_color(self, stitches: np.ndarray, num_colors: int) -> List[np.ndarray]:
        """Segment stitches evenly by specified number of colors"""
        if num_colors <= 0:
            return [stitches]

        # Split stitches into roughly equal segments
        stitches_per_color = len(stitches) // num_colors
        segments = []

        for i in range(num_colors):
            start_idx = i * stitches_per_color
            end_idx = start_idx + stitches_per_color if i < num_colors - 1 else len(stitches)
            segments.append(stitches[start_idx:end_idx])

        return segments

    def _calculate_density_map(self, stitches: np.ndarray, grid_size: int = 50) -> np.ndarray:
        """Calculate stitch density map"""
        x_coords = stitches[:, 0]
        y_coords = stitches[:, 1]

        x_min, x_max = np.min(x_coords), np.max(x_coords)
        y_min, y_max = np.min(y_coords), np.max(y_coords)

        # Create 2D histogram
        density_map, _, _ = np.histogram2d(
            x_coords, y_coords,
            bins=grid_size,
            range=[[x_min, x_max], [y_min, y_max]]
        )

        return density_map

    def _calculate_complexity_score(self, stitches: np.ndarray) -> Dict:
        """Calculate complexity metrics for the design"""
        if len(stitches) < 2:
            return {
                "complexity_score": 0,
                "direction_changes": 0,
                "density_score": 0,
                "stitch_length_variance": 0
            }

        # Calculate direction changes
        vectors = np.diff(stitches[:, :2], axis=0)
        angles = np.arctan2(vectors[:, 1], vectors[:, 0])
        angle_changes = np.abs(np.diff(angles))
        direction_changes = np.sum(angle_changes > np.pi/4)  # Count changes > 45 degrees

        # Calculate stitch density
        area_mm2 = (np.max(stitches[:, 0]) - np.min(stitches[:, 0])) * \
                   (np.max(stitches[:, 1]) - np.min(stitches[:, 1])) * 0.01  # Convert to mm²
        density = len(stitches) / area_mm2 if area_mm2 > 0 else 0
        density_score = min(density / 5, 10)  # Normalize density score

        # Calculate stitch length variance
        stitch_lengths = np.sqrt(np.sum(vectors * vectors, axis=1))
        length_variance = np.var(stitch_lengths) if len(stitch_lengths) > 0 else 0
        length_variance_score = min(length_variance / 100, 10)

        # Calculate overall complexity score (0-100)
        complexity_score = min(
            (direction_changes / len(stitches) * 40) +  # Weight direction changes
            (density_score * 30) +                      # Weight density
            (length_variance_score * 30),               # Weight length variance
            100
        )

        return {
            "complexity_score": round(complexity_score, 2),
            "direction_changes": int(direction_changes),
            "density_score": round(density_score, 2),
            "stitch_length_variance": round(length_variance_score, 2)
        }

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

        # Calculate complexity metrics
        complexity_data = self._calculate_complexity_score(stitches)

        return {
            "width_mm": width_mm,
            "height_mm": height_mm,
            "stitch_count": len(stitches),
            "thread_length_yards": thread_length_yards,
            **complexity_data
        }

    def generate_preview(self, show_foam: bool = False, foam_color: str = "#FF0000", 
                        num_colors: int = 1, thread_colors: List[str] = None) -> plt.Figure:
        """Generate preview of the design with density map and optional foam overlay"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        stitches = np.array(self.pattern.stitches)
        # Rotate 180 degrees
        stitches[:, :2] = -stitches[:, :2]

        # Plot stitches by color segments in first subplot
        segments = self._segment_by_color(stitches, num_colors)
        colors = thread_colors if thread_colors else ['#000000'] * num_colors

        for i, segment in enumerate(segments):
            color = colors[i % len(colors)]
            ax1.plot(segment[:, 0], segment[:, 1], color=color, linewidth=0.5)

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
            ax1.add_patch(rect)

        ax1.set_aspect('equal')
        ax1.axis('off')
        ax1.set_title("Design Preview")

        # Plot density heatmap in second subplot
        density_map = self._calculate_density_map(stitches)
        im = ax2.imshow(density_map.T, cmap='hot', interpolation='nearest', origin='lower')
        plt.colorbar(im, ax=ax2, label='Stitch Density')
        ax2.set_title("Stitch Density Heatmap")
        ax2.axis('off')

        plt.tight_layout()
        return fig

    def get_complexity_description(self, complexity_score: float) -> str:
        """Return a human-readable description of the design complexity"""
        if complexity_score < 20:
            return "Simple design with basic stitching patterns"
        elif complexity_score < 40:
            return "Moderate complexity with some direction changes"
        elif complexity_score < 60:
            return "Complex design with frequent direction changes and varied density"
        elif complexity_score < 80:
            return "Very complex design with high stitch density and technical challenges"
        else:
            return "Extremely complex design requiring careful production consideration"