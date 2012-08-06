#!/usr/bin/python
import pygame
import subprocess
import sys
import select
import os
import time
import StringIO
import codecs

pygame_reverse = dict( (v, k) for k, v in pygame.__dict__.items() if k.startswith('K_') )

class Terminal:
    def __init__(self):
        self.in_buff = ''
        self.out_buff = ''
        self.surf = None
        self.cols = 160
        self.rows = 40
        self.char_h = 17
        self.char_w = self.char_h * 14 // 20
        self.screen = Screen(self.rows, self.cols, self.write)

        self.is_alt = False
        self.is_ctrl = False
        self.is_shift = False

    def main(self, args, ptyhelper='./pty-helper'):
        self.init_subprocess(args, ptyhelper)
        self.init_graphics()
        self.init_window()
        while True:
            self.tick()

    def init_graphics(self):
        pygame.init()
        pygame.key.set_repeat(100, 50)
        self.font = pygame.font.Font('FreeMono.ttf', self.char_h - 1)

    def init_window(self):
        self.surf = pygame.display.set_mode((self.cols * self.char_w, self.rows * self.char_h))

    def init_subprocess(self, args, ptyhelper):
        os.environ['COLS'] = str(self.cols)
        os.environ['ROWS'] = str(self.rows)
        os.environ['TERM'] = 'vt100'
        process = subprocess.Popen([ptyhelper] + args,
                                   stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE)
        self.stdin_fd = process.stdin.fileno()
        self.stdout_fd = process.stdout.fileno()

    def tick(self):
        self.tick_stream()
        self.tick_term()
        self.tick_window()

    def tick_stream(self):
        start = time.time()
        in_buff = [self.in_buff]
        while True:
            time_left = 0.02 - (time.time() - start)
            if time_left < 0:
                break
            r, w, x = select.select([self.stdout_fd],
                                    [self.stdin_fd] if self.out_buff else [],
                                    [self.stdout_fd, self.stdin_fd],
                                    max(0, time_left))

            if x:
                raise SystemExit

            if r:
                data = os.read(self.stdout_fd, 1)
                if not data:
                    raise SystemExit
                in_buff.append(data)

            if w:
                os.write(self.stdin_fd, self.out_buff)
                self.out_buff = ''

        self.in_buff = ''.join(in_buff)

    def tick_term(self):
        if self.in_buff:
            self.in_buff = self.screen.add(self.in_buff)

    def tick_window(self):
        #self.screen.lines_updated
        if len(self.screen.lines_updated) > 5:
            print 'many lines updated'
        for y in self.screen.lines_updated:
            row = self.screen._data[y]
            for x, char in enumerate(row):
                bg_color = get_color(char.bg)
                surf = self.font.render(char.ch, True,
                                        get_color(char.fg, char.bold),
                                        bg_color)
                self.surf.fill(bg_color, (self.char_w * x, self.char_h * y, self.char_w, self.char_h))
                self.surf.blit(surf, (self.char_w * x, self.char_h * y))

        self.screen.lines_updated = set([self.screen.y])

        cursor_color = self.screen._data[self.screen.y][self.screen.x].fg

        pygame.draw.rect(self.surf,
                         get_color(cursor_color),
                         (self.char_w * self.screen.x, self.char_h * self.screen.y,
                          self.char_w, self.char_h),
                         1)

        for ev in pygame.event.get():
            if ev.type == pygame.KEYDOWN:
                self.handle_modifier(ev.key, True)
                self.handle_key(ev)
            elif ev.type == pygame.KEYUP:
                self.handle_modifier(ev.key, False)
        pygame.display.flip()

    def handle_key(self, ev):
        if self.screen.get_key_code_mode:
            self.write('%d %s\n' % (ev.key, pygame_reverse.get(ev.key, 'unknown')))
            self.screen.get_key_code_mode = False
            return

        ALPHA = 'abcdefghijklmnopqrstuwvwxyz'
        ALPHA_MAPPING = dict( (getattr(pygame, 'K_' + v), v) for v in ALPHA )
        NUMBERS  = '1234567890'
        NUMBERS_MAPPING = dict( (getattr(pygame, 'K_' + v), v) for v in NUMBERS )
        NUMSHIFT = '!@#$%^&*()'
        e = '\x1b'
        app = 'O' if self.screen.app_mode else '['
        MAPPING = {pygame.K_BACKSPACE: '\x7f',
                   pygame.K_RETURN: '\r',
                   pygame.K_UP: e + app + 'A',
                   pygame.K_DOWN: e + app + 'B',
                   pygame.K_RIGHT: e + app + 'C',
                   pygame.K_LEFT: e + app + 'D',
                   pygame.K_PAGEUP: e + '[5~',
                   pygame.K_PAGEDOWN: e + '[6~',
                   pygame.K_END: e + 'OF',
                   pygame.K_HOME: e + 'OH',
                   pygame.K_TAB: '\t',
                   pygame.K_SPACE: ' ',
                   pygame.K_SLASH: ('/', '?'),
                   pygame.K_BACKSLASH: ('\\', '|'),
                   pygame.K_PERIOD: ('.', '>'),
                   pygame.K_COMMA: (',', '<'),
                   pygame.K_KP_MINUS: ('-', '_'),
                   pygame.K_MINUS: ('-', '_'),
                   pygame.K_EQUALS: ('=', '+'),
                   pygame.K_SEMICOLON: (';', ':'),
                   pygame.K_QUOTE: ('\'', '"'),
                   pygame.K_LEFTBRACKET: ('[', '{'),
                   pygame.K_RIGHTBRACKET: (']', '}'),
                   }

        if ev.key in ALPHA_MAPPING:
            ch = ALPHA_MAPPING[ev.key]

            if self.is_ctrl:
                self.write(chr(ord(ch) - 0x60))
            elif self.is_shift:
                self.write(ch.upper())
            elif self.is_alt:
                self.write('\x1b' + ch)
            else:
                self.write(ch)

        elif ev.key in NUMBERS_MAPPING:
            ch = NUMBERS_MAPPING[ev.key]
            if self.is_shift:
                self.write(NUMSHIFT[NUMBERS.index(ch)])
            else:
                self.write(ch)

        elif ev.key in MAPPING:
            thing = MAPPING[ev.key]
            if type(thing) == tuple:
                ch = thing[1] if self.is_shift else thing[0]
            else:
                ch = thing
            self.write(ch)

        #elif ev.unicode:
        #    self.write(ev.unicode.encode('utf8'))

    def handle_modifier(self, keycode, state):
        if keycode in (pygame.K_RALT, pygame.K_LALT):
            self.is_alt = state
        elif keycode in (pygame.K_RCTRL, pygame.K_LCTRL):
            self.is_ctrl = state
        elif keycode in (pygame.K_RSHIFT, pygame.K_LSHIFT):
            self.is_shift = state
        else:
            return

    def write(self, w):
        print time.time(), 'send', repr(w)
        self.out_buff += w

