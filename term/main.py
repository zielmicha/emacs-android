# android main
import terminal
import os
import pygame
import time
import android

keymap = {
    57: pygame.K_LALT,
    58: pygame.K_RALT,
    113: pygame.K_LCTRL,
    114: pygame.K_RCTRL,
}

def main():
    for k, v in keymap.items():
        print 'map', k, v
        android.map_key(k, v)
    private = get_private_data_path()
    t = terminal.Terminal()
    pty_helper = private + '/pty-helper'
    busybox = private + '/busybox'
    os.chmod(pty_helper, 0o755)
    os.chmod(busybox, 0o755)

    os.environ['BUSYBOX'] = busybox
    os.environ['PRIVATE'] = private
    os.environ['PUBLIC'] = os.path.dirname(os.path.abspath(__file__))

    t.init_graphics()
    set_mode(t)
    t.init_subprocess([busybox, 'sh', 'init.sh'], pty_helper)

    while True:
        t.tick()

def get_private_data_path():
    public = os.path.dirname(os.path.abspath(__file__))
    return '/data/data/' + os.path.split(public)[1] + '/files'

def set_mode(term):
    term.surf = pygame.display.set_mode((0, 0))
    term.cols = term.surf.get_width() // term.char_w
    term.rows = term.surf.get_height() // term.char_h
