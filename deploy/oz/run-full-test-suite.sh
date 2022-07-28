#!/bin/bash
# "Cleanup previous allure report"
rm -rf /opt/allure-report
cd /opt

# "Run OpenZeppelin tests"
python3 clickfile.py run oz --dump=${DUMP_ENVS} --network=${NETWORK_NAME} --jobs=${FTS_JOBS_NUMBER} --amount=${REQUEST_AMOUNT} --users=${FTS_USERS_NUMBER}

# "Print OpenZeppelin report"
python3 clickfile.py ozreport

# "Archive report"
ALLURE_RESULT_DIR=/opt/allure-results
if [[ -d "$ALLURE_RESULT_DIR" ]]; then
    tar -czvf /opt/allure-reports.tar.gz $ALLURE_RESULT_DIR
fi

