
get_key_code() {
    printf "\033[?10000020l"
}

export PATH=$PRIVATE:$PATH
export TERMINFO=/sdcard/emacs/terminfo

echo "Hello!"
echo "Press Z to continue."

while [ true ]; do
    echo "Keycode:"
    get_key_code
    read keycode name
    if [ "$name" = K_z ]; then
        $BUSYBOX sh
        exit
    fi
done
