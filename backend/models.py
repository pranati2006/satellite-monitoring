from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship

from database import Base


class Satellite(Base):
    __tablename__ = "satellites"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    norad_id = Column(Integer, unique=True, nullable=False)
    name = Column(String(255), nullable=False)

    tle_line1 = Column(Text, nullable=False)
    tle_line2 = Column(Text, nullable=False)

    epoch = Column(DateTime)

    inclination = Column(Float)
    eccentricity = Column(Float)
    raan = Column(Float)
    arg_perigee = Column(Float)
    mean_anomaly = Column(Float)
    mean_motion = Column(Float)

    data_source = Column(String(100), default="CelesTrak")

    is_active = Column(Boolean, default=True, nullable=False)

    fetched_at = Column(DateTime)
    updated_at = Column(DateTime)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)

    prediction_start = Column(DateTime, nullable=False)
    prediction_end = Column(DateTime, nullable=False)

    screening_interval_seconds = Column(
        Integer,
        nullable=False,
        default=600
    )

    total_satellites = Column(Integer)
    conjunction_count = Column(Integer, default=0)

    status = Column(
        String(30),
        nullable=False,
        default="RUNNING"
    )

    error_message = Column(Text)


class AnalysisSatellite(Base):
    __tablename__ = "analysis_satellites"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    analysis_id = Column(
        BigInteger,
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False
    )

    satellite_id = Column(
        BigInteger,
        ForeignKey("satellites.id", ondelete="CASCADE"),
        nullable=False
    )

    included = Column(Boolean, default=True, nullable=False)


class Conjunction(Base):
    __tablename__ = "conjunctions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    analysis_id = Column(
        BigInteger,
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False
    )

    satellite_1_id = Column(
        BigInteger,
        ForeignKey("satellites.id", ondelete="CASCADE"),
        nullable=False
    )

    satellite_2_id = Column(
        BigInteger,
        ForeignKey("satellites.id", ondelete="CASCADE"),
        nullable=False
    )

    coarse_tca = Column(DateTime, nullable=False)

    minimum_coarse_distance_km = Column(Float, nullable=False)

    conjunction_threshold_km = Column(Float, nullable=False)

    selected_for_detailed = Column(
        Boolean,
        default=False,
        nullable=False
    )

    status = Column(
        String(30),
        default="POSSIBLE",
        nullable=False
    )


class DetailedConjunction(Base):
    __tablename__ = "detailed_conjunctions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    conjunction_id = Column(
        BigInteger,
        ForeignKey("conjunctions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    analysis_start = Column(DateTime, nullable=False)
    analysis_end = Column(DateTime, nullable=False)

    tca = Column(DateTime, nullable=False)

    minimum_distance_km = Column(Float, nullable=False)

    relative_velocity_km_s = Column(Float)

    risk_level = Column(String(30))

    calculated_at = Column(DateTime)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    setting_name = Column(
        String(100),
        unique=True,
        nullable=False
    )

    setting_value = Column(
        String(255),
        nullable=False
    )

    description = Column(Text)