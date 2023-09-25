import json
import random
import string
import typing
from types import SimpleNamespace

import allure
import pytest
import websockets

from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.rpc_checks import assert_fields_are_hex
from integration.tests.services.helpers.basic import cryptohex, hasattr_recursive
from integration.tests.services.helpers.websockets import ws_receive_all_messages, ws_receive_messages_limit_time


class ETH:
    def __init__(self, params: list, method: str):
        self.jsonrpc = 2.0
        self.id = 1
        self.method = method
        self.params = params


class Subscribe(ETH):
    def __init__(self, params: list):
        super().__init__(params, "eth_subscribe")


class Unsubscribe(ETH):
    def __init__(self, subscription_id: str):
        super().__init__([subscription_id], "eth_unsubscribe")


@allure.feature("Websocket Subscriber")
@allure.story("Subscribe to events")
class TestSubscriber(BaseMixin):
    def call_contract_events(self, event_caller_contract):
        arg1, arg2, arg3 = ("text1", "text2", "text3")

        instructions = {
            "callEvent1": [[arg1]],
            "callEvent2": [[arg1, arg2], [arg2, arg3]],
            "callEvent3": [[arg1, arg2, arg3]]
        }
        for i in instructions:
            for args in instructions[i]:
                tx = self.make_tx_object()
                instruction_tx = getattr(event_caller_contract.functions, i)(*args).build_transaction(tx)
                self.web3_client.send_transaction(self.sender_account, instruction_tx)

    def make_tx_object(self) -> typing.Dict:
        return {
            "chainId": self.web3_client._chain_id,
            "gasPrice": self.web3_client.gas_price(),
            "nonce": self.web3_client.eth.get_transaction_count(self.sender_account.address),
            "value": 0,
        }

    @staticmethod
    def assert_all_messages(messages: list, topics: list):
        """
        Validate that messages from the response contain all the initial topics
        (including additional arguments as topics)

        :param list messages: Messages from the websocket response
        :param list topics: Topics that have been subscribed to
        """
        is_event_topic_in_list = False
        is_arg_topic_in_list = False

        for m in messages:
            log = m.params.result
            if topics[0]:
                for topic in topics[0]:
                    if topic in log.topics:
                        is_event_topic_in_list = True
            else:
                is_event_topic_in_list = True
            if len(topics) == 2:
                for topic in topics[1]:
                    if topic in log.topics:
                        is_arg_topic_in_list = True
            else:
                is_arg_topic_in_list = True

        assert is_event_topic_in_list, f"Filter by {topics} works incorrect. Response: {m}"
        assert is_arg_topic_in_list, f"Filter by {topics} works incorrect. Response: {m}"

    @pytest.mark.only_devnet
    async def test_subscribe_to_newheads(self, ws_subscriber_url):
        async with websockets.connect(ws_subscriber_url) as ws:
            data = Subscribe(["newHeads"])
            await ws.send(json.dumps(data.__dict__))
            r = await ws.recv()
            response = json.loads(r, object_hook=lambda d: SimpleNamespace(**d))
            subscription = response.result
            assert len(subscription) > 0

            receipt = self.send_neon(self.sender_account, self.recipient_account, 0.1)

            messages = await ws_receive_messages_limit_time(ws, limit_time=20)

            # find required newHeads message by blockHash
            response = None
            for message in messages:
                if hasattr_recursive(message, "params.result.hash"):
                    result = message.params.result
                    if receipt.blockHash.hex() == result.hash:
                        # TODO additional checks:
                        #  response.number == receipt.blockNumber
                        #  response.receiptsRoot == receipt.transactionHash
                        #  after https://neonlabs.atlassian.net/browse/NDEV-2040
                        response = message
            assert response is not None, \
                f"no message with required blockHash {receipt.blockHash.hex()} in received messages"
            assert hasattr(response.params, "subscription")
            assert response.params.subscription == subscription
            assert_fields_are_hex(response.params.result,
                                  # TODO add ["number", "receiptsRoot"]
                                  #  after https://neonlabs.atlassian.net/browse/NDEV-2040
                                  ["extraData", "gasLimit", "gasUsed", "logsBloom",
                                   "nonce", "parentHash", "sha3Uncles",
                                   "stateRoot", "timestamp", "transactionsRoot"])

            data = Unsubscribe(subscription)
            await ws.send(json.dumps(data.__dict__))
            messages = await ws_receive_all_messages(ws)
            response = messages[len(messages) - 1]
            assert response.result == 'true'

            self.send_neon(self.sender_account, self.recipient_account, 0.1)
            messages = await ws_receive_all_messages(ws)
            assert len(messages) == 0, \
                f"Expected no events to be received after unsubscription, but got {len(messages)} events"

    @pytest.mark.only_devnet
    @pytest.mark.parametrize("param_fields", [("address", "topics"), ("topics",), ("address",), ()], ids=str)
    async def test_logs(self, param_fields, event_caller_contract, ws_subscriber_url):
        async with websockets.connect(ws_subscriber_url) as ws:
            optional_fields = {}
            topic = False

            if "address" in param_fields:
                optional_fields["address"] = event_caller_contract.address
            if "topics" in param_fields:
                topic = cryptohex("AllTypes(address,uint256,string,bytes32,bool)")
                optional_fields["topics"] = [topic]

            params = ["logs"]
            if len(optional_fields) > 0:
                params.append(optional_fields)

            data = Subscribe(params)
            await ws.send(json.dumps(data.__dict__))
            r = await ws.recv()
            response = json.loads(r, object_hook=lambda d: SimpleNamespace(**d))
            subscription = response.result
            assert len(subscription) > 0

            number = random.randint(1, 100)
            text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
            bytes_array = text.encode().ljust(32, b'\0')
            bol = True
            tx = self.make_tx_object()
            instruction_tx = event_caller_contract.functions.allTypes(
                self.sender_account.address, number, text, bytes_array, bol
            ).build_transaction(tx)
            self.web3_client.send_transaction(self.sender_account, instruction_tx)

            messages = await ws_receive_all_messages(ws)
            if len(param_fields) == 0:
                assert (len(messages) >= 1), f"Expected 1 event log or more, but found {len(messages)}"
            else:
                assert (len(messages) == 1), \
                    f"Expected 1 event log, but found {len(messages)}, " \
                    f"contract address {event_caller_contract.address}," \
                    f"messages: {messages}"
                assert hasattr_recursive(messages[0], "params.result.address")
                assert messages[0].params.result.address == event_caller_contract.address.lower(), \
                    "filter by address should emit only events with the same address, but received different"
            response = messages[0]
            assert hasattr_recursive(response, "params.subscription")
            assert hasattr(response.params, "result")
            assert response.params.subscription == subscription
            if topic:
                assert hasattr(response.params.result, "topics")
                assert topic in response.params.result.topics
            assert_fields_are_hex(response.params.result,
                                  ["transactionHash", "blockHash",
                                   "blockNumber", "transactionIndex",
                                   "address", "logIndex", "data"])

            data = Unsubscribe(subscription)
            await ws.send(json.dumps(data.__dict__))
            r = await ws.recv()
            response = json.loads(r, object_hook=lambda d: SimpleNamespace(**d))
            assert response.result == 'true'

    @pytest.mark.only_devnet
    @pytest.mark.parametrize(
        "event_filter, arg_filter, log_count",
        [
            (["Event2(string,string)"], None, 2),
            # TODO add following testcases after https://neonlabs.atlassian.net/browse/NDEV-2036
            # ([], ["text1"], 3),
            (["Event2(string,string)"], ["text2"], 1),
            # (["Event2(string,string)", "Event3(string,string,string)"], ["text2", "text3", "text1", "text5"], 3,),
            ([], None, 4),
        ],
    )
    async def test_filter_log_by_topics(
            self, event_filter, arg_filter, log_count, event_caller_contract, ws_subscriber_url):
        async with websockets.connect(ws_subscriber_url) as ws:
            # prepare params with specified topics and send them to websocket service
            topics = []
            if event_filter is not None:
                event_topics = []
                for item in event_filter:
                    event_topics.append(cryptohex(item))
                topics.append(event_topics)
            if arg_filter is not None:
                arg_topics = []
                for item in arg_filter:
                    arg_topics.append(cryptohex(item))
                topics.append(arg_topics)

            optional_fields = {"address": event_caller_contract.address}
            if topics:
                optional_fields["topics"] = topics
            params = ["logs", optional_fields]

            data = Subscribe(params)
            await ws.send(json.dumps(data.__dict__))
            r = await ws.recv()
            response = json.loads(r, object_hook=lambda d: SimpleNamespace(**d))
            subscription = response.result
            assert len(subscription) > 0

            # send transactions to trigger messages in websocket service
            self.call_contract_events(event_caller_contract)

            # validate result — all the received messages
            messages = await ws_receive_all_messages(ws)
            assert (len(messages) == log_count), \
                f"Expected {log_count} event logs, but found {len(messages)}: {messages}"
            self.assert_all_messages(messages, topics)

    @pytest.mark.only_devnet
    async def test_multiples_users_different_logs(self, event_caller_contract, ws_subscriber_url):
        topic1 = cryptohex("Event1(string)")
        topic2 = cryptohex("Event3(string,string,string)")
        params1 = ["logs", {"address": event_caller_contract.address, "topics": [topic1]}]
        params2 = ["logs", {"address": event_caller_contract.address, "topics": [topic2]}]

        data1, data2 = Subscribe(params1), Subscribe(params2)

        async with (
            websockets.connect(ws_subscriber_url) as ws1, websockets.connect(ws_subscriber_url) as ws2
        ):
            await ws1.send(json.dumps(data1.__dict__))
            r1 = await ws1.recv()
            response1 = json.loads(r1, object_hook=lambda d: SimpleNamespace(**d))
            subscription1 = response1.result

            await ws2.send(json.dumps(data2.__dict__))
            r2 = await ws2.recv()
            response2 = json.loads(r2, object_hook=lambda d: SimpleNamespace(**d))
            subscription2 = response2.result

            self.call_contract_events(event_caller_contract)

            messages1, messages2 = await ws_receive_all_messages(ws1), await ws_receive_all_messages(ws2)
            assert len(messages1) == 1, f"expected to receive 1 event for user1, but received {len(messages1)}"
            assert len(messages2) == 1, f"expected to receive 1 event for user2, but received {len(messages2)}"
            message1, message2 = messages1[0], messages2[0]
            assert hasattr_recursive(message1, "params.subscription")
            assert hasattr_recursive(message2, "params.subscription")
            assert hasattr_recursive(message1, "params.result.topics")
            assert hasattr_recursive(message2, "params.result.topics")
            r_subscription1, r_subscription2 = message1.params.subscription, message2.params.subscription
            topics1, topics2 = message1.params.result.topics, message2.params.result.topics
            assert r_subscription1 == subscription1, \
                f"expected received subscription {r_subscription1} to be equal {subscription1}"
            assert messages2[0].params.subscription == subscription2, \
                f"expected received subscription {r_subscription2} to be equal {subscription2}"
            assert topics1[0] == topic1, f"expected received topic {topics1[0]} equal to {topic1}"
            assert len(topics1) == 2, f"expected 2 topics for Event1, but received {len(topics1)}: {topics1}"
            assert topics2[0] == topic2, f"expected received topic {topics2[0]} equal to {topic2}"
            assert len(topics2) == 4, f"expected 4 topics for Event3, but received {len(topics2)}: {topics2}"

    @pytest.mark.only_devnet
    @pytest.mark.parametrize("subscription_type", ["newHeads", "logs"])
    async def test_another_user_cant_unsubscribe(self, subscription_type: string, ws_subscriber_url):
        async with (
            websockets.connect(ws_subscriber_url) as ws1, websockets.connect(ws_subscriber_url) as ws2
        ):
            data = Subscribe([subscription_type])
            await ws1.send(json.dumps(data.__dict__))
            r = await ws1.recv()
            response = json.loads(r, object_hook=lambda d: SimpleNamespace(**d))
            subscription = response.result
            assert len(subscription) > 0

            data = Unsubscribe(subscription)
            await ws2.send(json.dumps(data.__dict__))
            r = await ws2.recv()
            assert "error" in r
            assert "Subscription not found" in r
