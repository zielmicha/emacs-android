This is Emacs port for Android.

It works, but for now you have to run it through ConnectBot.

Building
=============

    cd native
    git clone http://github.com/zielmicha/emacs.git emacs-src
    ./build.sh

Installation
=============

   git clone https://github.com/zielmicha/emacs-android-app.git
   cd emacs-android-app
   ant debug install

Setting up mirror
============

By default Android application downloads pre-build Emacs from emacs.zielm.com.
If you want to use your own build:

1. Setup HTTP server with SSH access.
2. `cd native; ./upload.sh username@host:path`
3. Download http://emacs.zielm.com/data/busyboxrc.sh to the same directory.
4. Change MIRROR=... in busyboxrc.sh to your server URL.
