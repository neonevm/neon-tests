import { ethClient } from '../utils/ethClient.js';
import { standardScenarioOptions } from '../../options/options.js';
import { Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';

import exec from 'k6/execution';
import { check } from 'k6';

const ethCallRequests = new Counter('eth_get_storage_at_requests');
const ethCallRequestErrorCounter = new Counter('eth_get_storage_at_request_errors');
const ethCallErrorCounter = new Counter('eth_get_storage_at_errors');
const ethCallRequestTime = new Trend('eth_get_storage_at_request_time', true);

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


export default function EthCallTest() {
    const vuID = exec.vu.idInTest
    const index = vuID % usersArray.length;
   
    const dataIndex = vuID % (historicalData.storage_contract_calls).length;
    const txInfo = historicalData.storage_contract_calls[dataIndex];

    const accountPrivateKey = usersArray[index].sender_key;
    const client = ethClient(accountPrivateKey);

    // blockNumber
    const requestParamsBlockNumber = {
        requestType: "blockNumber",
        method: "eth_call",
        params: [txInfo.retreive_function_tx, {"blockNumber": txInfo.blockNumber}]
    }

    doRequest(client, requestParamsBlockNumber, txInfo.store_value);

    // blockHash
    const requestParamsBlockHash = {
        requestType: "blockHash",
        method: "eth_call",
        params: [txInfo.retreive_function_tx, {"blockHash": txInfo.blockHash}]
    }
    
    doRequest(client, requestParamsBlockHash, txInfo.store_value);
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
        console.log('response: ' + JSON.stringify(response));
        console.log('expectedValue: ' + expectedValue);
        console.log('result: ' + parseInt(response.result, 16));
        const checkResult = check(response, {
            'response result is not expected value': (r) => parseInt(r.result, 16) == expectedValue,
        });
        if (!checkResult) {
            console.log('Error in response of eth_call: ' + JSON.stringify(response));
            ethCallRequestErrorCounter.add(1);
        }
    } catch (e) {
        console.log('Error in eth_call: ' + e);
        ethCallErrorCounter.add(1);
    }
    ethCallRequestTime.add(new Date() - startTime);
    ethCallRequests.add(1);
}