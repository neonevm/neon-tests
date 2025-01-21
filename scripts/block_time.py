import os
import sys
import time
from datetime import datetime, timezone
from solana.rpc.core import RPCException

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from utils.solana_client import SolanaClient

sol_client = SolanaClient("https://solana-api.instantnodes.io/token-OjVeh8exYGMeFh7QKIRLsF93T4xratD6")

expected_time = "20-10-2024 00:00:00"

dt = datetime.strptime(expected_time, "%d-%m-%Y %H:%M:%S")
unix_time = int(time.mktime(dt.timetuple()))

utc_unix_time = int(dt.replace(tzinfo=timezone.utc).timestamp())


def get_time_for_closest_exist_slot(slot: int):
    try:
        time = sol_client.get_block_time(slot).value
        return slot, time
    except RPCException as e:
        print(f"Slot {slot} is skipped {e}")
        return get_time_for_closest_exist_slot(slot + 1)


# Given data
current_slot = sol_client.get_slot().value
current_time = sol_client.get_block_time(current_slot).value
slot_time_seconds = 0.4
expected_timestamp = utc_unix_time


def get_estimated_slot_for_time(current_slot, current_time, expected_timestamp, slot_time_seconds):
    time_difference_seconds = current_time - expected_timestamp
    slots_passed = time_difference_seconds / slot_time_seconds
    counted_slot = current_slot - int(slots_passed)
    return counted_slot


while abs(current_time - expected_timestamp) > 1:
    current_slot = get_estimated_slot_for_time(current_slot, current_time, expected_timestamp, slot_time_seconds)
    current_time = get_time_for_closest_exist_slot(current_slot)[1]

    print(current_slot)

print("Timestamp for the closest slot: ", current_time)
