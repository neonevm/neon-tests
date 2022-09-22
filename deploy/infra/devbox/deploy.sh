#!/bin/bash

function printColor () {
        echo "$(tput setaf $1) $2 $(tput sgr0)"
}

function printRed () {
    printColor 1 "$1"
}

function printGreen () {
    printColor 2 "$1"
}

function printYellow () {
    printColor 3 "$1"
}

packages="web3"


if [[ ! $(tfenv list) ]] &>/dev/null; then
    printYellow "installed 'terraform' not found, trying to install the 'latest' version!"
    if [[  $(tfenv list-remote) ]] &>/dev/null; then
        tfenv install && tfenv use latest
    else
        printRed "it is not possible to get a list of available terraform versions,
 try using vpn and restart the command 'tfenv install && tfenv use latest'"
    fi
fi

if [[ ! $(pip list | grep $packages) ]] &>/dev/null; then
    printYellow "no 'web3' package found, trying to update dependencies"
    pip install -U -r ${SOURCE_DIR}/deploy/requirements/nodeps.txt &>/dev/null
fi

