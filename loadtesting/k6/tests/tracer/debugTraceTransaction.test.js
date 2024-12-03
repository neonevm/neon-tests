import { ethClient } from '../utils/ethClient.js';
import { standardScenarioOptions } from '../../options/options.js';
import { Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';

import exec from 'k6/execution';
import { check } from 'k6';

const debugTraceTransactionRequests = new Counter('eth_get_storage_at_requests');
const debugTraceTransactionRequestErrorCounter = new Counter('eth_get_storage_at_request_errors');
const debugTraceTransactionErrorCounter = new Counter('eth_get_storage_at_errors');
const debugTraceTransactionRequestTime = new Trend('eth_get_storage_at_request_time', true);

export const options = standardScenarioOptions;

const historicalData = JSON.parse(open("../../data/tracer_data.json"));

const usersArray = new SharedArray('Users accounts', function () {
    const accounts = JSON.parse(open("../../data/accounts.json"));
    let data = [];
    for (let i = 0; i < Object.keys(accounts).length; i++) {
        data[i] = accounts[i];
    }
    return data;
});


export default function DebugTraceTransactionTest() {
    const vuID = exec.vu.idInTest
    const index = vuID % usersArray.length;

    const dataIndexStorage = vuID % (historicalData.storage_contract_calls).length;
    const txInfoStorage = historicalData.storage_contract_calls[dataIndexStorage];

    const dataIndexEvent = vuID % (historicalData.event_caller_contract_calls).length;
    const txInfoEvent = historicalData.event_caller_contract_calls[dataIndexStorage];

    const dataIndexIterative = vuID % (historicalData.iterative_tx_contract_calls).length;
    const txInfoIterative = historicalData.iterative_tx_contract_calls[dataIndexStorage];


    const accountPrivateKey = usersArray[index].sender_key;
    const client = ethClient(accountPrivateKey);

    // blockNumber
    const requestParamsBlockNumber = {
        requestType: "blockNumber",
        method: "debug_traceTransaction",
        params: [txInfoStorage.tx_hash, {"blockNumber": txInfoStorage.blockNumber}]
    }

    doRequest(client, requestParamsBlockNumber, txInfoStorage.store_value);

    // blockHash
    const requestParamsBlockHash = {
        requestType: "blockHash",
        method: "debug_traceTransaction",
        params: [txInfoStorage.tx_hash, {"blockHash": txInfoStorage.blockHash}]
    }
    
    doRequest(client, requestParamsBlockHash, txInfoStorage.store_value);
}

function doRequest(client, requestParams, expectedValue) {
    const startTime = new Date();
    try {
        const responseBody = client.callTracer(
            JSON.stringify(requestParams.requestType), 
            JSON.stringify(requestParams.method), 
            JSON.stringify(requestParams.params)
        );
        const response = JSON.parse(responseBody);
        console.log('expectedValue: ' + expectedValue);
        console.log('result: ' + parseInt(response.result.returnValue, 16));
        const checkResult = check(response, {
            'response result is not expected value': (r) => parseInt(r.result.returnValue, 16) == expectedValue,
        });
        if (!checkResult) {
            console.log('Error in response of eth_call: ' + JSON.stringify(response));
            debugTraceTransactionRequestErrorCounter.add(1);
        }
    } catch (e) {
        console.log('Error in eth_call: ' + e);
        debugTraceTransactionErrorCounter.add(1);
    }
    debugTraceTransactionRequestTime.add(new Date() - startTime);
    debugTraceTransactionRequests.add(1);
}