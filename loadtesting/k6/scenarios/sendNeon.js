import { default as sendNeonTest } from '../tests/sendNeon.test.js';

// TODO: we can combine multiple scenarios here
export const options = {
    scenarios: {
        scriptSendNeonScenario: {
            exec: 'sendNeon',
            executor: 'constant-vus',
            vus: 100,
            duration: '1m',
        },
        // scriptSecondScenario: {
        //   exec: 'mySecondScenario',
        //   executor: 'constant-vus',
        //   vus,
        //   duration,
        // },
    },
};

export function sendNeon() {
    sendNeonTest();
}

// the second scenario can be added here
// export function secondScenario() {
//  secondScenario();
//}