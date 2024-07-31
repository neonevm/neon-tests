from datetime import datetime
import typing as tp

from sqlalchemy import Column, Integer, Numeric, String, DateTime
from sqlalchemy.orm import relationship

from deploy.test_results_db.table_models.base import Base
from utils.types import RepoType


class CostReport(Base):
    __tablename__ = "cost_report"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    timestamp: datetime.utcnow = Column(DateTime, default=datetime.utcnow, nullable=False)
    repo: RepoType = Column(String(255), nullable=False)
    branch: str = Column(String(255), nullable=True)
    github_tag: tp.Optional[str] = Column(String(255), nullable=True)
    docker_image_tag: tp.Optional[str] = Column(String(255), nullable=True)
    token_usd_gas_price: float = Column(Numeric(20, 8), nullable=False)

    dapp_data = relationship("DappData", back_populates="report", cascade="all, delete-orphan")

    def __repr__(self):
        formatted_timestamp = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"<CostReport(id={self.id}, repo={self.repo}, branch={self.branch}, "
            f"github_tag={self.github_tag}, token_usd_gas_price={self.token_usd_gas_price}, "
            f"timestamp={formatted_timestamp})>"
        )
