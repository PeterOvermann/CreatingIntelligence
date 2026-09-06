#!/bin/bash

# Install or update prettier globally, suppressing all output
npm install -g prettier > /dev/null 2>&1

# Execute
prettier --write testsuite.json --print-width 120