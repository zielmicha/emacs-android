all: pty-helper pty-helper.android

pty-helper.android:
	arm-linux-androideabi-gcc pty-helper.c -o pty-helper.android

pty-helper: pty-helper.c
	gcc pty-helper.c -o pty-helper -lutil
