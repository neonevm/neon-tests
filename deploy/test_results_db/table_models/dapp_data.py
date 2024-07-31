from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from deploy.test_results_db.table_models.base import Base


class DappData(Base):
    __tablename__ = 'dapp_data'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    cost_report_id: int = Column(Integer, ForeignKey('cost_report.id'), nullable=False)
    dapp_name: str = Column(String(255), nullable=False)
    action: str = Column(String(255), nullable=False)
    fee_in_eth = Column(Numeric(20, 8), nullable=False)
    acc_count: int = Column(Integer, nullable=False)
    trx_count: int = Column(Integer, nullable=False)
    gas_estimated: int = Column(Integer, nullable=False)
    gas_used: int = Column(Integer, nullable=False)

    report = relationship('CostReport', back_populates='dapp_data')

    def __repr__(self):
        return (f"<DappData(id={self.id}, dapp_name={self.dapp_name}, action={self.action}, "
                f"fee_in_eth={self.fee_in_eth}, acc_count={self.acc_count}, "
                f"trx_count={self.trx_count}, gas_estimated={self.gas_estimated}, gas_used={self.gas_used})>")
