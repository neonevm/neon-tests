import exec from 'k6/execution';
import eth from 'k6/x/ethereum';
import {Counter, Trend} from 'k6/metrics';

import {BlockContractAddress, networkId, proxyUrl} from '../../utils/consts.js';
import {standardScenarioOptions} from '../../../options/options.js';
import {sendCallContractTransaction} from '../../utils/ethClient.js';
import {readUsersFromFile} from '../../utils/accounts.js'


const requestCounter = new Counter('send_block_contract_requests');
const contractErrorCounter = new Counter('block_contract_errors');
const receiptErrorCounter = new Counter('block_contract_errors_in_receipt');
const requestTimeTrend = new Trend('block_contract_request_time', true);

export const options = standardScenarioOptions;

const pathToContractData = '../../../contracts/BlockNumber/BlockNumber.abi';
const abi = open(pathToContractData);
const users = readUsersFromFile();


export default function restartTransactionsWithTimestampTest() {
    const vuID = exec.vu.idInTest
    const index = vuID - 1
    const senderAddress = users[index].sender_address;
    const senderPrivateKey = users[index].sender_key;

    const client = new eth.Client({
        url: proxyUrl,
        mnemonic: '',
        privateKey: senderPrivateKey,
        chainID: networkId,
    });

    sendCallContractTransaction({
        ethClient: client,
        contractAddress: BlockContractAddress,
        contractAbi: abi,
        senderAddress: senderAddress,
        functionName: "accrueInterest",
        receiptErrorCounter: receiptErrorCounter,
        contractErrorCounter: contractErrorCounter,
        requestTimeTrend: requestTimeTrend,
        requestCounter: requestCounter,
        prometheusLabels: {iterative: false},
        gasLimitMultiplier: 10,
    })

    sendCallContractTransaction({
        ethClient: client,
        contractAddress: BlockContractAddress,
        contractAbi: abi,
        senderAddress: senderAddress,
        functionName: "accrueInterestIterative",
        receiptErrorCounter: receiptErrorCounter,
        contractErrorCounter: contractErrorCounter,
        requestTimeTrend: requestTimeTrend,
        requestCounter: requestCounter,
        prometheusLabels: {iterative: true},
        gasLimitMultiplier: 10,
    })
}
