## Requirements
Python 3.6 or later, if you dont already have it. 
[Locust](https://docs.locust.io/en/stable/index.html) 2.8.3 or later.

## Quick Start

```bash

1. cd /Users/user_name/NeonLabs/neon-tests/ 
   pip install -U locust==2.8.3 
   or 
   pip install -U -r ./deploy/requirements/prod.txt
   or
   ./clickfile.py requirements
2. export NEON_CRED=envs.json 
   or --credentials=envs.json as locust command line argument 
3. locust -f ./loadtesting/locustfile.py --headless --host=night-stand -t 60 -u 10 -r 10 --logfile run.log
```

## Environment Variables

Test configuration via environment variables settings:

- `NEON_TRACING_URL`
  Endpoint to Neon-RPC. Neon-RPC is a single RPC entrypoint to Neon-EVM (specified for tracing tests). 
  The function of this service is so route requests between Tracer API and Neon Proxy services. 
  Used only in tracer API cases.
-  `SAVE_TRANSACTIONS` Save all neon transactions and their solana transactions to "transactions-{id}.json" files


## Running the test and analyzing the results in the console without using the web interface 

##### Instant load method without locust web interface 
```bash
locust -f ./loadtesting/{test_group}/locustfile.py --headless --host=night-stand -u 10 -r 10
```

```bash
Options:
-f             : Python module to import, e.g. '../other_test.py'. Either a .py file or a package directory.
                 Defaults to 'locustfile'
-u             : Peak number of concurrent Locust users. Primarily used together with --headless or
                 --autostart. Can be changed during a test by keyboard inputs w, W (spawn 1, 10 users) and
                 s, S (stop 1, 10 users)
-r             : Rate to spawn users at (users per second). Primarily used together with --headless or
                 --autostart
--headless     : Disable the web interface, and start the test immediately. Use -u and -t to control user
                 count and run time
--host or -h   : Test environment name (night-stand | devnet | local)
```

### Running the test with clickfile
```bash
./clickfile.py locust --help

Commands:
  prepare  Run preparation stage for `tracer api` performance test
  run      Run `neon` pipeline performance test
```

```bash
Usage: ./clickfile.py locust [OPTIONS]

  Run `neon` pipeline performance test

Options:
  -f, --locustfile TEXT           Python module to import. It is sub-folder and
                                  file name.  [default:
                                  loadtesting/{test_group}/locustfile.py]
                                  Choices between ["proxy", "synthetic", "tracerapi"]
  -h, --host [night-stand|release-stand|devnet|local]
                                  In which stand run tests.  [default: night-
                                  stand]
  -u, --users INTEGER             Peak number of concurrent Locust users.
                                  [default: 10]
  -r, --spawn-rate INTEGER        Rate to spawn users at (users per second)
                                  [default: 1]
  -t, --run-time INTEGER          Stop after the specified amount of time,
                                  e.g. (300s, 20m, 3h, 1h30m, etc.). Only used
                                  together without Locust Web UI. [default:
                                  always run]
  -T, --tag TEXT                  tag to include in the test, so only tasks
                                  with any matching tags will be executed
  --web-ui / -w, --headless       Enable the web interface. If UI is enabled,
                                  go to http://0.0.0.0:8089/ [default: `Web UI
                                  is enabled`]
  --help                          Show this message and exit.
```

```bash
Usage: ./clickfile.py locust prepare [OPTIONS]

  Run preparation stage for `tracer api` performance test

Options:
  -c, --credentials TEXT    Relative path to credentials. Default repo
                            root/envs.json
  -h, --host TEXT           In which stand run tests.  [default: night-stand]
  -u, --users INTEGER       Peak number of concurrent Locust users.  [default:
                            50]
  -r, --spawn-rate INTEGER  Rate to spawn users at (users per second)
                            [default: 1]
  -t, --run-time INTEGER    Stop after the specified amount of time, e.g.
                            (300s, 20m, 3h, 1h30m, etc.). Only used together
                            without Locust Web UI. [default: always run]
  -T, --tag TEXT            tag to include in the test, so only tasks with any
                            matching tags will be executed
  --help                    Show this message and exit.
```

##### Running test with Web UI
```bash
./clickfile.py locust
then go to http://0.0.0.0:8089/

[2022-03-17 16:21:43,161] local/INFO/locust.main: Starting web interface at http://0.0.0.0:8089 (accepting connections from all network interfaces)
[2022-03-17 16:21:43,175] local/INFO/locust.main: Starting Locust 2.8.3

for exit press Ctrl+C

for more options use --help
```

##### Running test without Web UI (headless mode)
```bash
./clickfile.py locust --headless | -w 
Test will start immediately. Use -u and -t to control user count and run time

for exit press Ctrl+C

for more options use --help
```

##### Statistics metrics 
```bash

 Name                                   # reqs      # fails  |     Avg     Min     Max  Median  |   req/s failures/s
---------------------------------------------------------------------------------------------------------------------
 `send neon`                                 1     0(0.00%)  |    1596    1596    1596    1596  |    0.00    0.00
---------------------------------------------------------------------------------------------------------------------
 Aggregated                                  1     0(0.00%)  |    1596    1596    1596    1596  |    0.00    0.00

 - req        : total tasks
 - fails      : total number of errorsк
 - Avg        : average task execution time in ms
 - Min        : minimum task execution time in ms
 - Max        : maximum task execution time in ms
 - Median     : median in ms
 - req/s      : tasks per second
 - failures/s : failed requests per second

```

