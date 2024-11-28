import { randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import { ethClient, sendNeon } from '../utils/ethClient.js';
import { standardScenarioOptions } from '../../options/options.js';
import { transferAmountRange } from './consts.js';
import { Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';
import exec from 'k6/execution';
import { check } from 'k6';

const sendNeonRequests = new Counter('send_neon_requests');
const sendNeonErrorCounter = new Counter('send_neon_errors');
const sendNeonErrorReceiptStatusCounter = new Counter('send_neon_errors_in_receipt');
const sendNeonRequestTime = new Trend('send_neon_request_time', true);

export const options = standardScenarioOptions;

const usersArray = new SharedArray('Users accounts', function () {
    const accounts = JSON.parse(open("../data/accounts.json"));
    let data = [];
    for (let i = 0; i < Object.keys(accounts).length; i++) {
        data[i] = accounts[i];
    }
    return data;
});


export default function sendNeonTest() {
    const vuID = exec.vu.idInTest
    const index = vuID % usersArray.length;

    const accountSenderAddress = usersArray[index].sender_address;
    const accountSenderPrivateKey = usersArray[index].sender_key;
    const accountReceiverAddress = usersArray[index].receiver_address;

    const client = ethClient(accountSenderPrivateKey);

    const startTime = new Date();

    try {
        let receipt = sendNeon(
            client,
            accountSenderAddress,
            accountReceiverAddress,
            randomItem(transferAmountRange)
        );
        const checkResult = check(receipt, {
            'receipt status is 1': (r) => r.status === 1,
        });
        if (!checkResult) {
            console.log('Error send Neon in receipt: ' + receipt);
            sendNeonErrorReceiptStatusCounter.add(1);
        }
    } catch (e) {
        console.log('Error sendNeon: ' + e);
        sendNeonErrorCounter.add(1);
    }
    sendNeonRequestTime.add(new Date() - startTime);
    sendNeonRequests.add(1);
}