class Screen:
    def __init__(self, rows, cols, write_callback):
        self.rows = rows
        self.cols = cols
        self.x = 0
        self.y = 0
        self.saved_pos = (0, 0)
        self.scroll_start = 0
        self.scroll_end = self.rows - 1
        self.decoder = codecs.getincrementaldecoder('utf8')('replace')
        self._data = [
            [ Character() for i in xrange(self.cols) ] for i in xrange(self.rows) ]
        self.style = Character()
        self.app_mode = False
        self.get_key_code_mode = False
        self.write_callback = write_callback
        self.lines_updated = set()

    def add(self, data):
        reader = StringReader(data)
        try:
            while True:
                try:
                    self._handle(reader)
                except ValueError as err:
                    print >>sys.stderr, err
                print time.time(), 'put', repr(reader.s[reader._breakpoint:reader.i])
                reader.put_breakpoint()
        except StopIteration:
            pass
        self._normalize()
        return reader.get_rest()

    def _handle(self, r):
        ch = r.next()
        if ch == '\n':
            self.y += 1
        elif ch == '\r':
            self.x = 0
        elif ch == '\b':
            self.x -= 1
        elif ch == '\a':
            self.ring()
        elif ch == '\t':
            if self.x % 8 == 0:
                self.x += 1
            self.x = (self.x // 8) * 8 + 8
        elif ch == '\v':
            print 'vertical tab is not supported'
        elif ch == '\x1B':
            ch = r.next()
            if ch == '[':
                self._handle_escape(r)
            elif ch in ')(':
                r.next() # set font - not supported
            elif ch == 'H':
                # reset
                self.x, self.y = 0, 0
                self.style.copy_style(Character())
            elif ch == 'M':
                self.scroll(n=-1)
            elif ch == 'D':
                self.scroll(n=1)
            elif ch in ('=', '>'):
                pass # set alternate/numeric keypad
            else:
                print >>sys.stderr, 'unknow escape', repr(ch)
        elif ch in ('\x0f', '\0'):
            pass # skip?
        else:
            data = self.decoder.decode(ch)

            for ch in data:
                self.append(ch)

    def _handle_escape(self, r):
        ch, data = self._read_escape(r)
        if ch == 'A':
            n = _int(data)
            self.y -= n
        elif ch == 'B':
            n = _int(data)
            self.y += n
        elif ch == 'C':
            n = _int(data)
            self.x += n
        elif ch == 'D' or ch == 'd':
            n = _int(data)
            self.x += n
        elif ch == 'E':
            n = _int(data)
            self.y += n
            self.x = 0
        elif ch == 'F':
            n = _int(data)
            self.y -= n
            self.x = 0
        elif ch == 'G':
            n = _int(data)
            self.y = n
        elif ch == 'H' or ch == 'f':
            if ';' not in data: data += ';'
            a, b = data.split(';', 1)
            self.x = _int(b) - 1
            self.y = _int(a) - 1
            self.lines_updated.add(self.y)
        elif ch == 'J':
            n = _int(data, default=0)
            self.clear(option=n, line=False)
        elif ch == 'K':
            n = _int(data, default=0)
            self.clear(option=n, line=True)
        elif ch == 'S':
            n = _int(data)
            self.scroll(n)
        elif ch == 'T':
            n = _int(data)
            self.scroll(-n)
        elif ch == 'm':
            for code in data.split(';'):
                self.set_sgr(code)
        elif ch == 'n':
            # report position
            self.write_callback('\x1b[%d;%dR' % (self.y + 1, self.x + 1))
        elif ch == 's':
            self.saved_pos = (self.x, self.y)
        elif ch == 'u':
            self.x, self.y = self.saved_pos
        # non-ansi
        elif ch == 'l':
            if data == '7':
                print 'disable wrap'
            elif data == '?1':
                self.app_mode = False
            elif data in ('?25', '?12', '?12;25'):
                pass # cursor hilite
            elif data == '?5':
                pass # flash
            elif data == '34':
                pass # ???
            elif data == '?10000020': # private terminal.py escape sequence
                # enable get key code mode
                self.get_key_code_mode = True
            else:
                print >>sys.stderr, 'unknown "l" code', repr(data)
        elif ch == 'h':
            if data == '7':
                print 'enable wrap'
            elif data == '?1':
                self.app_mode = True
            elif data in ('?25', '?12', '?12;25'):
                pass # cursor hilite
            elif data == '?5':
                pass # flash
            elif data == '34':
                pass # ???
            else:
                print >>sys.stderr, 'unknown "h" code', repr(data)
        elif ch == '@':
            for i in xrange(_int(data)):
                line = self._data[self.y]
                char = line.pop()
                line.insert(self.x + 1, Character())
            self.lines_updated.add(self.y)
        elif ch == 'L':
            for i in xrange(_int(data)):
                self.clear_line(self.scroll_end)
                line = self._data.pop(self.scroll_end)
                self._data.insert(self.y + 1, line)
            self._all_updated()
        elif ch == 'r':
            if not data:
                start, end = 0, self.rows - 1
            else:
                start, end = map(int, data.split(';'))
            self.scroll_start = start - 1
            self.scroll_end = end - 1
        elif ch == 'M':
            for i in xrange(_int(data)):
                self.clear_line(self.y)
                line = self._data.pop(self.y)
                self._data.insert(self.scroll_end, line)
            self._all_updated()
        elif ch == 'P':
            for i in xrange(_int(data)):
                line = self._data[self.y]
                char = line.pop(self.x)
                line.append(Character())
            self.lines_updated.add(self.y)
        else:
            print >>sys.stderr, 'unsupported code', repr(ch), repr(data)

    def _read_escape(self, r):
        data = ''
        while True:
            ch = r.next()
            if ord(ch) >= 0x40 and ord(ch) <= 0x7e:
                break
            data += ch
            if len(data) > 100: # application misbehaves
                raise ValueError()
        return ch, data

    def clear(self, option=2, line=False):
        self._normalize()
        if option == 0:
            for i in xrange(self.x, self.cols):
                self._data[self.y][i].reset()
            self.lines_updated.add(self.y)
            if not line:
                for i in xrange(self.y + 1, self.rows):
                    self.clear_line(i)
        elif option == 1:
            for i in xrange(self.x):
                self._data[self.y][i].reset()
            self.lines_updated.add(self.y)
            if not line:
                for i in xrange(self.y):
                    self.clear_line(i)
        elif option == 2:
            if line:
                self.clear_line(self.y)
            else:
                for i in xrange(self.rows):
                    self.clear_line(i)

    def clear_line(self, y):
        for i in xrange(self.cols):
            self._data[y][i].reset()
        self.lines_updated.add(y)

    def set_sgr(self, code):
        code = _int(code)

        if code == 0:
            self.style.copy_style(Character())
        elif code == 1:
            self.style.bold = True
        elif code == 3:
            pass # italic
        elif code == 4:
            pass # underline
        elif code == 7:
            self.style.negative = True
        elif code == 23:
            pass # disable italic
        elif code == 27:
            self.style.negative = False
        elif code in range(30, 38):
            self.style.fg = code - 30
        elif code == 39:
            self.style.fg = Character().fg
        elif code in range(40, 48):
            self.style.bg = code - 40
        elif code == 49:
            self.style.bg = Character().bg
        else:
            print 'unknown sgr', code

    def ring(self):
        pass # drrr!

    def append(self, ch):
        assert len(ch) == 1
        self._normalize()
        char = self._data[self.y][self.x]
        char.ch = ch
        char.copy_style(self.style)
        self.x += 1

        self.lines_updated.add(self.y)

    def scroll(self, n=1):
        if n > 0:
            for i in xrange(n):
                self.clear_line(self.scroll_start)
                first_line = self._data.pop(self.scroll_start)
                self._data.insert(self.scroll_end, first_line)
        elif n < 0:
            for i in xrange(-n):
                self.clear_line(self.scroll_end)
                last_line = self._data.pop(self.scroll_end)
                self._data.insert(self.scroll_start, last_line)
        self._all_updated()

    def _normalize(self):
        if self.y < 0:
            self.y = 0

        if self.x < 0:
            self.x = 0

        while self.x >= self.cols:
            self.x -= self.cols
            self.y += 1

        if self.y >= self.rows:
            self.y = self.rows - 1
            self.scroll(n=1)

        if self.scroll_start < 0:
            self.scroll_start = 0
        elif self.scroll_start >= self.rows:
            self.scroll_start = self.rows - 1

        if self.scroll_end < 0:
            self.scroll_end = 0
        elif self.scroll_end >= self.rows:
            self.scroll_end = self.rows - 1

        if self.scroll_end < self.scroll_start:
            self.scroll_end = self.scroll_start

    def _all_updated(self):
        self.lines_updated = set(range(self.rows))

    def __iter__(self):
        return iter(self._data)

theme_windows_xp = [
    (128, 128, 128),
    (255, 0, 0),
    (0, 255, 0),
    (255, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
    ], [
    (0, 0, 0),
    (128, 0, 0),
    (0, 128, 0),
    (128, 128, 0),
    (0, 0, 128),
    (128, 0, 128),
    (0, 128, 128),
    (192, 192, 192),
 ]


theme_terminal_app = [
    (0, 0, 0),
    (194, 54, 33),
    (37, 188, 36),
    (173, 173, 39),
    (73, 46, 225),
    (211, 56, 211),
    (51, 187, 200),
    (203, 204, 205),
    ], [
    (129, 131, 131),
    (252, 57, 32),
    (49, 231, 34),
    (234, 236, 35),
    (88, 51, 255),
    (249, 53, 248),
    (20, 240, 240),
    (233, 235, 235),
    ]
theme = theme_terminal_app

def get_color(i, bold=False):
    if not bold:
        return theme[0][i]
    else:
        return theme[1][i]

def _int(v, default=1):
    if not v:
        return default
    try:
        return int(v)
    except ValueError:
        print >>sys.stderr, 'cannot convert %r to int' % v
        return 0

class StringReader:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self._breakpoint = 0

    def next(self, n=1):
        if self.i + n > len(self.s):
            raise StopIteration
        self.i += n
        return self.s[self.i - n: self.i]

    def put_breakpoint(self):
        self._breakpoint = self.i

    def get_rest(self):
        return self.s[self._breakpoint:]

class Character:
    def __init__(self):
        self.reset()

    def reset(self):
        self.ch = ' '
        self.bg = 0
        self.fg = 7
        self.bold = False

    def copy_style(self, ch):
        self.bg = ch.bg
        self.fg = ch.fg
        self.bold = ch.bold

if __name__ == '__main__':
    t = Terminal()
    t.main(sys.argv[1:])
