from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from datetime import datetime

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Design Information
    design_name = Column(String)
    stitch_count = Column(Integer)
    thread_length_yards = Column(Float)
    width_mm = Column(Float)
    height_mm = Column(Float)
    thread_weight = Column(Integer)
    color_changes = Column(Integer)
    thread_colors = Column(JSON)  # Store color hex values

    # Machine Configuration
    quantity = Column(Integer)
    active_heads = Column(Integer, default=15)
    use_foam = Column(Boolean, default=False)
    use_coloreel = Column(Boolean, default=False)

    # Complexity Metrics
    complexity_score = Column(Float)
    direction_changes = Column(Integer)
    density_score = Column(Float)
    stitch_length_variance = Column(Float)

    # Production Information
    total_runtime = Column(Float)  # minutes
    stitch_time = Column(Float)    # minutes
    pieces_per_cycle = Column(Integer)
    total_cycles = Column(Integer)

    # Relationships
    materials = relationship("MaterialUsage", back_populates="job")
    costs = relationship("CostBreakdown", back_populates="job")

class MaterialUsage(Base):
    __tablename__ = "material_usage"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    material_type = Column(String)  # "thread", "bobbin", "foam"
    quantity = Column(Float)
    unit = Column(String)  # "yards", "pieces", "sheets"
    unit_cost = Column(Float)  # Cost per unit

    job = relationship("Job", back_populates="materials")

class CostBreakdown(Base):
    __tablename__ = "cost_breakdown"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    cost_type = Column(String)  # "thread", "bobbin", "foam", "total"
    amount = Column(Float)
    details = Column(JSON)  # Additional cost details (e.g., breakdown by color)

    job = relationship("Job", back_populates="costs")

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)