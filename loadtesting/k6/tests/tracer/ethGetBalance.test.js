import { ethClient } from '../utils/ethClient.js';
import { standardScenarioOptions } from '../../options/options.js';
import { Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';

import exec from 'k6/execution';
import { check } from 'k6';

const ethGetBalanceRequests = new Counter('eth_get_storage_at_requests');
const ethGetBalanceRequestErrorCounter = new Counter('eth_get_storage_at_request_errors');
const ethGetBalanceErrorCounter = new Counter('eth_get_storage_at_errors');
const ethGetBalanceRequestTime = new Trend('eth_get_storage_at_request_time', true);

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


export default function EthGetBalanceTest() {
    const vuID = exec.vu.idInTest
    const index = vuID % usersArray.length;

    // TODO: use this value when erc20 get balance will be available
    // const mixedData = (historicalData.neon_transfers).concat(historicalData.erc20_transfers, 
    //     historicalData.erc20spl_transfers);
    const mixedData = historicalData.neon_transfers
    const dataIndex = vuID % mixedData.length;
    const txInfo = mixedData[dataIndex];

    const accountPrivateKey = usersArray[index].sender_key;
    const client = ethClient(accountPrivateKey);

    // blockNumber
    const requestParamsBlockNumber = {
        requestType: "blockNumber",
        method: "eth_getBalance",
        params: [txInfo.sender, {"blockNumber": txInfo.blockNumber}]
    }

    doRequest(client, requestParamsBlockNumber, txInfo.sender_balance_after);

    // blockHash
    const requestParamsBlockHash = {
        requestType: "blockHash",
        method: "eth_getBalance",
        params: [txInfo.sender, {"blockHash": txInfo.blockHash}]
    }
    
    doRequest(client, requestParamsBlockHash, txInfo.sender_balance_after);
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
        const checkResult = check(response, {
            'response result is not equal to real nonce': (r) => parseInt(r.result, 16) == expectedValue,
        });
        if (!checkResult) {
            console.log('Error in response of eth_getTransactionCount: ' + JSON.stringify(response));
            ethGetBalanceRequestErrorCounter.add(1);
        }
    } catch (e) {
        console.log('Error in eth_getTransactionCount: ' + e);
        ethGetBalanceErrorCounter.add(1);
    }
    ethGetBalanceRequestTime.add(new Date() - startTime);
    ethGetBalanceRequests.add(1);
}