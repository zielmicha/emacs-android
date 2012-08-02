#!/bin/bash

source build-util.inc || exit 1

if [ ! -d emacs-src/.git ]; then
    echo "Execute:"
    echo "git clone http://github.com/zielmicha/emacs.git emacs-src"
    exit 1
fi

export base="$(pwd)"

(echo "started build"; date) >> build.log

skip mkdir -p build/emacs-src/lib
skip mkdir -p build/emacs-src/src
skip mkdir -p build/tinfo

echo "Building Emacs for Android."
echo " * more detailed log: build.log"
echo " * to start from begining remove build/ and android.mk"
echo

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
    echo "  already built - to rebuild delete $build_confirm_path"
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

    cd ../..

    touch $build_confirm_path
fi

progress "3) Finishing"
echo

if [ ! -f "build/busybox-arm" ]; then
    progress "  downloading BusyBox binary"
    trimout wget --progress=dot http://busybox.net/downloads/binaries/1.19.0/busybox-armv5l -o build/busybox-arm || die
    end_progress
else
    echo "  BusyBox binary aleardy downloaded"
fi

progress "  packaging Lisp modules"
cd build/host || die
trimout tar cvzf ../lisp.tgz lisp || die
end_progress
cd ../..

progress "  packaging etc"
cd emacs-src || die
trimout tar cvzf ../build/etc.tgz etc || die
end_progress
cd ..

progress "  packaging terminfo"
trimout tar czvf build/terminfo.tgz terminfo || doe
end_progress
