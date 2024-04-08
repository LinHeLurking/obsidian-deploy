#!/bin/bash

DIR_ROOT=$(dirname -- "$( readlink -f -- "$0"; )")
cd $DIR_ROOT


if [[ -f "env.sh" ]]; then 
  source "env.sh"
fi

# activate venv if exists and not in venv
if [[ "$VIRTUAL_ENV" == "" ]] && [[ -d "./venv" ]]; then 
  echo "Activating python venv"
  source "./venv/bin/activate"
fi
echo "Selecting $(which python)"

if [[ -z "$RAW_VAULT" ]]; then 
  echo "No vault dir! Set RAW_VAULT environment variable!"
  exit 1
fi 
if [[ -z "$HUGO_SITE" ]]; then 
  echo "No hugo site dir! Set HUGO_SITE environment variable!"
  exit 1
fi 

if [[ ! -d "$DIR_ROOT/tmp" ]]; then 
  mkdir -p "$DIR_ROOT/tmp/" 
fi 
rm -r "$DIR_ROOT/tmp"
TMP_VAULT="$DIR_ROOT/tmp"
echo "copy from $RAW_VAULT/blog/ to $TMP_VAULT/"
cp -r "$RAW_VAULT/blog" "$TMP_VAULT/"

# reset git submodule and apply patch 
git submodule deinit -f .
git submodule update --init --recursive 
cd $HUGO_SITE/themes/LoveIt 
git apply ../../../patch/theme.patch

cd $DIR_ROOT
echo "Removing old build"
rm -r "$HUGO_SITE/public/"
echo "Transpiling files from $RAW_VAULT to $HUGO_SITE/content"
python ./transpile.py $TMP_VAULT $HUGO_SITE && \
hugo -s $HUGO_SITE
