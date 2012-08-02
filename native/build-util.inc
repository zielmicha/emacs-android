
if [ "$RANDOM" = "" ]; then
    echo "Run this script with bash, not sh".
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
