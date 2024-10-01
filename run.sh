#!/usr/bin/env bash
# replace .pdf with .md in first argument
fpmd=$(echo $1 | sed 's/.pdf/.md/g')
# replace .pdf with .epub in first argument
ofepub=$(echo $1 | sed 's/.pdf/.epub/g')
#activate pythnon venv
source env/bin/activate
# set environment variables from .env
export $(cat .env | xargs)
# run conversion to markdown
python3 main.py $1 $fpmd
# convert markdown to epub
pandoc $fpmd -o $ofepub