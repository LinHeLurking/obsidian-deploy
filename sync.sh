#!/bin/bash

DIR_ROOT=$(dirname -- "$( readlink -f -- "$0"; )")
cd $DIR_ROOT

[[ -f "./env.sh" ]] && source "./env.sh"

# activate venv if exists and not in venv
[[ "$VIRTUAL_ENV" == "" ]] && [[ -d "./venv" ]] && source "./venv/bin/activate"

python "./incremental_update_remote.py" "$@"
