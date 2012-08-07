DESCR="Uploads packaged resources and emacs executable using SCP (scp file \$1/file)"
if [ "$1" = "" ]; then
    echo "Usage: ./upload.sh user@host:path"
    echo $DESCR
    exit 1
fi

scp build/lisp.tlzma $1/lisp.tlzma
scp build/terminfo.tlzma $1/terminfo.tlzma
scp build/etc.tlzma $1/etc.tlzma
lzma < build/emacs.bin > build/emacs.lzma
scp build/emacs.lzma $1/emacs.lzma
