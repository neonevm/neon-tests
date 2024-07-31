import os
import re
import signal
import typing as tp

from sqlalchemy import create_engine, Engine, asc, distinct
from sqlalchemy.orm import sessionmaker
import pandas as pd
from packaging import version

from deploy.test_results_db.table_models.base import Base
from deploy.test_results_db.table_models.cost_report import CostReport
from deploy.test_results_db.table_models.dapp_data import DappData
from utils.types import RepoType
from utils.version import remove_heading_chars_till_first_digit


class PostgresTestResultsHandler:
    def __init__(self):
        self.engine: Engine = self.__create_engine()
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.__create_tables_if_needed()
        signal.signal(signal.SIGTERM, self.__handle_exit)
        signal.signal(signal.SIGINT, self.__handle_exit)

    @staticmethod
    def __create_engine() -> Engine:
        db_host = os.environ["TEST_RESULTS_DB_HOST"]
        db_port = os.environ["TEST_RESULTS_DB_PORT"]
        db_name = os.environ["TEST_RESULTS_DB_NAME"]
        db_user = os.environ["TEST_RESULTS_DB_USER"]
        db_password = os.environ["TEST_RESULTS_DB_PASSWORD"]
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(db_url)
        return engine

    def __create_tables_if_needed(self):
        Base.metadata.create_all(self.engine)

    def __handle_exit(self, signum, frame):
        self.Session.close_all()

    def get_cost_report_ids_by_branch(self, branch: str) -> tp.List[int]:
        cost_reports = self.session.query(CostReport).filter(CostReport.branch == branch).all()
        return [cost_report.id for cost_report in cost_reports] if cost_reports else []

    def delete_reports(self, repo: str, branch: str, tag: tp.Optional[str]) -> list[int]:
        reports = self.session.query(CostReport).filter(
            CostReport.repo == repo,
            CostReport.branch == branch,
            CostReport.github_tag == tag,
        )
        reports.delete(synchronize_session=False)
        self.session.commit()
        report_ids = [r.id for r in reports]
        return report_ids

    def delete_data_by_report_ids(self, report_ids: tp.List[int]):
        self.session.query(DappData).filter(DappData.cost_report_id.in_(report_ids)).delete(synchronize_session=False)
        self.session.commit()

    def save_cost_report(
        self,
        branch: str,
        repo: RepoType,
        token_usd_gas_price: float,
        github_tag: tp.Optional[str],
        docker_image_tag: tp.Optional[str],
    ) -> int:
        cost_report = CostReport(
            repo=repo,
            branch=branch,
            github_tag=github_tag,
            docker_image_tag=docker_image_tag,
            token_usd_gas_price=token_usd_gas_price,
        )
        self.session.add(cost_report)
        self.session.commit()
        return cost_report.id

    def save_cost_report_data(self, report_data: pd.DataFrame, cost_report_id: int):
        dapp_groups = report_data.groupby("dapp_name")

        for dapp_name, group in dapp_groups:
            for _, row in group.iterrows():
                cost_report_data = DappData(
                    cost_report_id=cost_report_id,
                    dapp_name=str(dapp_name),
                    action=row["action"],
                    fee_in_eth=row["fee_in_eth"],
                    acc_count=row["acc_count"],
                    trx_count=row["trx_count"],
                    gas_estimated=row["gas_estimated"],
                    gas_used=row["gas_used"],
                )
                self.session.add(cost_report_data)

        self.session.commit()

    def get_previous_tag(self, repo: str, branch: str, tag: str) -> str:
        tags: list[str] = (
            self.session.query(distinct(CostReport.github_tag))
            .filter(
                CostReport.repo == repo,
                CostReport.branch == branch,
            )
            .all()
        )

        sorted_tags = sorted(
            [t[0] for t in tags if t[0] is not None],
            key=lambda t: version.parse(remove_heading_chars_till_first_digit(t)),
            reverse=True,
        )

        latest_tag = version.parse(remove_heading_chars_till_first_digit(tag))
        previous_tag = version.parse("0")

        for tag_ in sorted_tags:
            next_tag = version.parse(remove_heading_chars_till_first_digit(tag_))
            if previous_tag < next_tag < latest_tag:
                previous_tag = tag_
                break

        return previous_tag

    def get_historical_data(
        self,
        depth: int,
        repo: RepoType,
        last_branch: str,
        previous_branch: str,
        tag: tp.Optional[str],
    ) -> pd.DataFrame:
        # Define the previous tag
        from clickfile import VERSION_BRANCH_TEMPLATE
        if tag is not None:
            if re.fullmatch(VERSION_BRANCH_TEMPLATE, previous_branch):
                tag_ = previous_branch.replace("x", "99999999")
            else:
                tag_ = tag

        previous_tag = tag if tag is None else self.get_previous_tag(repo=repo, branch=previous_branch, tag=tag_)

        # Fetch previous CostReport entries
        offset = 0 if previous_branch != last_branch or previous_tag else 1
        previous_reports: list[CostReport] = (
            self.session.query(CostReport)
            .filter(
                CostReport.repo == repo,
                CostReport.branch == previous_branch,
                CostReport.github_tag == previous_tag,
            )
            .order_by(asc(CostReport.timestamp))
            .offset(offset)
            .limit(depth - 1)
            .all()
        )

        # Fetch last CostReport
        last_report: CostReport = (
            self.session.query(CostReport)
            .filter(
                CostReport.repo == repo,
                CostReport.branch == last_branch,
                CostReport.github_tag == tag,
            )
            .order_by(asc(CostReport.timestamp))
            .first()
        )

        cost_report_entries: list[CostReport] = [last_report] + previous_reports
        cost_report_ids: list[int] = [r.id for r in previous_reports] + [last_report.id]

        # Fetch DappData entries for these cost_report_ids
        actions_tuples = (
            self.session.query(distinct(DappData.action)).filter(DappData.cost_report_id == last_report.id).all()
        )
        actions = [action_tuple[0] for action_tuple in actions_tuples]
        dapp_data_entries = (
            self.session.query(DappData)
            .filter(
                DappData.cost_report_id.in_(cost_report_ids),
                DappData.action.in_(actions),
            )
            .all()
        )

        # Convert the list of CostReport objects to a dictionary for quick lookup
        cost_report_dict: dict[int, CostReport] = {r.id: r for r in cost_report_entries}

        df_data = []
        for data_entry in dapp_data_entries:
            cost_report: tp.Optional[CostReport] = cost_report_dict.get(data_entry.cost_report_id)
            if cost_report:
                df_data.append(
                    {
                        "timestamp": cost_report.timestamp,
                        "branch": cost_report.branch,
                        "tag": cost_report.github_tag,
                        "token_usd_gas_price": cost_report.token_usd_gas_price,
                        "dapp_name": data_entry.dapp_name,  # Directly use dapp_name from DappData
                        "action": data_entry.action,
                        "fee_in_eth": data_entry.fee_in_eth,
                        "acc_count": data_entry.acc_count,
                        "trx_count": data_entry.trx_count,
                        "gas_estimated": data_entry.gas_estimated,
                        "gas_used": data_entry.gas_used,
                    }
                )

        # Initialize the DataFrame and sort it
        df = pd.DataFrame(data=df_data)
        df = df.sort_values(by=["timestamp", "dapp_name", "action"])

        return df
