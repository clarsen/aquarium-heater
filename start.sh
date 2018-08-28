#!/bin/sh
cd `dirname $0`
pipenv run python -u monitor_temp.py
