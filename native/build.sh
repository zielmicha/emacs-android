#!/bin/bash

if [ "$RANDOM" = "" ]; then
    echo "Run this script with bash, not sh".
    exit 1
fi

if [ ! -d emacs-src/.git ]; then
    echo "Execute:"
    echo "git clone http://github.com/zielmicha/emacs.git emacs-src"
    exit 1
fi

check() {
    $* || exit
}

skip() {
    $* 2>/dev/null
}

trimout() {
    ($* 2>&1; echo $?>"$base/.success") | tee -a "$base/build.log" | (curr=0; while read line; do
        i=$[curr%7]
        [ $i = 0 ] && ch='|'
        [ $i = 1 ] && ch='/'
        [ $i = 2 ] && ch='-'
        [ $i = 3 ] && ch='\'
        [ $i = 4 ] && ch='/'
        [ $i = 5 ] && ch='-'
        [ $i = 6 ] && ch='\'
        printf "\b%s" $ch
        curr=$[curr+1]
    done)
    return $(cat "$base/.success"; rm "$base/.success")
}

die() {
    cd "$base"
    echo
    echo -e "${RED}Here is \`tail build.log\`:$NORMAL"
    tail build.log
    echo -e "${RED}Build failed. See build.log for details.$NORMAL" >&2
    exit 1
}

end_progress() {
    echo -e "\bdone"
}

NORMAL="\033[0m"
RED="\033[31;1m"
GREEN="\033[32;1m"
BLUE="\033[34;1m"
YELLOW="\033[33;1m"
WHITE="\033[37;1m"
AAA="\033[01;32m"


progress() {
    printf "$GREEN%s$NORMAL...  " "$1"
}

export base="$(pwd)"

(echo "started build"; date) >> build.log

skip mkdir -p build/emacs-src/lib
skip mkdir -p build/emacs-src/src
skip mkdir -p build/tinfo

progress '1) Building Android Emacs'

if [ ! -f android.mk ]; then
    trimout ./android-configure || die
fi
trimout ./android-make -j5 || die

end_progress

progress "2) Building Host Emacs"
echo

build_confirm_path=build/host/emacs_built
if [ -f $build_confirm_path ]; then
    echo "  already built - to rebuilt delete $build_confirm_path"
else
    progress "  copying Emacs source"

    trimout rm -rvf build/host
    mkdir build/host || die
    trimout git clone --progress emacs-src build/host/ || die
    cd build/host
    trimout git checkout de81159faf05814ed5e89c1addcee41b80f25c29 -- . || die
    end_progress

    progress "  running ./autogen.sh"
    trimout ./autogen.sh || die
    end_progress

    progress "  running ./configure"
    trimout ./configure || die
    end_progress

    progress "  running make -j4"
    trimout make -j4 || die
    end_progress

    touch $build_confirm_path
fi
