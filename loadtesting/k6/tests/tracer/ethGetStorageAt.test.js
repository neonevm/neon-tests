import { ethClient } from '../utils/ethClient.js';
import { standardScenarioOptions } from '../../options/options.js';
import { Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';

import exec from 'k6/execution';
import { check } from 'k6';

const ethGetStorageAtRequests = new Counter('tracer_eth_get_storage_at_requests');
const ethGetStorageAtRequestErrorCounter = new Counter('tracer_eth_get_storage_at_request_errors');
const ethGetStorageAtErrorCounter = new Counter('tracer_eth_get_storage_at_errors');
const ethGetStorageAtRequestTime = new Trend('tracer_eth_get_storage_at_request_time', true);

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


export default function EthGetStorageAtTest() {
    const vuID = exec.vu.idInTest
    const index = vuID % usersArray.length;

    const dataIndex = vuID % (historicalData.storage_contract_calls).length;
    const txInfo = historicalData.storage_contract_calls[dataIndex];

    const accountPrivateKey = usersArray[index].sender_key;
    const client = ethClient(accountPrivateKey);

    // blockNumber
    const requestParamsBlockNumber = {
        requestType: "blockNumber",
        method: "eth_getStorageAt",
        params: [txInfo.storage_contract_address, "0x0", {"blockNumber": txInfo.blockNumber}]
    }

    doRequest(client, requestParamsBlockNumber);

    // blockHash
    const requestParamsBlockHash = {
        requestType: "blockHash",
        method: "eth_getStorageAt",
        params: [txInfo.storage_contract_address, "0x0", {"blockHash": txInfo.blockHash}]
    }
    
    doRequest(client, requestParamsBlockHash);
}

function doRequest(client, requestParams) {
    const startTime = new Date();
    try {
        const responseBody = client.callTracer(
            JSON.stringify(requestParams.requestType), 
            JSON.stringify(requestParams.method), 
            JSON.stringify(requestParams.params)
        );
        const response = JSON.parse(responseBody);
        const checkResult = check(response, {
            'response result is not 0': (r) => r.result != "0x0",
        });
        if (!checkResult) {
            console.log('Error in response of eth_getStorageAt: ' + JSON.stringify(response));
            ethGetStorageAtRequestErrorCounter.add(1);
        }
    } catch (e) {
        console.log('Error in eth_getStorageAt: ' + e);
        ethGetStorageAtErrorCounter.add(1);
    }
    ethGetStorageAtRequestTime.add(new Date() - startTime);
    ethGetStorageAtRequests.add(1);
}