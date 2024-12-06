import { ethClient } from '../utils/ethClient.js';
import { standardScenarioOptions } from '../../options/options.js';
import { Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';

import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import exec from 'k6/execution';
import { check } from 'k6';

const debugTraceTransactionRequests = new Counter('debug_trace_transaction_requests');
const debugTraceTransactionRequestErrorCounter = new Counter('debug_trace_transaction_request_errors');
const debugTraceTransactionErrorCounter = new Counter('debug_trace_transaction_errors');
const debugTraceTransactionRequestTime = new Trend('debug_trace_transaction_request_time', true);

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

    const dataIndexStorage = randomIntBetween(0, (historicalData.storage_contract_calls).length - 1);
    const txInfoStorage = historicalData.storage_contract_calls[dataIndexStorage];

    const dataIndexEvent = randomIntBetween(0, (historicalData.event_caller_contract_calls).length - 1);
    const txInfoEvent = historicalData.event_caller_contract_calls[dataIndexEvent];

    const dataIndexIterative = randomIntBetween(0, (historicalData.iterative_tx_contract_calls).length - 1);
    const txInfoIterative = historicalData.iterative_tx_contract_calls[dataIndexIterative];

    const accountPrivateKey = usersArray[index].sender_key;
    const client = ethClient(accountPrivateKey);

    // call storage contract
    // blockNumber
    const requestParamsBlockNumberStorage = {
        requestType: "blockNumber",
        method: "debug_traceTransaction",
        params: [txInfoStorage.tx_hash, {"blockNumber": txInfoStorage.blockNumber}]
    }

    doRequest(client, requestParamsBlockNumberStorage, checkExpectedValueStorage, txInfoStorage.store_value);

    // blockHash
    const requestParamsBlockHashStorage = {
        requestType: "blockHash",
        method: "debug_traceTransaction",
        params: [txInfoStorage.tx_hash, {"blockHash": txInfoStorage.blockHash}]
    }
    
    doRequest(client, requestParamsBlockHashStorage, checkExpectedValueStorage, txInfoStorage.store_value);

    // call event caller contract
    // blockNumber
    const tracer_config = { "tracer": "callTracer", "tracerConfig": { "withLog": true } }
    const requestParamsBlockNumberEvent = {
        requestType: "blockNumber",
        method: "debug_traceTransaction",
        params: [txInfoEvent.tx_hash, tracer_config]
    }

    doRequest(client, requestParamsBlockNumberEvent, checkExpectedValueEvent, [1, 2]);

    // blockHash
    const requestParamsBlockHashEvent = {
        requestType: "blockHash",
        method: "debug_traceTransaction",
        params: [txInfoEvent.tx_hash, tracer_config]
    }
    
    doRequest(client, requestParamsBlockHashEvent, checkExpectedValueEvent, [1, 2]);

    // call iterative tx contract
    // blockNumber
    const requestParamsBlockNumberIterative = {
        requestType: "blockNumber",
        method: "debug_traceTransaction",
        params: [txInfoIterative.tx_hash, tracer_config]
    }

    doRequest(client, requestParamsBlockNumberIterative, checkExpectedValueIterative, 1001);

    // blockHash
    const requestParamsBlockHashIterative = {
        requestType: "blockHash",
        method: "debug_traceTransaction",
        params: [txInfoIterative.tx_hash, tracer_config]
    }
    
    doRequest(client, requestParamsBlockHashIterative, checkExpectedValueIterative, 1001);                    
}

function doRequest(client, requestParams, checkExpectedValueFunction, args) {
    const startTime = new Date();
    try {
        const responseBody = client.callTracer(
            JSON.stringify(requestParams.requestType), 
            JSON.stringify(requestParams.method), 
            JSON.stringify(requestParams.params)
        );
        const response = JSON.parse(responseBody);
        const checkResult = checkExpectedValueFunction(response, args);
        if (!checkResult) {
            console.log('Error in response of debug_traceTransaction: ' + JSON.stringify(response));
            debugTraceTransactionRequestErrorCounter.add(1);
        }
    } catch (e) {
        console.log('Error in debug_traceTransaction: ' + e);
        debugTraceTransactionErrorCounter.add(1);
    }
    debugTraceTransactionRequestTime.add(new Date() - startTime);
    debugTraceTransactionRequests.add(1);
}


function checkExpectedValueStorage(response, expectedValue) {
    return check(response, {
        'response result is not expected value': (r) => { 
            return (parseInt(r.result.returnValue, 16) == expectedValue)
        }
    });
}

function checkExpectedValueEvent(response, expectedValue) {
    return check(response, {
        'response result is not expected value': (r) => { 
            return ((r.result.calls[0].logs.length == expectedValue[0]) && (r.result.logs.length == expectedValue[1]))
        }
    });
}

function checkExpectedValueIterative(response, expectedValue) {
    return check(response, {
        'response result is not expected value': (r) => { 
            return (r.result.logs.length == expectedValue)
        }
    });
}