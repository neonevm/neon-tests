#!/bin/bash

path=$HOME/.cache/hardhat-nodejs/compilers-v2/linux-amd64/
attempts=1

while [ $attempts -le 10 ]; do
  echo "Attempt $attempts"

  npx hardhat compile
  wait $!

  file_count=$(ls -1 $path | wc -l)

  if [ $file_count -ge 2 ]; then
    echo "Hardhat compiled files successfully"
    exit 0
  else
    echo "Looks like hardhat didn't download compiler, retry"
    sleep 15
    attempts=$((attempts+1))
  fi
done

echo "Failed after 10 attempts"
exit 1
