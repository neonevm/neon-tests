import textwrap
import time
import typing as tp
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_pdf import PdfPages

from utils.types import RepoType
from deploy.test_results_db.db_handler import PostgresTestResultsHandler


class TestResultsHandler:
    def __init__(self):
        self.db_handler = PostgresTestResultsHandler()

    def save_to_db(
            self,
            report_data: pd.DataFrame,
            repo: RepoType,
            branch: str,
            github_tag: tp.Optional[str],
            docker_image_tag: tp.Optional[str],
            token_usd_gas_price: float,
    ):
        cost_report_id = self.db_handler.save_cost_report(
            repo=repo,
            branch=branch,
            github_tag=github_tag,
            docker_image_tag=docker_image_tag,
            token_usd_gas_price=token_usd_gas_price,
        )
        self.db_handler.save_cost_report_data(report_data=report_data, cost_report_id=cost_report_id)

    def delete_report_and_data(self, repo: str, branch: str, tag: tp.Optional[str]):
        report_ids = self.db_handler.delete_reports(repo=repo, branch=branch, tag=tag)
        self.db_handler.delete_data_by_report_ids(report_ids=report_ids)

    def get_historical_data(
            self,
            depth: int,
            repo: RepoType,
            last_branch: str,
            previous_branch: str,
            tag: str,
    ) -> pd.DataFrame:
        return self.db_handler.get_historical_data(
            depth=depth,
            repo=repo,
            last_branch=last_branch,
            previous_branch=previous_branch,
            tag=tag,
        )

    @staticmethod
    def generate_and_save_plots_pdf(historical_data: pd.DataFrame, title_end: str, output_pdf="cost_reports.pdf") -> str:
        historical_data["timestamp"] = pd.to_datetime(historical_data["timestamp"], errors="coerce")
        historical_data["fee_in_eth"] = historical_data["fee_in_eth"].apply(Decimal)
        historical_data["fee_in_usd"] = historical_data["fee_in_eth"] * historical_data["token_usd_gas_price"]
        historical_data["acc_count"] = historical_data["acc_count"].apply(Decimal)
        historical_data["trx_count"] = historical_data["trx_count"].apply(Decimal)
        historical_data["gas_estimated"] = historical_data["gas_estimated"].apply(Decimal)
        historical_data["gas_used"] = historical_data["gas_used"].apply(Decimal)
        historical_data["token_usd_gas_price"] = historical_data["token_usd_gas_price"].apply(Decimal)
        historical_data["used_%_of_EG"] = (
            (historical_data["gas_used"] / historical_data["gas_estimated"]) * Decimal("100")
        ).apply(lambda x: x.quantize(Decimal("0.000"), rounding=ROUND_HALF_UP))

        # analyze only the dapps that are present in the latest report
        latest_timestamp = historical_data["timestamp"].max()
        latest_report_data = historical_data[historical_data["timestamp"] == latest_timestamp]
        dapp_names = latest_report_data["dapp_name"].unique()
        metrics = ["fee_in_eth", "fee_in_usd", "acc_count", "trx_count", "gas_estimated", "gas_used", "used_%_of_EG"]

        with PdfPages(output_pdf) as pdf:
            for dapp_name in dapp_names:
                # Filter data for the current dapp_name
                dapp_data = historical_data[historical_data["dapp_name"] == dapp_name]
                actions = dapp_data["action"].unique()

                num_rows = len(actions)
                num_cols = len(metrics)
                fig, axes = plt.subplots(nrows=num_rows, ncols=num_cols, figsize=(5 * num_cols, 3 * num_rows), sharex="col")
                fig.suptitle(t=f'Cost report for "{dapp_name}" dApp on {title_end}', fontsize=16, fontweight="bold")

                for action_idx, action in enumerate(actions):
                    # Calculate y-axis limits for each metric
                    buffer_fraction = Decimal("0.5")
                    action_data = dapp_data[dapp_data["action"] == action]
                    y_limits = {}

                    for metric in metrics:
                        metric_data = action_data[metric]
                        min_val = metric_data.min()
                        max_val = metric_data.max()
                        range_val = max_val - min_val

                        if range_val == 0:
                            min_val -= abs(min_val) * buffer_fraction
                            max_val += abs(max_val) * buffer_fraction
                        else:
                            min_val -= range_val * buffer_fraction
                            max_val += range_val * buffer_fraction

                        y_limits[metric] = (min_val, max_val)

                    for metric_idx, metric in enumerate(metrics):
                        ax = axes[action_idx, metric_idx] if num_rows > 1 else axes[metric_idx]
                        data_subset = dapp_data[dapp_data["action"] == action].copy()

                        if not data_subset.empty:
                            # Convert timestamps to evenly spaced numeric values
                            data_subset["time_numeric"] = range(len(data_subset))
                            data_subset = data_subset.sort_values(by=["timestamp"])
                            prev_value = None
                            prev_is_valid = True

                            # Plot blue lines before scatter
                            ax.plot(
                                data_subset["time_numeric"], data_subset[metric], color="blue", linestyle="-", linewidth=1
                            )

                            for i, (x, y) in enumerate(zip(data_subset["time_numeric"], data_subset[metric])):
                                if prev_value is not None and y != prev_value:
                                    ax.scatter(x, y, color="red")
                                    ax.annotate(
                                        f"{y}",
                                        (x, y),
                                        textcoords="offset points",
                                        xytext=(25, 5),
                                        ha="center",
                                        color="red",
                                        rotation=45,
                                    )

                                    if prev_is_valid:
                                        ax.annotate(
                                            f"{prev_value}",
                                            (prev_x, prev_y),
                                            textcoords="offset points",
                                            xytext=(25, 5),
                                            ha="center",
                                            color="blue",
                                            rotation=45,
                                        )
                                    prev_is_valid = False
                                else:
                                    ax.scatter(x, y, color="blue")
                                    prev_is_valid = True

                                prev_value = y
                                prev_x, prev_y = x, y

                            # Formatting x-axis to show evenly spaced points
                            ax.set_xticks(range(len(data_subset)))

                            # set tick labels
                            if data_subset["tag"].notna().any():
                                x_tick_labels = data_subset["tag"]
                            else:
                                x_tick_labels = data_subset["branch"]
                            ax.set_xticklabels(x_tick_labels, rotation=45)
                            ax.tick_params(axis="y", labelsize=8)

                            # Set y-axis limits and labels
                            ax.set_ylim(float(y_limits[metric][0]), float(y_limits[metric][1]))
                            has_decimals = any(Decimal(str(value)) % 1 != 0 for value in data_subset[metric])
                            if has_decimals:
                                ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.3f"))
                            else:
                                ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f"))

                            if metric_idx == 0:
                                multiline_action = textwrap.fill(action, width=30)
                                ax.set_ylabel(multiline_action)

                            if action_idx == 0:
                                ax.set_title(metric)

                plt.tight_layout()
                plt.subplots_adjust(top=0.9)
                pdf.savefig(fig)
                plt.close(fig)

        return output_pdf
