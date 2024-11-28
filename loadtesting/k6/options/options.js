import { usersNumber } from "../tests/utils/consts.js";

export const standardScenarioOptions = {
    scenarios: {
        standardScenario: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: usersNumber },
                { duration: '1200s', target: usersNumber },
            ],
            gracefulRampDown: '60s',
        },
    },
    noConnectionReuse: true,
};