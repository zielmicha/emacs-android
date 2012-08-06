#!/bin/bash

DEF_PYDIST=~/apps/pygame-package-0.9.3

if [ "$PYDIST" = "" ]; then
    PYDIST=$DEF_PYDIST
fi

if [ ! -d "$PYDIST" ]; then
    echo "Cannot find Pygame Subset for Android distribution under $PYDIST."
    echo "Point it with environment varible \$PYDIST."
    exit 1
fi

if [ ! -f "$PYDIST/build.py" ]; then
    echo "$PYDIST is not Python for Android distribution."
    echo "(Expected build.py file)"
    exit 1
fi

if [ "$BUILD_ACTION" = "" ]; then
    BUILD_ACTION=debug
fi

mkdir build 2> /dev/null

mkdir build/public 2> /dev/null
mkdir build/private 2> /dev/null
mkdir build/apk 2> /dev/null

cp *.py *.ttf build/public || exit 1
cp  scripts/* build/public || exit 1
make pty-helper.android || exit 1
cp pty-helper.android build/private/pty-helper || exit 1
cp ../native/build/busybox-arm build/private/busybox || exit 1

cp -r $PYDIST build/pygame || exit 1
cp build.xml.template build/pygame/templates/build.xml || exit 1

pwd=$PWD
cd build/pygame

./build.py \
    --package com.zielm.emacs.debug \
    --name "EmacsD" --version 1.0.0 \
    --numeric-version 1000 \
    --dir $pwd/build/public \
    --private $pwd/build/private \
    $BUILD_ACTION \
    || exit 1

cd ../..

mv build/pygame/bin/EmacsD-1.0.0-debug.apk build/apk/ || exit 1

if [ "$1" = "install" ]; then
    adb install -r build/apk/EmacsD-1.0.0-debug.apk || exit 1
fi
