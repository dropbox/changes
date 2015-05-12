#!/bin/bash -eux

PATH=`pwd`/env/bin:$PATH make test-full
