import streamlit as st
import io
from utils.design_analyzer import DesignAnalyzer
from utils.cost_calculator import CostCalculator
from utils.pdf_generator import PDFGenerator
import json

st.set_page_config(page_title="Embroidery Cost Calculator", layout="wide")

# Load custom CSS
with open("styles/custom.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def main():
    st.title("Embroidery Cost Calculator")
    
    # Initialize components
    analyzer = DesignAnalyzer()
    calculator = CostCalculator()
    pdf_gen = PDFGenerator()
    
    # Machine configuration
    st.sidebar.subheader("Machine Configuration")
    use_coloreel = st.sidebar.checkbox("Use Coloreel ITCU")
    heads = 2 if use_coloreel else 15
    
    # File upload
    uploaded_file = st.file_uploader("Upload DST/U01 File", type=["dst", "u01"])
    
    if uploaded_file:
        try:
            # Analyze design
            design_data = analyzer.analyze_file(uploaded_file.getvalue())
            
            # Display design preview
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Design Information")
                st.metric("Stitch Count", f"{design_data['stitch_count']:,}")
                st.metric("Design Width", f"{design_data['width_mm']:.1f}mm")
                st.metric("Design Height", f"{design_data['height_mm']:.1f}mm")
                
                # Thread weight selection
                thread_weight = st.selectbox("Thread Weight", [40, 60])
                
                # Foam options
                use_foam = st.checkbox("Use 3D Foam")
                if use_foam:
                    foam_color = st.color_picker("Foam Color", "#FF0000")
                
                quantity = st.number_input("Quantity", min_value=1, value=1)
                
            with col2:
                st.subheader("Design Preview")
                fig = analyzer.generate_preview(
                    show_foam=use_foam,
                    foam_color=foam_color if use_foam else None
                )
                st.pyplot(fig)
            
            # Calculate costs
            thread_costs = calculator.calculate_thread_cost(
                design_data['thread_length_yards'],
                quantity,
                heads
            )
            
            runtime = calculator.calculate_runtime(
                design_data['stitch_count'],
                thread_weight
            )
            
            # Display cost breakdown
            st.subheader("Cost Breakdown")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Thread Cost", f"${thread_costs['thread_cost']:.2f}")
            with col2:
                st.metric("Bobbin Cost", f"${thread_costs['bobbin_cost']:.2f}")
            with col3:
                st.metric("Estimated Runtime", f"{runtime:.1f} min")
            
            if use_foam:
                foam_costs = calculator.calculate_foam_cost(
                    design_data['width_mm'],
                    design_data['height_mm'],
                    quantity
                )
                st.metric("Foam Cost", f"${foam_costs['total_cost']:.2f}")
            
            # Export PDF
            if st.button("Export PDF Report"):
                report_data = {
                    **design_data,
                    **thread_costs,
                    "runtime": runtime,
                    "foam_used": use_foam,
                    "quantity": quantity,
                    "thread_weight": thread_weight
                }
                
                if use_foam:
                    report_data.update(foam_costs)
                    
                pdf_bytes = pdf_gen.generate_report(report_data)
                st.download_button(
                    "Download Report",
                    pdf_bytes,
                    "embroidery_cost_report.pdf",
                    "application/pdf"
                )
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()
