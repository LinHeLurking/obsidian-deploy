#!/bin/bash

DIR_ROOT=$(dirname -- "$( readlink -f -- "$0"; )")
cd $DIR_ROOT


if [[ -f "env.sh" ]]; then 
  source "env.sh"
fi

# activate venv if exsists and not in venv
if [[ "$VIRTUAL_ENV" == "" ]] && [[ -d "./venv" ]]; then 
  echo "Activating python venv"
  source "./venv/bin/activate"
fi
which python

# reset git submodule and apply patch 
git submodule deinit -f .
git submodule update --init --recursive 
cd $HUGO_SITE/themes/LoveIt 
git apply ../../../patch/theme.patch

cd $DIR_ROOT
echo "Removing old build"
rm -r "$HUGO_SITE/public/"
echo "Transpiling files from $VAULT to $HUGO_SITE/content"
python3 ./transpile.py $VAULT $HUGO_SITE && \
hugo -s $HUGO_SITE
