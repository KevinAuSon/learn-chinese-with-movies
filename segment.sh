#!/bin/sh

lang="pku"
files=$1
enc="UTF-8"
kBest="0"

BASEDIR=`dirname $0`
DATADIR=$BASEDIR/data
# LEXDIR=$DATADIR/lexicons
JAVACMD="java -mx2g -cp $BASEDIR/*: edu.stanford.nlp.ie.crf.CRFClassifier -sighanCorporaDict $DATADIR -textFiles $files -inputEncoding $enc -sighanPostProcessing true $ARGS"
DICTS=$DATADIR/dict-chris6.ser.gz
KBESTCMD=""

if [ $kBest != "0" ]; then
    KBESTCMD="-kBest $kBest"
fi

cd "stanford-segmenter";

if [ $lang = "ctb" ]; then
  $JAVACMD -loadClassifier $DATADIR/ctb.gz -serDictionary $DICTS $KBESTCMD
elif [ $lang = "pku" ]; then
  $JAVACMD -loadClassifier $DATADIR/pku.gz -serDictionary $DICTS $KBESTCMD
fi
