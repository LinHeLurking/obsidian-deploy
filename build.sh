#!/bin/bash

DIR_ROOT=$(dirname -- "$( readlink -f -- "$0"; )")
cd $DIR_ROOT

if [[ -z "$VAULT" ]] || [[ -z "$HUGO_SITE" ]]; then 
  if [[ -f "env.sh" ]];then 
    . "env.sh"
  else
    echo "Pass `VAULT` and `HUGO_SITE` through environment variables!"
    exit 
  fi
fi 

# reset git submodule and apply patch 
git submodule deinit -f .
git submodule update --init --recursive 
cd $HUGO_SITE/themes/LoveIt 
git apply ../../../theme_patch.1

cd $DIR_ROOT
echo "Removing old build"
rm -r "$HUGO_SITE/public/"
echo "Transpiling files from $VAULT to $HUGO_SITE/content"
python ./transpile.py $VAULT $HUGO_SITE
hugo -s $HUGO_SITE
