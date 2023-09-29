# Overview

Verify RLP decoding

# Tests list

| Test case                                 | Description                                     | XFailed |
|-------------------------------------------|-------------------------------------------------|---------|
| TestTrxRlpDecoding::test_modify_v         | Change value for "V" parameter and expect error |         |
| TestTrxRlpDecoding::test_modify_s         | Change value for "S" parameter and expect error |         |
| TestTrxRlpDecoding::test_modify_r         | Change value for "R" parameter and expect error |         |
| TestTrxRlpDecoding::test_add_waste_to_trx | Transaction with bad sign                       |         |
