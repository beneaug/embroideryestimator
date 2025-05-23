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
    runtime_data: dict,
    thread_colors: list = None,
    foam_costs: dict = None,
    use_foam: bool = False,
    use_coloreel: bool = False,
    quantity: int = 1,
    thread_weight: int = 40,
    active_heads: int = 15
) -> Job:
    """Save job details to database"""
    try:
        # Convert NumPy values to native Python types
        thread_length = float(design_data['thread_length_yards'])
        width = float(design_data['width_mm'])
        height = float(design_data['height_mm'])

        # Create job record
        job = Job(
            # Design Information
            design_name=design_data.get('design_name', 'Untitled'),
            stitch_count=int(design_data['stitch_count']),
            thread_length_yards=thread_length,
            width_mm=width,
            height_mm=height,
            thread_weight=thread_weight,
            color_changes=design_data.get('color_changes', 1),
            thread_colors=thread_colors,

            # Machine Configuration
            quantity=quantity,
            active_heads=active_heads,
            use_foam=use_foam,
            use_coloreel=use_coloreel,

            # Complexity Metrics
            complexity_score=float(design_data.get('complexity_score', 0)) if design_data.get('complexity_score') is not None else None,
            direction_changes=int(design_data.get('direction_changes', 0)) if design_data.get('direction_changes') is not None else None,
            density_score=float(design_data.get('density_score', 0)) if design_data.get('density_score') is not None else None,
            stitch_length_variance=float(design_data.get('stitch_length_variance', 0)) if design_data.get('stitch_length_variance') is not None else None,

            # Production Information
            total_runtime=float(runtime_data['total_runtime']),
            stitch_time=float(runtime_data['stitch_time']),
            pieces_per_cycle=int(runtime_data['pieces_per_cycle']),
            total_cycles=int(runtime_data['cycles'])
        )
        db.add(job)
        db.flush()

        # Add material usage
        materials = [
            MaterialUsage(
                job_id=job.id,
                material_type='thread',
                quantity=thread_costs['total_spools'],
                unit='spools',
                unit_cost=thread_costs['thread_cost'] / thread_costs['total_spools']
            ),
            MaterialUsage(
                job_id=job.id,
                material_type='bobbin',
                quantity=thread_costs['total_bobbins'],
                unit='pieces',
                unit_cost=thread_costs['bobbin_cost'] / thread_costs['total_bobbins']
            )
        ]

        if use_foam and foam_costs:
            materials.append(
                MaterialUsage(
                    job_id=job.id,
                    material_type='foam',
                    quantity=foam_costs['sheets_needed'],
                    unit='sheets',
                    unit_cost=foam_costs['foam_unit_cost']
                )
            )

        db.bulk_save_objects(materials)

        # Add cost breakdown
        total_cost = thread_costs['thread_cost'] + thread_costs['bobbin_cost']
        costs = [
            CostBreakdown(
                job_id=job.id,
                cost_type='thread',
                amount=thread_costs['thread_cost'],
                details={'spools_per_head': thread_costs['spools_per_head']}
            ),
            CostBreakdown(
                job_id=job.id,
                cost_type='bobbin',
                amount=thread_costs['bobbin_cost'],
                details={'bobbins_per_piece': thread_costs['total_bobbins'] / quantity}
            )
        ]

        if use_foam and foam_costs:
            foam_cost = foam_costs['total_cost']
            total_cost += foam_cost
            costs.append(
                CostBreakdown(
                    job_id=job.id,
                    cost_type='foam',
                    amount=foam_cost,
                    details={'sheets_per_piece': foam_costs['sheets_needed'] / quantity}
                )
            )

        # Add total cost record
        costs.append(
            CostBreakdown(
                job_id=job.id,
                cost_type='total',
                amount=total_cost,
                details={
                    'cost_per_piece': total_cost / quantity,
                    'thread_percentage': (thread_costs['thread_cost'] / total_cost) * 100,
                    'bobbin_percentage': (thread_costs['bobbin_cost'] / total_cost) * 100,
                    'foam_percentage': (foam_costs['total_cost'] / total_cost) * 100 if use_foam and foam_costs else 0
                }
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
                        st.caption(f"{thread_costs['spools_per_head']} spools per head ({num_colors} colors)")
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
                                    runtime_data,
                                    thread_colors,
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
                                # Save current plot to bytes
                                plot_buffer = io.BytesIO()
                                fig.savefig(plot_buffer, format='png', dpi=300, bbox_inches='tight')
                                plot_buffer.seek(0)

                                report_data = {
                                    **design_data,
                                    **thread_costs,
                                    **runtime_data,
                                    'design_preview': plot_buffer,
                                    'foam_used': use_foam,
                                    'quantity': quantity,
                                    'thread_weight': thread_weight,
                                    'active_heads': active_heads,
                                    'thread_colors': thread_colors
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
                                logger.error(f"Error generating PDF: {str(e)}")
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
                        # Design Information Section
                        st.subheader("Design Information")
                        info_col1, info_col2 = st.columns(2)

                        with info_col1:
                            st.metric("Stitch Count", f"{job.stitch_count:,}")
                            st.metric("Dimensions", f"{job.width_mm:.1f}mm × {job.height_mm:.1f}mm")
                            st.metric("Thread Weight", f"{job.thread_weight}wt")

                        with info_col2:
                            st.metric("Thread Length", f"{job.thread_length_yards:.1f} yards")
                            st.metric("Color Changes", str(job.color_changes))
                            if job.complexity_score:
                                st.metric("Complexity Score", f"{job.complexity_score:.1f}/100")

                        # Production Information Section
                        st.subheader("Production Details")
                        prod_col1, prod_col2, prod_col3 = st.columns(3)

                        with prod_col1:
                            st.metric("Quantity", str(job.quantity))
                            st.metric("Active Heads", str(job.active_heads))

                        with prod_col2:
                            st.metric("Pieces per Cycle", str(job.pieces_per_cycle))
                            st.metric("Total Cycles", str(job.total_cycles))

                        with prod_col3:
                            st.metric("Stitch Time", f"{job.stitch_time:.1f} min")
                            st.metric("Total Runtime", f"{job.total_runtime:.1f} min")

                        # Cost Breakdown Section
                        st.subheader("Cost Analysis")
                        costs = {c.cost_type: c for c in job.costs}
                        cost_col1, cost_col2, cost_col3 = st.columns(3)

                        with cost_col1:
                            thread_cost = costs.get('thread')
                            if thread_cost:
                                st.metric("Thread Cost", f"${thread_cost.amount:.2f}")
                                if thread_cost.details:
                                    st.caption(f"Spools per head: {thread_cost.details.get('spools_per_head', 'N/A')}")

                        with cost_col2:
                            bobbin_cost = costs.get('bobbin')
                            if bobbin_cost:
                                st.metric("Bobbin Cost", f"${bobbin_cost.amount:.2f}")
                                if bobbin_cost.details:
                                    st.caption(f"Bobbins per piece: {bobbin_cost.details.get('bobbins_per_piece', 'N/A'):.2f}")

                        with cost_col3:
                            if job.use_foam:
                                foam_cost = costs.get('foam')
                                if foam_cost:
                                    st.metric("Foam Cost", f"${foam_cost.amount:.2f}")
                                    if foam_cost.details:
                                        st.caption(f"Sheets per piece: {foam_cost.details.get('sheets_per_piece', 'N/A'):.2f}")

                            total_cost = costs.get('total')
                            if total_cost:
                                st.metric("Total Cost", f"${total_cost.amount:.2f}")
                                if total_cost.details:
                                    st.caption(f"Cost per piece: ${total_cost.details.get('cost_per_piece', 'N/A'):.2f}")

                        # Additional configuration details
                        st.divider()
                        config_col1, config_col2 = st.columns(2)
                        with config_col1:
                            if job.use_foam:
                                st.info("3D Foam: Enabled")
                            if job.use_coloreel:
                                st.info("Coloreel: Enabled")

                        with config_col2:
                            if job.thread_colors:
                                st.write("Thread Colors:")
                                color_cols = st.columns(len(job.thread_colors))
                                for i, color in enumerate(job.thread_colors):
                                    with color_cols[i]:
                                        st.color_picker(f"Color {i+1}", color, disabled=True)

            except Exception as e:
                logger.error(f"Error loading history: {str(e)}")
                st.error("Error loading calculation history")

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error("An unexpected error occurred. Please try again later.")

if __name__ == "__main__":
    main()