"""SQLite persistence via SQLAlchemy."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from src.models import ProductAnalysis


class Base(DeclarativeBase):
    pass


class AnalysisRow(Base):
    __tablename__ = "product_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    analysis_json: Mapped[str] = mapped_column(Text())
    notion_page_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def get_engine(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path.as_posix()}", echo=False)


def get_session_factory(db_path: Path):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def save_analysis(sf, analysis: ProductAnalysis, notion_page_id: str | None = None) -> None:
    payload = analysis.model_dump_json()
    url = analysis.product.source_url
    with sf() as s:
        row = s.scalars(select(AnalysisRow).where(AnalysisRow.source_url == url)).first()
        now = datetime.now(timezone.utc)
        if row is None:
            row = AnalysisRow(
                source_url=url,
                analysis_json=payload,
                notion_page_id=notion_page_id,
                created_at=now,
            )
            s.add(row)
        else:
            row.analysis_json = payload
            if notion_page_id:
                row.notion_page_id = notion_page_id
        s.commit()


def source_urls_with_notion(sf) -> set[str]:
    with sf() as s:
        rows = s.scalars(select(AnalysisRow).where(AnalysisRow.notion_page_id.isnot(None))).all()
        return {r.source_url for r in rows}