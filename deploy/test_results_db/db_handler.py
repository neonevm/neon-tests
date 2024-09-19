import os
import re
import signal
import typing as tp

import click
from sqlalchemy import create_engine, Engine, distinct, desc
from sqlalchemy.orm import sessionmaker, Query
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

    def get_cost_report_ids(self, repo: str, tag: str) -> list[int]:
        tag_column = CostReport.neon_evm_tag if repo == "evm" else CostReport.proxy_tag
        report_ids = self.session.query(CostReport.id).filter(
            CostReport.repo == repo,
            tag_column == tag,
        ).all()
        report_ids = [id_[0] for id_ in report_ids]
        return report_ids

    def delete_data_by_report_ids(self, report_ids: tp.List[int]):
        click.echo(f"delete_data_by_report_ids: {report_ids}")
        self.session.query(DappData).filter(DappData.cost_report_id.in_(report_ids)).delete(synchronize_session=False)
        self.session.commit()

    def delete_reports(self, report_ids: tp.List[int]):
        click.echo(f"delete_reports: {report_ids}")
        self.session.query(CostReport).filter(CostReport.id.in_(report_ids)).delete(synchronize_session=False)
        self.session.commit()

    def save_cost_report(
        self,
        repo: RepoType,
        neon_evm_tag: str,
        proxy_tag: str,
        evm_commit_sha: tp.Optional[str],
        proxy_commit_sha: str,
    ) -> int:
        click.echo(f"save_cost_report: {locals()}")
        cost_report = CostReport(
            repo=repo,
            neon_evm_tag=neon_evm_tag,
            proxy_tag=proxy_tag,
            evm_commit_sha=evm_commit_sha or None,
            proxy_commit_sha=proxy_commit_sha,
        )
        self.session.add(cost_report)
        self.session.commit()
        return cost_report.id

    def save_cost_report_data(self, report_data: pd.DataFrame, cost_report_id: int):
        click.echo(f"save_cost_report_data for cost_report_id: {cost_report_id}")
        dapp_groups = report_data.groupby("dapp_name")

        for dapp_name, group in dapp_groups:
            for _, row in group.iterrows():
                cost_report_data = DappData(
                    cost_report_id=cost_report_id,
                    dapp_name=str(dapp_name),
                    action=row["action"],
                    acc_count=row["acc_count"],
                    trx_count=row["trx_count"],
                    gas_estimated=row["gas_estimated"],
                    gas_used=row["gas_used"],
                    compute_units=row["compute_units"],
                )
                self.session.add(cost_report_data)

        self.session.commit()

    def get_previous_tags(self, repo: RepoType, tag: str, limit: int) -> list[str]:
        """

        :param repo:
        :param tag: must match GITHUB_TAG_PATTERN
        :param limit:
        :return:
        """
        from clickfile import GITHUB_TAG_PATTERN

        assert re.fullmatch(GITHUB_TAG_PATTERN, tag)
        tag_column = CostReport.neon_evm_tag if repo == "evm" else CostReport.proxy_tag
        tags: list[str] = (
            self.session.query(distinct(tag_column))
            .filter(
                CostReport.repo == repo,
            )
            .all()
        )
        tags = [tag[0] for tag in tags]
        tags = [tag for tag in tags if GITHUB_TAG_PATTERN.match(tag)]
        sorted_tags: list[str] = sorted(
            [t for t in tags if t is not None],
            key=lambda t: version.parse(remove_heading_chars_till_first_digit(t)),
            reverse=True,
        )
        latest_tag: version.Version = version.parse(remove_heading_chars_till_first_digit(tag))

        # Find the index of the first tag that is less than latest_tag
        for i, tag_ in enumerate(sorted_tags):
            if version.parse(remove_heading_chars_till_first_digit(tag_)) < latest_tag:
                # Return all tags before the found index, limited by the specified limit
                previous_tags: list[str] = sorted_tags[i:]
                return previous_tags[:limit]
        else:
            return []

    def get_historical_data(
        self,
        depth: int,
        repo: RepoType,
        latest_tag: str,
        previous_tags: list[str],
    ) -> pd.DataFrame:
        """
        :param depth:
        :param repo:
        :param latest_tag:
        :param previous_tags: ["latest] or ["v3.1.x"] or ["v3.1.0", "v3.1.1", ...]
        """

        tag_column = CostReport.neon_evm_tag if repo == "evm" else CostReport.proxy_tag

        # Fetch previous CostReport entries
        previous_reports: Query = (
            self.session.query(CostReport)
            .filter(
                CostReport.repo == repo,
                tag_column.in_(previous_tags),
            )
            .order_by(desc(CostReport.timestamp))
        )

        # offset the previous_reports query by 1 if it's a merge event because latest_tag is the same as previous_tags
        offset = 1 if latest_tag in previous_tags else 0
        previous_reports: list[CostReport] = previous_reports.offset(offset).limit(depth - 1).all()

        # Fetch last CostReport
        last_report: CostReport = (
            self.session.query(CostReport)
            .filter(
                CostReport.repo == repo,
                tag_column == latest_tag,
            )
            .order_by(desc(CostReport.timestamp))
            .first()
        )

        cost_report_entries: list[CostReport] = [last_report] + previous_reports
        cost_report_ids: list[int] = [r.id for r in previous_reports] + [last_report.id]

        # Define the dapps that are present in the last_report
        dapp_name_tuples = (
            self.session.query(distinct(DappData.dapp_name)).filter(DappData.cost_report_id == last_report.id).all()
        )
        dapp_names = [dapp_name_tuple[0] for dapp_name_tuple in dapp_name_tuples]

        # Define the actions that are present in the last_report
        actions_tuples = (
            self.session.query(distinct(DappData.action)).filter(DappData.cost_report_id == last_report.id).all()
        )
        actions = [action_tuple[0] for action_tuple in actions_tuples]

        # Fetch DappData entries for cost_report_ids but only for dapps and actions present in last_report
        dapp_data_entries: list[tp.Type[DappData]] = (
            self.session.query(DappData)
            .filter(
                DappData.cost_report_id.in_(cost_report_ids),
                DappData.dapp_name.in_(dapp_names),
                DappData.action.in_(actions),
            )
            .all()
        )

        # Convert the list of CostReport objects to a dictionary for quick lookup
        cost_report_dict: dict[int, CostReport] = {r.id: r for r in cost_report_entries}

        # prepare data for the DataFrame
        df_data = []
        for data_entry in dapp_data_entries:
            cost_report: tp.Optional[CostReport] = cost_report_dict.get(data_entry.cost_report_id)
            if cost_report:
                tag = cost_report.neon_evm_tag if repo == "evm" else cost_report.proxy_tag
                df_data.append(
                    {
                        "repo": cost_report.repo,
                        "timestamp": cost_report.timestamp,
                        "neon_evm_tag": cost_report.neon_evm_tag,
                        "proxy_tag": cost_report.proxy_tag,
                        "tag": tag,
                        "dapp_name": data_entry.dapp_name,
                        "action": data_entry.action,
                        "acc_count": data_entry.acc_count,
                        "trx_count": data_entry.trx_count,
                        "gas_estimated": data_entry.gas_estimated,
                        "gas_used": data_entry.gas_used,
                        "evm_commit_sha": cost_report.evm_commit_sha,
                        "proxy_commit_sha": cost_report.proxy_commit_sha,
                        "compute_units": data_entry.compute_units,
                    }
                )

        # Initialize the DataFrame and sort it
        df = pd.DataFrame(data=df_data)
        if not df.empty:
            df = df.sort_values(by=["timestamp", "dapp_name", "action"])

        return df
