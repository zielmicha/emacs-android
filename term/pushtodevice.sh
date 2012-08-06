#!/bin/bash
for i in *.py; do
    adb shell rm /sdcard/com.zielm.emacs.debug/${i}o
    adb push $i /sdcard/com.zielm.emacs.debug/$i
done
