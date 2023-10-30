import functools
import json
import logging
import os
import re
import pathlib
import sys
import time
import typing as tp
import uuid
from dataclasses import dataclass

import requests
import tabulate
from web3.datastructures import AttributeDict
from web3.exceptions import TimeExhausted

from locust import events
from locust.runners import WorkerRunner

from utils import operator
from utils.web3client import NeonChainWeb3Client

from . import env

LOG = logging.getLogger(__name__)


def get_token_balance(op: operator.Operator) -> tp.Dict:
    """Return tokens balance"""
    return dict(neon=op.get_neon_balance(), sol=op.get_solana_balance())


def execute_before(*attrs) -> tp.Callable:
    """Extends user task functional"""

    @functools.wraps(*attrs)
    def ext_runner(func: tp.Callable) -> tp.Callable:
        @functools.wraps(func)
        def task_wrapper(self, *args, **kwargs) -> tp.Any:
            for attr in attrs:
                getattr(self, attr)(*args, **kwargs)
            return func(self, *args, **kwargs)

        return task_wrapper

    return ext_runner


@events.test_start.add_listener
def operator_economy_pre_balance(environment, **kwargs):
    if isinstance(environment.runner, WorkerRunner):
        return
    LOG.info("Get operator balances")
    op = operator.Operator(
        environment.credentials["proxy_url"],
        environment.credentials["solana_url"],
        environment.credentials["operator_neon_rewards_address"],
        environment.credentials["spl_neon_mint"],
        environment.credentials["operator_keys"],
        web3_client=NeonChainWeb3Client(
            environment.credentials["proxy_url"]
        ),
    )
    environment.op = op
    environment.pre_balance = get_token_balance(op)


@events.test_stop.add_listener
def operator_economy_balance(environment, **kwargs):
    if isinstance(environment.runner, WorkerRunner):
        return
    LOG.info("Get operator balances")
    balance = get_token_balance(environment.op)
    operator_balance = tabulate.tabulate(
        [
            ["NEON", environment.pre_balance["neon"], balance["neon"]],
            ["SOL", environment.pre_balance["sol"], balance["sol"]],
        ],
        headers=["Token", "Balance before", "Balance after"],
        tablefmt="fancy_outline",
        numalign="right",
        floatfmt=".2f",
    )
    LOG.info(f"\n{10 * '_'} Operator balance {10 * '_'}\n{operator_balance}\n")


class LocustEventHandler:
    """Implements custom Locust events handler"""

    def __init__(self, request_event: "EventHook") -> None:
        self.buffer: tp.Dict[str, tp.Any] = dict()
        self._request_event = request_event

    def init_event(
        self,
        task_id: str,
        request_type: str,
        task_name: tp.Optional[str] = "",
        start_time: tp.Optional[float] = None,
    ) -> None:
        """Added data to buffer"""
        params = dict(
            name=task_name,
            start_time=start_time or time.time(),
            request_type=request_type,
            start_perf_counter=time.perf_counter(),
        )
        self.buffer[task_id] = params
        LOG.debug("- buffer - %s" % self.buffer)

    def fire_event(self, task_id: str, **kwargs) -> None:
        """Sends event to locust ."""
        event = self.buffer.pop(task_id)
        total_time = (time.perf_counter() - event["start_perf_counter"]) * 1000
        request_meta = dict(
            name=event["name"],
            request_type=event["request_type"],
            response=event.get("response"),
            response_time=total_time,
            response_length=event.get("response_length", 0),
            exception=event.get("exception"),
            context={},
        )
        self._request_event.fire(**request_meta)
        LOG.debug(
            "- %s : %s - %sms"
            % (event["request_type"], event["event_type"], total_time)
        )


locust_events_handler = LocustEventHandler(events.request)


def statistics_collector(name: tp.Optional[str] = None) -> tp.Callable:
    """Handle locust events."""

    def decor(func: tp.Callable) -> tp.Callable:
        @functools.wraps(func)
        def wrap(*args, **kwargs) -> tp.Any:
            task_id = str(uuid.uuid4())
            if name:
                request_type = name
            else:
                request_type = f"{func.__name__.replace('_', ' ').title()}"
            event = dict(task_id=task_id, request_type=request_type)
            locust_events_handler.init_event(**event)
            response = None
            try:
                response = func(*args, **kwargs)
                event = dict(
                    response=response,
                    response_length=sys.getsizeof(response),
                    event_type="success",
                )
            except Exception as err:
                event = dict(event_type="failure", exception=err)
                locust_events_handler.buffer[task_id].update(event)
                locust_events_handler.fire_event(task_id)
                LOG.error(
                    f"Web3 RPC call {request_type} is failed: {err} passed args: `{args}`, passed kwargs: `{kwargs}`"
                )
                raise
            locust_events_handler.buffer[task_id].update(event)
            locust_events_handler.fire_event(task_id)
            return response

        return wrap

    return decor


def save_transaction(transactions: tp.List[str]) -> tp.Callable:
    def decor(func: tp.Callable) -> tp.Callable:
        @functools.wraps(func)
        def wrap(*args, **kwargs) -> tp.Any:
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                tx_id = re.findall("(0x[\w\d]+)", str(e))
                if tx_id:
                    transactions.append(f"{tx_id[0]}")
                raise
            if isinstance(result, AttributeDict) or (
                isinstance(result, tuple)
                and len(result) == 2
                and isinstance(result[1], AttributeDict)
            ):
                if isinstance(result, tuple) and len(result) == 2:
                    tx = result[1]
                else:
                    tx = result
                if "transactionHash" in tx:
                    transactions.append(f'{tx["transactionHash"].hex()}')
            return result

        return wrap

    return decor
