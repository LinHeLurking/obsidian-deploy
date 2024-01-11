#!/bin/bash

DIR_ROOT=$(dirname -- "$( readlink -f -- "$0"; )")
cd $DIR_ROOT

[[ -f "./env.sh" ]] && source "./env.sh"

# activate venv if exsists and not in venv
[[ "$VIRTUAL_ENV" == "" ]] && [[ -d "./venv" ]] && source "./venv/bin/activate"

python3 "./incremental_update_remote.py"