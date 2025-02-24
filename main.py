import streamlit as st
import io
import logging
from utils.design_analyzer import DesignAnalyzer
from utils.cost_calculator import CostCalculator
from utils.pdf_generator import PDFGenerator
from utils.database import init_db, get_db, Job, MaterialUsage, CostBreakdown
from sqlalchemy.orm import Session
import json
from typing import Generator
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Embroidery Cost Calculator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization error: {str(e)}")
    st.error("Error connecting to database. Please try again later.")

# Load custom CSS
try:
    with open("styles/custom.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception as e:
    logger.error(f"Error loading CSS: {str(e)}")

def save_job_to_db(
    db: Session,
    design_data: dict,
    thread_costs: dict,
    foam_costs: dict = None,
    use_foam: bool = False,
    use_coloreel: bool = False,
    quantity: int = 1,
    thread_weight: int = 40
) -> Job:
    """Save job details to database"""
    try:
        # Create job record
        job = Job(
            design_name=design_data.get('design_name', 'Untitled'),
            stitch_count=design_data['stitch_count'],
            thread_length_yards=design_data['thread_length_yards'],
            width_mm=design_data['width_mm'],
            height_mm=design_data['height_mm'],
            quantity=quantity,
            thread_weight=thread_weight,
            use_foam=use_foam,
            use_coloreel=use_coloreel
        )
        db.add(job)
        db.flush()

        # Add material usage
        materials = [
            MaterialUsage(
                job_id=job.id,
                material_type='thread',
                quantity=thread_costs['total_spools'],
                unit='spools'
            ),
            MaterialUsage(
                job_id=job.id,
                material_type='bobbin',
                quantity=thread_costs['total_bobbins'],
                unit='pieces'
            )
        ]

        if use_foam and foam_costs:
            materials.append(
                MaterialUsage(
                    job_id=job.id,
                    material_type='foam',
                    quantity=foam_costs['sheets_needed'],
                    unit='sheets'
                )
            )

        db.bulk_save_objects(materials)

        # Add cost breakdown
        costs = [
            CostBreakdown(
                job_id=job.id,
                cost_type='thread',
                amount=thread_costs['thread_cost']
            ),
            CostBreakdown(
                job_id=job.id,
                cost_type='bobbin',
                amount=thread_costs['bobbin_cost']
            )
        ]

        if use_foam and foam_costs:
            costs.append(
                CostBreakdown(
                    job_id=job.id,
                    cost_type='foam',
                    amount=foam_costs['total_cost']
                )
            )

        db.bulk_save_objects(costs)
        db.commit()
        logger.info(f"Successfully saved job {job.id} to database")
        return job
    except Exception as e:
        logger.error(f"Error saving job to database: {str(e)}")
        db.rollback()
        raise

def main():
    st.title("Embroidery Cost Calculator")

    try:
        # Initialize components
        analyzer = DesignAnalyzer()
        calculator = CostCalculator()
        pdf_gen = PDFGenerator()

        # Database session
        db = next(get_db())

        # Add tabs for new calculation and history
        tab1, tab2 = st.tabs(["New Calculation", "History"])

        with tab1:
            # Machine configuration
            st.sidebar.subheader("Machine Configuration")
            use_coloreel = st.sidebar.checkbox("Use Coloreel ITCU")
            heads = 2 if use_coloreel else 15

            # File upload
            st.info("Please upload a DST or U01 file to analyze")
            uploaded_file = st.file_uploader(
                "Upload DST/U01 File",
                type=["dst", "u01"],
                help="Upload your embroidery design file"
            )

            if uploaded_file is not None:
                try:
                    logger.info(f"Processing uploaded file: {uploaded_file.name}")
                    file_contents = uploaded_file.getvalue()

                    if not file_contents:
                        st.error("The uploaded file is empty")
                        return

                    # Analyze design
                    design_data = analyzer.analyze_file(file_contents)
                    design_data['design_name'] = uploaded_file.name

                    # Display design preview and information in columns
                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("Design Information")

                        # Basic metrics
                        metrics_col1, metrics_col2 = st.columns(2)
                        with metrics_col1:
                            st.metric("Stitch Count", f"{design_data['stitch_count']:,}")
                            st.metric("Design Width", f"{design_data['width_mm']:.1f}mm")
                        with metrics_col2:
                            st.metric("Color Changes", str(design_data['color_changes']))
                            st.metric("Design Height", f"{design_data['height_mm']:.1f}mm")

                        # Complexity Analysis
                        st.subheader("Complexity Analysis")
                        complexity_score = design_data['complexity_score']
                        st.progress(complexity_score / 100)
                        st.write(f"Complexity Score: {complexity_score}/100")
                        st.info(analyzer.get_complexity_description(complexity_score))

                        # Detailed metrics
                        with st.expander("Detailed Complexity Metrics"):
                            st.metric("Direction Changes", design_data['direction_changes'])
                            st.metric("Density Score", f"{design_data['density_score']:.1f}/10")
                            st.metric("Stitch Length Variance", 
                                    f"{design_data['stitch_length_variance']:.1f}/10")

                        # Thread weight selection
                        thread_weight = st.selectbox("Thread Weight", [40, 60])

                        # Foam options
                        use_foam = st.checkbox("Use 3D Foam")
                        foam_color = None
                        if use_foam:
                            foam_color = st.color_picker("Foam Color", "#FF0000")

                        quantity = st.number_input("Quantity", min_value=1, value=1)

                    with col2:
                        st.subheader("Design Preview")
                        fig = analyzer.generate_preview(
                            show_foam=use_foam,
                            foam_color=foam_color if use_foam else "#FF0000"
                        )
                        st.pyplot(fig)

                    # Calculate costs with complexity adjustment
                    complexity_factor = 1 + (complexity_score / 200)  # Max 50% increase for complex designs
                    thread_costs = calculator.calculate_thread_cost(
                        design_data['thread_length_yards'],
                        quantity,
                        heads
                    )

                    runtime = calculator.calculate_runtime(
                        design_data['stitch_count'],
                        thread_weight
                    ) * complexity_factor  # Adjust runtime based on complexity

                    # Display cost breakdown
                    st.subheader("Cost Breakdown")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Thread Cost", f"${thread_costs['thread_cost']:.2f}")
                    with col2:
                        st.metric("Bobbin Cost", f"${thread_costs['bobbin_cost']:.2f}")
                    with col3:
                        st.metric("Estimated Runtime", f"{runtime:.1f} min")
                        st.caption("Includes complexity adjustment")

                    foam_costs = None
                    if use_foam:
                        foam_costs = calculator.calculate_foam_cost(
                            design_data['width_mm'],
                            design_data['height_mm'],
                            quantity
                        )
                        st.metric("Foam Cost", f"${foam_costs['total_cost']:.2f}")

                    # Save calculation
                    if st.button("Save Calculation"):
                        job = save_job_to_db(
                            db,
                            design_data,
                            thread_costs,
                            foam_costs,
                            use_foam,
                            use_coloreel,
                            quantity,
                            thread_weight
                        )
                        st.success("Calculation saved!")

                    # Export PDF
                    if st.button("Export PDF Report"):
                        report_data = {
                            **design_data,
                            **thread_costs,
                            "runtime": runtime,
                            "foam_used": use_foam,
                            "quantity": quantity,
                            "thread_weight": thread_weight,
                            "complexity_factor": complexity_factor
                        }

                        if use_foam and foam_costs:
                            report_data.update(foam_costs)

                        pdf_bytes = pdf_gen.generate_report(report_data)
                        st.download_button(
                            "Download Report",
                            pdf_bytes,
                            "embroidery_cost_report.pdf",
                            "application/pdf"
                        )

                except Exception as e:
                    logger.error(f"Error processing file: {str(e)}")
                    st.error(f"Error processing file: {str(e)}")

        with tab2:
            st.subheader("Calculation History")
            try:
                # Query recent jobs
                recent_jobs = db.query(Job).order_by(Job.created_at.desc()).limit(10).all()

                if not recent_jobs:
                    st.info("No calculations saved yet")
                    return

                for job in recent_jobs:
                    with st.expander(f"{job.design_name} - {job.created_at.strftime('%Y-%m-%d %H:%M')}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Stitch Count", f"{job.stitch_count:,}")
                            st.metric("Quantity", str(job.quantity))
                            st.metric("Thread Weight", f"{job.thread_weight}wt")
                        with col2:
                            costs = {c.cost_type: c.amount for c in job.costs}
                            st.metric("Thread Cost", f"${costs.get('thread', 0):.2f}")
                            st.metric("Bobbin Cost", f"${costs.get('bobbin', 0):.2f}")
                            if job.use_foam:
                                st.metric("Foam Cost", f"${costs.get('foam', 0):.2f}")
            except Exception as e:
                logger.error(f"Error loading history: {str(e)}")
                st.error("Error loading calculation history")

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error("An unexpected error occurred. Please try again later.")

if __name__ == "__main__":
    main()