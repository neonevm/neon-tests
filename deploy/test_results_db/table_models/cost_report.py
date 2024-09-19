from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from deploy.test_results_db.table_models.base import Base
from utils.types import RepoType


class CostReport(Base):
    __tablename__ = "cost_report"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    timestamp: datetime.utcnow = Column(DateTime, default=datetime.utcnow, nullable=False)
    repo: RepoType = Column(String(255), nullable=False)
    neon_evm_tag: str = Column(String(255), nullable=False)
    proxy_tag: str = Column(String(255), nullable=False)
    evm_commit_sha: str = Column(String(255), nullable=True)
    proxy_commit_sha: str = Column(String(255), nullable=False)

    dapp_data = relationship("DappData", back_populates="report", cascade="all, delete-orphan")

    def __repr__(self):
        formatted_timestamp = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"<CostReport(id={self.id}, timestamp={formatted_timestamp}, repo={self.repo}"
            f"neon_evm_tag={self.neon_evm_tag}, proxy_tag={self.proxy_tag}, "
            f"evm_commit_sha={self.evm_commit_sha}), proxy_commit_sha={self.proxy_commit_sha})>"
        )
