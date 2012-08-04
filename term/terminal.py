import pygame
import subprocess
import sys
import select
import os
import time
import StringIO
import codecs

class Terminal:
    def __init__(self):
        self.in_buff = ''
        self.out_buff = ''
        self.surf = None
        self.cols = 160
        self.rows = 40
        self.char_h = 12
        self.char_w = self.char_h * 13 // 20
        self.screen = Screen(self.rows, self.cols)

    def main(self):
        self.init_subprocess()
        self.init_window()
        while True:
            self.tick()

    def init_window(self):
        pygame.init()
        pygame.key.set_repeat(100, 100)
        self.surf = pygame.display.set_mode((self.cols * self.char_w, self.rows * self.char_h))
        self.font = pygame.font.Font('FreeMono.ttf', self.char_h)

    def init_subprocess(self):
        os.environ['COLS'] = str(self.cols)
        os.environ['ROWS'] = str(self.rows)
        os.environ['TERM'] = 'vt100'
        process = subprocess.Popen(['./pty-helper'] + sys.argv[1:],
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
            r, w, x = select.select([self.stdout_fd],
                                    [self.stdin_fd] if self.out_buff else [],
                                    [], 0.02)

            if r:
                in_buff.append(os.read(self.stdout_fd, 1))

            #print repr(self.out_buff), r, w, repr(in_buff)
            if w:
                os.write(self.stdin_fd, self.out_buff)
                self.out_buff = ''

            if not r:
                break

        self.in_buff = ''.join(in_buff)
        #print 'read', repr(self.in_buff)

    def tick_term(self):
        if self.in_buff:
            self.in_buff = self.screen.add(self.in_buff)

    def tick_window(self):
        for y, row in enumerate(self.screen):
            for x, char in enumerate(row):
                surf = self.font.render(char.ch, True,
                                        get_color(char.fg, char.bold),
                                        get_color(char.bg))
                self.surf.blit(surf, (self.char_w * x, self.char_h * y))

        cursor_color = self.screen._data[self.screen.y][self.screen.x].fg
        #print get_color(cursor_color), self.screen.x, self.screen.y
        pygame.draw.rect(self.surf,
                         get_color(cursor_color),
                         (self.char_w * self.screen.x, self.char_h * self.screen.y,
                          self.char_w, self.char_h),
                         1)

        for ev in pygame.event.get():
            if ev.type == pygame.KEYDOWN:
                self.handle_key(ev)
        pygame.display.flip()

    def handle_key(self, ev):
        mapping = {pygame.K_BACKSPACE: '\b',
                   pygame.K_RETURN: '\n',
                   }

        if ev.key in mapping:
            self.write(mapping[ev.key])

        elif ev.unicode:
            self.write(ev.unicode.encode('utf8'))

    def write(self, w):
        self.out_buff += w

class Screen:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.x = 0
        self.y = 0
        self.saved_pos = (0, 0)
        self.decoder = codecs.getincrementaldecoder('utf8')('replace')
        self._data = [ [ Character() for i in xrange(self.cols) ] for i in xrange(self.rows) ]
        self.style = Character()

    def add(self, data):
        reader = StringReader(data)
        try:
            while True:
                try:
                    self._handle(reader)
                except ValueError as err:
                    print >>sys.stderr, err
                reader.put_breakpoint()
        except StopIteration:
            pass
        self._normalize()
        return reader.get_rest()

    def _handle(self, r):
        ch = r.next()
        if ch == '\n':
            self.x = 0
        elif ch == '\r':
            self.y += 1
        elif ch == '\b':
            self.x -= 1
        elif ch == '\a':
            self.ring()
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
            elif ch in ('=', '>'):
                pass # set alternate/numeric keypad
            else:
                print >>sys.stderr, 'unknow escape', repr(ch)
        elif ch == '\x0f':
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
        elif ch == 'D':
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
        elif ch == 'J':
            n = _int(data)
            self.clear(option=n, line=False)
        elif ch == 'K':
            n = _int(data)
            self.clear(option=n, line=True)
        elif ch == 'S':
            n = _int(data)
            self.scroll(n)
        elif ch == 'T':
            n = _int(data)
            self.scroll(-n)
        elif ch == 'm':
            self.set_sgr(data)
        elif ch == 'n':
            self.report_position()
        elif ch == 's':
            self.saved_pos = (self.x, self.y)
        elif ch == 'u':
            self.x, self.y = self.saved_pos
        # non-ansi
        elif ch == 'l':
            if data == '7':
                print 'disable wrap'
            else:
                print >>sys.stderr, 'unknown "l" code', repr(data)
        elif ch == 'h':
            if data == '7':
                print 'enable wrap'
            else:
                print >>sys.stderr, 'unknown "h" code', repr(data)
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
                self._data[self.y][i].ch = ' '
            if not line:
                for i in xrange(self.y, self.rows):
                    self.clear_line(i)
        elif option == 1:
            for i in xrange(self.x):
                self._data[self.y][i].ch = ' '
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
            self._data[y][i].ch = ' '

    def set_sgr(self, data):
        if ';' not in data: data += ';'
        code, param = data.split(';', 1)
        code = _int(code)
        param = _int(param)

        if code == 0:
            self.style.copy_style(Character())
        elif code == 1:
            self.style.bold = True
        elif code == 7:
            self.style.negative = True
        elif code == 27:
            self.style.negative = False
        elif code in range(30, 38):
            self.style.fg = code - 30
            self.style.bold = param
        elif code == 39:
            self.style.fg = Character().fg
        elif code in range(40, 48):
            self.style.bg = code - 40

    def ring(self):
        pass # drrr!

    def append(self, ch):
        self._normalize()
        char = self._data[self.y][self.x]
        char.ch = ch
        char.copy_style(self.style)
        self.x += 1

    def scroll(self, n=1):
        if n > 0:
            for i in xrange(n):
                self.clear_line(0)
                first_line = self._data.pop(0)
                self._data.append(first_line)
        elif n < 0:
            for i in xrange(n):
                self.clear_line(self.rows - 1)
                last_line = self._data.pop()
                self._data.insert(0, last_line)

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

def _int(v):
    if not v:
        return 1
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
    t.main()
