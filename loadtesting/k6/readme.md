# How to build a k6 bin

Make sure your Golang version >= 1.19.

Make sure you have Golang bin path in PATH, otherwise
```bash
export PATH=$PATH:$(go env GOPATH)/bin
```


## Run performance test using clickfile:
Install xk6 and build exe file, tag is a neonlabsorg forked xk6-ethereum plugin tag, it can be a fixed version of a forked xk6-ethereum plugin or commit sha (ex. ```05e0ce5```)
```bash
./clickfile.py k6 build --tag 05e0ce5
```

Run load scenario:
```bash
./clickfile.py k6 run --network local --script ./loadtesting/k6/tests/sendNeon.test.js
```


## Native commands to run load tests:
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



## Run infrastructure
go to the monitoring folder and run
```bash
docker-compose -f compose.yml up -d --build
```
It is needed to include telegraf tool in the infrastructure. Install it if do not have one (```brew install telegraf``` or similar for your system)

run telegraf with config
```bash
telegraf --config telegraf.conf
```
## Run load test
To run tests go to the repo k6
```bash
./k6 run ./scenarios/sendNeon.test.js
```
## Monitoring
To monitor your test run go to the default grafana host/port ```localhost:3000```. Open dashboard: ``` Neonlabs performance test```.