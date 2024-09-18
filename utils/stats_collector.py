import contextlib
import inspect
import json
from pathlib import Path
from typing import Callable, Generator

from filelock import FileLock
from web3.types import TxReceipt

from clickfile import COST_REPORT_DIR
from conftest import GEN_COST_REPORTS
from utils.models.cost_report_model import CostReportModel, CostReportAction


class cost_report:  # noqa
    def __init__(
            self,
            func: Callable[..., TxReceipt],
    ):
        self.func: Callable[..., TxReceipt] = func
        self.model = CostReportModel(name=Path(inspect.getfile(func)).stem)
        self.report_file: Path = self.__get_report_file_path(directory=COST_REPORT_DIR)
        self.lock = FileLock(self.report_file.with_suffix(self.report_file.suffix + ".lock"), is_singleton=True)

    def __create(self):
        data = self.model.model_dump_json(indent=4)
        self.report_file.write_text(data)

    def read(self) -> CostReportModel:
        with self.report_file.open() as f:
            data = json.load(f)
        report = CostReportModel(**data)
        return report

    @contextlib.contextmanager
    def _update(self) -> Generator[CostReportModel, None, None]:
        with self.lock:
            if not self.report_file.exists():
                self.__create()

            report: CostReportModel = self.read()

            yield report

            data = report.model_dump_json(indent=4)
            self.report_file.write_text(data)

    def __get_report_file_path(self, directory: str) -> Path:
        root_dir: Path = Path(__file__).resolve().parent.parent
        func_file_path = Path(inspect.getfile(self.func)).relative_to(root_dir)
        report_file_name = '.'.join(func_file_path.parts[:-1]) + '.' + func_file_path.stem + ".json"
        file_path = root_dir / Path(directory) / report_file_name
        return file_path

    def __get__(self, instance, owner):
        return lambda *args, **kwargs: self.__call__(instance, *args, **kwargs)

    def __call__(self, *args, **kwargs) -> TxReceipt:
        receipt: TxReceipt = self.func(*args, **kwargs)

        if GEN_COST_REPORTS:
            used_gas = receipt['gasUsed']
            gas_price = receipt['effectiveGasPrice']
            tx_hash = receipt['transactionHash'].hex()

            action = CostReportAction(
                name=self.func.__name__,
                usedGas=used_gas,
                gasPrice=gas_price,
                tx=tx_hash,
            )

            report: CostReportModel
            with self._update() as report:
                report.actions.append(action)

        return receipt
