from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.database import Base


class HerbCompound(Base):
    __tablename__ = "herb_compounds"
    __table_args__ = (
        Index("ix_herb_compounds_herb_compound", "herb_id", "compound_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    herb_id: Mapped[int] = mapped_column(
        ForeignKey("herbs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    compound_name: Mapped[str] = mapped_column(String(255), nullable=False)
    chemical_formula: Mapped[str | None] = mapped_column(String(100), nullable=True)
    medicinal_use: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_study: Mapped[str | None] = mapped_column(Text, nullable=True)

    herb: Mapped["Herb"] = relationship(back_populates="compounds")

    def __repr__(self) -> str:
        return f"<HerbCompound id={self.id} compound_name={self.compound_name!r}>"
