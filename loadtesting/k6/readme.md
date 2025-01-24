# How to: proxy and tracer load scenarios

Make sure your Golang version >= 1.19.

Make sure you have Golang bin path in PATH, otherwise
```bash
export PATH=$PATH:$(go env GOPATH)/bin
```

##
## Run performance test using clickfile:

First of all you need to run infra for monitoring:
go to the ./loadtesting/k6/monitoring folder and run
```bash
docker-compose -f compose.yml up -d --build
```
It is needed to include telegraf tool in the infrastructure. Install it if do not have one (```brew install telegraf``` or similar for your system)

run telegraf with config
```bash
telegraf --config telegraf.conf
```

Run needed scenario:
Install xk6 and build an executable file, tag is a neonlabsorg forked xk6-ethereum plugin tag, it can be a fixed version of a forked xk6-ethereum plugin or commit sha (ex. ```05e0ce5```)
```bash
./clickfile.py k6 build --tag 05e0ce5
```

To run load scenario:
```bash
./clickfile.py k6 run --network devnet --script ./loadtesting/k6/tests/sendNeon.test.js --users 100 --balance 200
```
Inside this command we compile and deploy contracts, prepare accounts with balances and then run load script.


To get more information about run parameters and its values:
```bash
./clickfile.py k6 --help
```

To monitor test metrics you should go to the default grafana host/port ```localhost:3000```. Default login/password: admin/admin. Open dashboard: ``` Neonlabs performance test```.

### Native commands to build and run k6:
Install k6
```bash
go install go.k6.io/xk6/cmd/xk6@latest
```
Build a k6 binary file with the following command, BUILD_TAG can be a fixed version of a forked xk6-ethereum plugin or commit sha (ex. ```05e0ce5```)
 ```bash
xk6 build --with github.com/szkiba/xk6-prometheus --with github.com/neonlabsorg/xk6-ethereum@${BUILD_TAG}
```
where: 

- github.com/szkiba/xk6-prometheus - a plugin for working with metrics

- neonlabsorg/xk6-ethereum - the ethereum plugin forked by neonlabsorg

Run test scenario:
```bash
./k6 run -o 'prometheus=namespace=k6' -e K6_USERS_NUMBER=100 -e K6_INITIAL_BALANCE=200 ./loadtesting/k6/tests/sendNeon.test.js
```
##
## Local test run with local version of the xk6-ethereum plugin
It is common approach to do some changes in the plugin and test it locally before pushing changes to github.
Pass the xk6-ethereum plugin repository path (on your local machine) as a parameter to the build command:
```bash
xk6 build --with github.com/szkiba/xk6-prometheus --with github.com/neonlabsorg/xk6-ethereum="<path_to_xk6_ethereum_plugin_repository>" 
```
Use an executable file builded with command above to run test scenario (see 'Run performance test using clickfile' or 'Native commands to build and run k6' sections).
```bash
./clickfile.py k6 run --network local --script ./loadtesting/k6/tests/sendErc20.test.js --users 10 --balance 200
```

##
## Scenario options
Standard single scenario settings:
```js
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
```
```executor: 'ramping-vus'``` -  VUs execute as many iterations as possible for a specified amount of time

```startVUs: 0``` - number of VUs to start the run with

```stages``` - an array of objects that specify the target number of VUs to ramp up or down to, in our case: number of VUs is increased from 0 to `usersNumber` value during 30 seconds, then `usersNumber` VUs execute the scenario during 1200 seconds

```gracefulRampDown: '60s'``` - time to wait for an already started iteration to finish before stopping it during a ramp down 

```noConnectionReuse: true``` - determines whether a connection is reused throughout different actions of the same virtual user and in the same iteration

##
## Tracer load test data preparation and run
To prepare data you have to use a script from ```./scripts/tracer_load_preparation/tracer_data_producer.py```.
Set envs before run
```
NETWORK
BANK_ACCOUNT_PRIVATE_KEY (if needed)
TRANSFERS
CONTRACT_CALLS
ITERATIVE_TXS 
```

```bash
python3 -m tracer_data_producer.py
```


This script will generate data for the tracer load test and put it to a ```loadtesting/k6/data/tracer_data.json``` file.

To run the standard tracer load scenario the clickfile run k6 command can be used:
```bash
./clickfile.py k6 run --network local --script loadtesting/k6/scenarios/tracerStandardLoad.js --users 10 --balance 200
```

A combined standard tracer scenario: ```loadtesting/k6/scenarios/tracerStandardLoad.js```.