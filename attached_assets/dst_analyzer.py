import streamlit as st
import pyembroidery
import matplotlib.pyplot as plt
import math
import tempfile
import os

def main():
    st.title("DST File Analyzer")
    
    uploaded_file = st.file_uploader("Upload a DST file", type=["dst"])
    
    if uploaded_file is not None:
        try:
            # Save the uploaded file to a temporary file
            with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".dst") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            # Read the DST file using its file path
            pattern = pyembroidery.read(tmp_path)
            
            # Remove the temporary file after reading
            os.remove(tmp_path)
            
            if pattern is None:
                st.error("Failed to read DST file. Please ensure the file is a valid DST file.")
                return
        except Exception as e:
            st.error(f"Error reading DST file: {e}")
            return
        
        # Verify that the pattern contains stitch data
        if not hasattr(pattern, 'stitches') or pattern.stitches is None:
            st.error("The DST file does not contain valid stitch data.")
            return

        # Basic design information
        stitch_count = len(pattern.stitches)
        # DST files often do not have thread information
        if hasattr(pattern, "threads") and pattern.threads is not None:
            color_count = len(pattern.threads)
        else:
            color_count = "N/A"
        
        # Calculate thread length and group consecutive stitches into segments
        thread_length = 0.0
        min_x, max_x = float('inf'), -float('inf')
        min_y, max_y = float('inf'), -float('inf')
        segments = []
        current_segment = []
        previous_stitch = None
        
        for stitch in pattern.stitches:
            x, y, command = stitch
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            
            if command == pyembroidery.STITCH:
                current_segment.append((x, y))
                if previous_stitch is not None:
                    dx = x - previous_stitch[0]
                    dy = y - previous_stitch[1]
                    thread_length += math.hypot(dx, dy)
                previous_stitch = (x, y)
            else:
                if current_segment:
                    segments.append(current_segment)
                    current_segment = []
                previous_stitch = None
        
        if current_segment:
            segments.append(current_segment)

        # Convert DST units (0.1 mm units) to display metrics
        thread_length_m = (thread_length * 0.1) / 1000  # Convert to meters
        width = (max_x - min_x) * 0.1  # mm
        height = (max_y - min_y) * 0.1  # mm

        # Create a preview plot using matplotlib
        fig, ax = plt.subplots(figsize=(8, 8))
        for seg in segments:
            if seg:
                xs, ys = zip(*seg)
                ax.plot(xs, ys, linewidth=0.5)
        ax.invert_yaxis()
        ax.set_aspect('equal')
        ax.set_title("Embroidery Preview")
        ax.set_xlabel("X (0.1 mm units)")
        ax.set_ylabel("Y (0.1 mm units)")
        plt.tight_layout()

        # Display design information
        st.subheader("Design Information")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Stitches", stitch_count)
            st.metric("Width", f"{width:.1f} mm")
        with col2:
            st.metric("Color Changes", color_count)
            st.metric("Height", f"{height:.1f} mm")
        with col3:
            st.metric("Thread Length", f"{thread_length_m:.2f} meters")
        
        # Display thread colors if available; otherwise, notify the user.
        if hasattr(pattern, "threads") and pattern.threads is not None:
            st.subheader("Thread Colors")
            cols = st.columns(4)
            for i, thread in enumerate(pattern.threads):
                with cols[i % 4]:
                    r, g, b = thread.color
                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                    st.color_picker(
                        f"Color {i+1}",
                        value=hex_color,
                        key=f"color_{i}",
                        disabled=True
                    )
        else:
            st.info("Thread color information is not available for DST files.")
        
        # Show the design preview plot
        st.subheader("Design Preview")
        st.pyplot(fig)

if __name__ == "__main__":
    main()
