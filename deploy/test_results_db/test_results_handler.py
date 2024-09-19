import textwrap
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_pdf import PdfPages


class TestResultsHandler:
    @staticmethod
    def generate_and_save_plots_pdf(
            historical_data: pd.DataFrame,
            title_end: str,
            output_pdf: str,
    ) -> str:
        historical_data["timestamp"] = pd.to_datetime(historical_data["timestamp"], errors="coerce")
        historical_data["acc_count"] = historical_data["acc_count"].apply(Decimal)
        historical_data["trx_count"] = historical_data["trx_count"].apply(Decimal)
        historical_data["gas_estimated"] = historical_data["gas_estimated"].apply(Decimal)
        historical_data["gas_used"] = historical_data["gas_used"].apply(Decimal)
        historical_data["gas_used_%"] = (
            (historical_data["gas_used"] / historical_data["gas_estimated"]) * Decimal("100")
        ).apply(lambda x: x.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP))
        historical_data["compute_units"] = historical_data["compute_units"].apply(Decimal)

        # analyze only the dapps that are present in the latest report
        latest_timestamp = historical_data["timestamp"].max()
        latest_report_data = historical_data[historical_data["timestamp"] == latest_timestamp]
        dapp_names = latest_report_data["dapp_name"].unique()
        metrics = ["acc_count", "trx_count", "gas_estimated", "gas_used", "gas_used_%", "compute_units"]
        historical_data = historical_data.sort_values(by=["timestamp"])

        unique_timestamps = historical_data["timestamp"].unique().tolist()
        x_tick_labels = historical_data.groupby('timestamp')['tag'].first().tolist()

        with PdfPages(output_pdf) as pdf:
            for dapp_name in dapp_names:
                # Filter data for the current dapp_name
                dapp_data = historical_data[historical_data["dapp_name"] == dapp_name]
                actions = dapp_data["action"].unique()

                num_rows = len(actions)
                num_cols = len(metrics)
                axes: plt.Axes
                fig, axes = plt.subplots(nrows=num_rows, ncols=num_cols, figsize=(5 * num_cols, 3 * num_rows), sharex="col")
                fig.suptitle(t=f'Cost report for "{dapp_name}" dApp\n{title_end}', fontsize=16, fontweight="bold")

                for action_idx, action in enumerate(actions):
                    # Calculate y-axis limits for each metric
                    buffer_fraction = Decimal("0.5")
                    action_data = dapp_data[dapp_data["action"] == action]
                    y_limits = {}

                    # define y limits
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

                        # normalize data
                        need_to_add_rows = len(unique_timestamps) - len(data_subset)
                        if need_to_add_rows:
                            for i, unique_timestamp in enumerate(unique_timestamps):
                                if unique_timestamp not in data_subset["timestamp"].values:
                                    new_row = pd.DataFrame(
                                        data=[{
                                            "timestamp": unique_timestamp,
                                            "tag": x_tick_labels[i],
                                            "dapp_name": data_subset.iloc[0]["dapp_name"],
                                            "action": data_subset.iloc[0]["action"],
                                        }],
                                        columns=data_subset.columns,
                                    )
                                    data_subset = pd.concat([data_subset, new_row], ignore_index=True)

                        data_subset = data_subset.sort_values(by='timestamp').reset_index(drop=True)

                        if not data_subset.empty:
                            prev_value = None
                            prev_is_valid = True

                            # Fill data for smooth lines
                            data_subset_filled = data_subset.copy()

                            for column in data_subset.columns:
                                for i in range(1, len(data_subset) - 1):
                                    if pd.isna(data_subset_filled.loc[i, column]):
                                        above_value = data_subset_filled.loc[i - 1, column]
                                        below_value = data_subset_filled.loc[i + 1, column]
                                        if pd.notna(above_value) and pd.notna(below_value):
                                            try:  # for numerical data
                                                data_subset_filled.loc[i, column] = (above_value + below_value) / 2
                                            except TypeError:  # for non-numerical data
                                                data_subset_filled.loc[i, column] = above_value or below_value

                            # Plot grey lines before scatter
                            ax.plot(
                                data_subset_filled.index,
                                data_subset_filled[metric],
                                color="darkgrey",
                                linestyle="-",
                                linewidth=2,
                                zorder=1,
                            )

                            # Plot blue or red dots
                            for i, (x, y) in enumerate(zip(data_subset.index, data_subset[metric])):
                                if not pd.isna(y):
                                    # last 2 dots should be larger
                                    dot_size = 50 if i < len(data_subset[metric]) - 2 else 150
                                    if prev_value is not None and y != prev_value:
                                        # next data point has different value compared to the previous one
                                        ax.scatter(x, y, color="red", zorder=2, s=dot_size)
                                        ax.annotate(
                                            f"{y}",
                                            (x, y),
                                            textcoords="offset points",
                                            xytext=(15, 5),
                                            ha="center",
                                            color="red",
                                            rotation=60,
                                        )

                                        if prev_is_valid:
                                            # if the previous data point had the same value as the preceding one
                                            ax.annotate(
                                                f"{prev_value}",
                                                (prev_x, prev_y),
                                                textcoords="offset points",
                                                xytext=(15, 5),
                                                ha="center",
                                                color="blue",
                                                rotation=60,
                                            )
                                        prev_is_valid = False
                                    else:
                                        ax.scatter(x, y, color="blue", s=dot_size)
                                        prev_is_valid = True

                                    prev_value = y
                                    prev_x, prev_y = x, y

                            # Set x-axis ticks and labels
                            ax.set_xticks(range(len(x_tick_labels)))
                            ax.set_xticklabels(x_tick_labels, rotation=45)

                            # Set y-axis limits and labels
                            ax.tick_params(axis="y", labelsize=8)
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

                            # add vertical grey dotted line before the last two dots
                            if len(data_subset[metric]) > 2:
                                ax.axvline(x=len(data_subset[metric]) - 2.5, color='#a6a4a4', linestyle=':')

                plt.tight_layout()
                plt.subplots_adjust(top=0.9)
                pdf.savefig(fig)
                plt.close(fig)

        return output_pdf
