#!/bin/bash -ex

source ~/env/bin/activate
# webapp/entry.js must be ES5-compatible; we don't currently preprocess it.
node_modules/.bin/eslint --no-eslintrc --parser-options=ecmaVersion:5 -f junit webapp/entry.js > entry_eslint.junit.xml
make test-full
