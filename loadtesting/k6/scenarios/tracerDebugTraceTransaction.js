import { default as DebugTraceTransactionTest } from '../tests/tracer/traceTransaction/debugTraceTransactionSimple.test.js'
import { default as DebugTraceTransactionWithEventsTest } from '../tests/tracer/traceTransaction/debugTraceTransactionWithEvents.test.js'
import { default as DebugTraceIterativeTransactionTest } from '../tests/tracer/traceTransaction/debugTraceTransactionIterative.test.js'
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
