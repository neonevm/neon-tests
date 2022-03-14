### Requirements
Python 3.6 or later, if you dont already have it. 
[Locust](https://docs.locust.io/en/stable/index.html) 2.8.3 or later.

## Quick Start

```bash

1. 
   cd /Users/user_name/NeonLabs/neon-tests/ 
   pip install -U locust==2.8.3 
   or 
   pip install -U -r ./deploy/requirements/prod.txt
2. export NEON_NETWORK=night-stand 
   or --network=night-stand as locust command line argument
   export NEON_CRED=/Users/user_name/neon-tests/envs.json 
   or --credentials=/Users/user_name/neon-tests/envs.json as locust command linee argument 
3. locust -f ./loadtesting/locustfile.py --headless --host=localhost -t 60 -u 10 -r 10 --logfile run.log
```

#### Environment Variables

Test configuration via environment variables settings:

- `NEON_NETWORK`
  Test environment name.

- `NEON_CRED`
  Absolute path to environment credentials file.


## Running the test and analyzing the results in the console without using the web interface 

##### Instant load method 
```bash

locust -f ./loadtesting/locustfile.py --headless --host=localhost -u 10 -r 10

-f             : Python module to import, e.g. '../other_test.py'. Either a .py file or a package directory.
                 Defaults to 'locustfile'
-u             : Peak number of concurrent Locust users. Primarily used together with --headless or
                 --autostart. Can be changed during a test by keyboard inputs w, W (spawn 1, 10 users) and
                 s, S (stop 1, 10 users)
-r             : Rate to spawn users at (users per second). Primarily used together with --headless or
                 --autostart
--headless     : Disable the web interface, and start the test immediately. Use -u and -t to control user
                 count and run time
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

