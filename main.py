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
    thread_weight: int = 40,
    active_heads: int = 15
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
            use_coloreel=use_coloreel,
            active_heads=active_heads
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
            # Machine Configuration Section
            st.subheader("Machine Configuration")
            config_col1, config_col2, config_col3 = st.columns(3)

            with config_col1:
                active_heads = st.number_input(
                    "Active Heads",
                    min_value=1,
                    max_value=15,
                    value=15,
                    help="Number of active embroidery heads (1-15)"
                )
                st.caption("More active heads = faster production")

            with config_col2:
                use_coloreel = st.checkbox(
                    "Use Coloreel ITCU",
                    help="Enable Coloreel Instant Thread Coloring Units"
                )
                if use_coloreel:
                    st.warning("⚠️ Coloreel mode limits maximum heads to 2")
                    active_heads = min(active_heads, 2)

            with config_col3:
                st.write("Machine Status")
                st.metric(
                    "Production Capacity",
                    f"{active_heads} heads",
                    delta="Limited to 2" if use_coloreel else None,
                    delta_color="off" if use_coloreel else "normal"
                )

            st.divider()

            # File upload
            st.subheader("Design Upload")
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

                    # Color selection
                    st.subheader("Thread Colors")
                    num_colors = st.number_input("Number of Colors", 1, 15, 1,
                                                  help="Specify how many different thread colors are used")
                    thread_colors = []
                    if num_colors > 0:
                        color_cols = st.columns(min(4, num_colors))
                        for i in range(num_colors):
                            with color_cols[i % 4]:
                                color = st.color_picker(f"Color {i+1}", "#000000")
                                thread_colors.append(color)

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
                            st.metric("Thread Length", f"{design_data['thread_length_yards']:.1f} yards")
                            st.metric("Design Height", f"{design_data['height_mm']:.1f}mm")

                        # Complexity Analysis
                        st.subheader("Complexity Analysis")
                        complexity_score = design_data['complexity_score']
                        st.progress(complexity_score / 100)
                        st.write(f"Complexity Score: {complexity_score}/100")
                        st.info(analyzer.get_complexity_description(complexity_score))

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
                            foam_color=foam_color if use_foam else "#FF0000",
                            num_colors=num_colors,
                            thread_colors=thread_colors
                        )
                        st.pyplot(fig)

                    # Production Information Section
                    st.subheader("Production Information")
                    prod_col1, prod_col2, prod_col3 = st.columns(3)

                    runtime_data = calculator.calculate_runtime(
                        design_data['stitch_count'],
                        thread_weight,
                        quantity,
                        active_heads
                    )

                    with prod_col1:
                        st.metric("Total Cycles", str(runtime_data['cycles']))
                        st.metric("Pieces per Cycle", str(runtime_data['pieces_per_cycle']))
                        if runtime_data['last_cycle_pieces'] != runtime_data['pieces_per_cycle']:
                            st.caption(f"Last cycle: {runtime_data['last_cycle_pieces']} pieces")

                    with prod_col2:
                        st.metric("Stitch Time", f"{runtime_data['stitch_time']:.1f} min")
                        st.metric("Hooping Time/Cycle", f"{runtime_data['hooping_time_per_cycle']:.1f} min")
                        st.caption("Operations run concurrently")

                    with prod_col3:
                        st.metric("Cycle Time", f"{runtime_data['cycle_time']:.1f} min")
                        st.metric("Total Runtime", f"{runtime_data['total_runtime']:.1f} min")
                        st.caption(f"Includes {runtime_data['buffer_time']:.1f} min buffer between cycles")

                    # Cost Breakdown
                    st.subheader("Cost Breakdown")
                    thread_costs = calculator.calculate_thread_cost(
                        design_data['thread_length_yards'],
                        quantity,
                        active_heads,
                        num_colors
                    )

                    cost_col1, cost_col2, cost_col3 = st.columns(3)
                    with cost_col1:
                        st.metric("Thread Cost", f"${thread_costs['thread_cost']:.2f}")
                        st.caption(f"{thread_costs['spools_per_head']} spools per head")
                        st.caption(f"{thread_costs['colors_per_head']} colors per head")
                        st.caption(f"Total: {thread_costs['total_spools']} spools")
                    with cost_col2:
                        st.metric("Bobbin Cost", f"${thread_costs['bobbin_cost']:.2f}")
                        st.caption(f"Using {thread_costs['total_bobbins']} bobbins")
                    with cost_col3:
                        total_cost = thread_costs['thread_cost'] + thread_costs['bobbin_cost']

                        foam_costs = None
                        if use_foam:
                            foam_costs = calculator.calculate_foam_cost(
                                design_data['width_mm'],
                                design_data['height_mm'],
                                quantity
                            )
                            total_cost += foam_costs['total_cost']
                            st.metric("Foam Cost", f"${foam_costs['total_cost']:.2f}")
                            st.caption(f"Using {foam_costs['sheets_needed']} sheets")
                        st.metric("Total Cost", f"${total_cost:.2f}")

                    # Export options in a clean container
                    st.container()
                    export_col1, export_col2 = st.columns(2)

                    with export_col1:
                        if st.button("💾 Save Calculation", use_container_width=True):
                            try:
                                job = save_job_to_db(
                                    db,
                                    design_data,
                                    thread_costs,
                                    foam_costs,
                                    use_foam,
                                    use_coloreel,
                                    quantity,
                                    thread_weight,
                                    active_heads
                                )
                                st.success("✅ Calculation saved successfully!")
                            except Exception as e:
                                st.error(f"Error saving calculation: {str(e)}")

                    with export_col2:
                        if st.button("📄 Export PDF Report", use_container_width=True):
                            try:
                                report_data = {
                                    **design_data,
                                    **thread_costs,
                                    **runtime_data,
                                    "foam_used": use_foam,
                                    "quantity": quantity,
                                    "thread_weight": thread_weight,
                                    "active_heads": active_heads
                                }

                                if use_foam and foam_costs:
                                    report_data.update(foam_costs)

                                pdf_bytes = pdf_gen.generate_report(report_data)
                                st.download_button(
                                    "📥 Download Report",
                                    pdf_bytes,
                                    f"embroidery_cost_report_{design_data['design_name']}.pdf",
                                    "application/pdf",
                                    use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"Error generating PDF: {str(e)}")

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