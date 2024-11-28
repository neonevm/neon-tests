import { ethClient, sendErc20ViaTransferFunction } from '../utils/ethClient.js';
import { randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import { transferAmountRange } from '../utils/consts.js';
import { standardScenarioOptions } from '../../options/options.js';
import { Trend, Counter } from 'k6/metrics';
import { check } from 'k6';
import { SharedArray } from 'k6/data';
import exec from 'k6/execution';

const sendErc20Requests = new Counter('send_erc20_requests');
const sendErc20ErrorCounter = new Counter('send_erc20_errors');
const sendErc20ErrorReceiptStatusCounter = new Counter('send_erc20_errors_in_receipt');
const sendErc20RequestTime = new Trend('send_erc20_request_time', true);

export const options = standardScenarioOptions;
const pathToContractData = '../contracts/ERC20/ERC20';
const abi = JSON.parse(open(pathToContractData + '.abi'));

const usersArray = new SharedArray('Users accounts', function () {
    const accounts = JSON.parse(open("../data/accounts.json"));
    let data = [];
    for (let i = 0; i < Object.keys(accounts).length; i++) {
        data[i] = accounts[i];
    }
    return data;
});

export default function sendErc20Test() {
    const vuID = exec.vu.idInTest
    const index = vuID % usersArray.length;

    const accountSenderAddress = usersArray[index].sender_address;
    const accountSenderPrivateKey = usersArray[index].sender_key;
    const accountReceiverAddress = usersArray[index].receiver_address;
    const client = ethClient(accountSenderPrivateKey);

    const startTime = new Date();

    try {
        const receipt = sendErc20ViaTransferFunction(
            client,
            JSON.stringify(abi),
            { "address": accountSenderAddress, "key": accountSenderPrivateKey },
            accountReceiverAddress,
            randomItem(transferAmountRange)
        );
        const checkResult = check(receipt, {
            'receipt status is 1': (r) => r.status === 1,
        });
        if (!checkResult) {
            console.log('Error sendErc20 in receipt: ' + receipt);
            sendErc20ErrorReceiptStatusCounter.add(1);
        }
    } catch (e) {
        console.log('Error sendErc20: ' + e);
        sendErc20ErrorCounter.add(1);
    }
    sendErc20RequestTime.add(new Date() - startTime);
    sendErc20Requests.add(1);
}