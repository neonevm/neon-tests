import { default as DebugTraceTransactionTest } from '../tests/tracer/traceTransaction/debugTraceTransactionSimple.test.js'
import { default as DebugTraceTransactionWithEventsTest } from '../tests/tracer/traceTransaction/debugTraceTransactionWithEvents.test.js'
import { default as DebugTraceIterativeTransactionTest } from '../tests/tracer/traceTransaction/debugTraceTransactionIterative.test.js'
import { default as EthCallTest } from '../tests/tracer/ethCall.test.js';
import { default as EthGetBalanceTest } from '../tests/tracer/ethGetBalance.test.js';
import { default as EthGetTransactionCountTest } from '../tests/tracer/ethGetTransactionCount.test.js';
import { default as EthGetStorageAtTest } from '../tests/tracer/ethGetStorageAt.test.js';
import { usersNumber } from "../tests/utils/consts.js";

export const options = {
    scenarios: {
        DebugTraceTransaction: {
            exec: 'DebugTraceTransaction',
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '20s', target: usersNumber },
                { duration: '20m', target: usersNumber },
            ],
            gracefulRampDown: '60s',
        },
        DebugTraceTransactionWithEvents: {
            exec: 'DebugTraceTransactionWithEvents',
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '20s', target: usersNumber },
                { duration: '20m', target: usersNumber },
            ],
            gracefulRampDown: '60s',
        },
        DebugTraceIterativeTransaction: {
            exec: 'DebugTraceIterativeTransaction',
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '20s', target: usersNumber },
                { duration: '20m', target: usersNumber },
            ],
            gracefulRampDown: '60s',
        },
        EthCall: {
            exec: 'EthCall',
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '20s', target: usersNumber },
                { duration: '20m', target: usersNumber },
            ],
            gracefulRampDown: '60s',
        },
        EthGetBalance: {
            exec: 'EthGetBalance',
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '20s', target: usersNumber },
                { duration: '20m', target: usersNumber },
            ],
            gracefulRampDown: '60s',
        },
        EthGetTransactionCount: {
            exec: 'EthGetTransactionCount',
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '20s', target: usersNumber },
                { duration: '20m', target: usersNumber },
            ],
            gracefulRampDown: '60s',
        },
        EthGetStorageAt: {
            exec: 'EthGetStorageAt',
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '20s', target: usersNumber },
                { duration: '20m', target: usersNumber },
            ],
            gracefulRampDown: '60s',
        },
    },
    noConnectionReuse: true,
};

export function DebugTraceTransaction() {
    DebugTraceTransactionTest();
}

export function DebugTraceTransactionWithEvents() {
    DebugTraceTransactionWithEventsTest();
}

export function DebugTraceIterativeTransaction() {
    DebugTraceIterativeTransactionTest();
}

export function EthCall() {
    EthCallTest();
}

export function EthGetBalance() {
    EthGetBalanceTest();
}

export function EthGetTransactionCount() {
    EthGetTransactionCountTest();
}

export function EthGetStorageAt() {
    EthGetStorageAtTest();
}