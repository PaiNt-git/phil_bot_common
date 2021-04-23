#!/bin/bash -e

SCRIPT=`readlink -f $0`
SCRIPTPATH=`dirname $SCRIPT`

PYTHON=$SCRIPTPATH/../venv/bin/python
PYTHONPATH=$SCRIPTPATH/../

PATH=$PATH

cd $SCRIPTPATH/../phil_bot

USER=pnu_sso

sudo -u $USER\
 PYTHONPATH=$PYTHONPATH\
 LD_LIBRARY_PATH=$LD_LIBRARY_PATH\
 PATH=$PATH\
 $PYTHON broadcaster.py $*