# android main
import terminal
import os
import pygame

def main():
    private = get_private_data_path()
    t = terminal.Terminal()
    pty_helper = private + '/pty-helper'
    os.chmod(pty_helper, 0o755)

    t.init_graphics()
    set_mode(t)
    t.init_subprocess(['/system/bin/sh'], pty_helper)

    while True:
        t.tick()

def get_private_data_path():
    public = os.path.dirname(os.path.abspath(__file__))
    return '/data/data/' + os.path.split(public)[1] + '/files'

def set_mode(term):
    term.surf = pygame.display.set_mode((0, 0))
    term.cols = term.surf.get_width() // term.char_w
    term.rows = term.surf.get_height() // term.char_h
