import { sleep } from 'k6';

let ENVIRONMENT = {};
ENVIRONMENT.execution = "local";
if (__ENV.EXECUTION) {
  ENVIRONMENT.execution = __ENV.EXECUTION;
}

ENVIRONMENT.optionsSet = "load";
if  (__ENV.OPTIONS_SET) {
  ENVIRONMENT.optionsSet = `.${__ENV.OPTIONS_SET}`;
}

import { sendNeon } from './tests/sendNeon.test.js';
let TESTS = [ ...sendNeon ];

let optionsFile = `./env/options.json`;
export let options = JSON.parse(open(optionsFile));

//TO DO: add basic scenario here