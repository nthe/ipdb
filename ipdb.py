import bdb
import os
import sys
import subprocess
import linecache


_out = sys.stdout
_pf = sys.platform.lower()
_W = 80
_H = 25


if _pf == 'darwin':
    CLEAR = 'clear'
    def _resize_handler():
        w = int(subprocess.check_output('tput cols', shell=True))
        h = int(subprocess.check_output('tput lines', shell=True)) 
        return w, h

elif _pf.startswith('linux'):
    CLEAR = 'clear'
    def _resize_handler():
        return map(int, subprocess.check_output('stty size', shell=True).split())

elif _pf == 'win32':
    CLEAR = 'cls'
    def _resize_handler():
        from ctypes import windll, create_string_buffer
        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            import struct
            (bufx, bufy, curx, cury, wattr, left, top, right, bottom, maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            sizex = right - left + 1
            sizey = bottom - top + 1
        else:
            sizex, sizey = _W, _H
        return sizex, sizey

else:
    def _resize_handler():
        return _W, _H


class Ipdb(bdb.Bdb, object):
    """ Simple, small, nteractive, console-based Python debugger."""
    def __init__(self):
        self._currout = " " + repr(None)
        super(Ipdb, self).__init__()


    def handle_resize(self):
        self._w, self._h = _resize_handler()


    def update_ui(self):
        os.system(CLEAR)
        self.handle_resize()
        el = " " * (self._w - 2) + "\n"
        self.ui = "%s" % (" previous> " + self._prev + (" " * (self._w - 7 - len(self._prev))))
        first = max(1, self.curframe.f_lineno - 5)
        last = first + 10

        filename = self.curframe.f_code.co_filename
        breaklist = self.get_file_breaks(filename)
        for lineno in range(first, last+1):
            line = linecache.getline(filename, lineno,
                    self.curframe.f_globals)
            if not line:
                print >>_out, '[EOF]'
                break
            else:
                s = repr(lineno).rjust(3)
                if len(s) < 4: s = s + ' '
                if lineno in breaklist: s = s + 'B'
                else: s = s + ' '
                if lineno == self.curframe.f_lineno:
                    s = s + '->'
                print >>_out, s + '\t' + line,
                self.lineno = lineno
        
        print >>_out, "\n" * (10 - (lineno - first))     
        print >>_out, self.ui


    def user_call(self, frame, args):
        name = frame.f_code.co_name
        if not name: name = '???'
        self._prev = self._currout
        self._currout = ' call: %s %s' % (name, args)
        self.prompt(frame)


    def user_line(self, frame):
        name = frame.f_code.co_name
        if not name: name = '???'
        fn = self.canonic(frame.f_code.co_filename)
        line = linecache.getline(fn, frame.f_lineno, frame.f_globals)
        self._prev = self._currout
        self._currout = ' %s: %s' % (frame.f_lineno, line.strip())
        self.prompt(frame)


    def user_return(self, frame, retval):
        self._prev = self._currout
        self._currout = ' retn: ' + repr(retval)
        self.prompt(frame)


    def user_exception(self, frame, exc_stuff):
        self._currout = ' expt: ' +  exc_stuff
        self.prompt(frame)


    def prompt(self, f):
        self.curframe = f
        self.update_ui()
        cmd = raw_input(" [n]ext  [s]tep in  [r]eturn  [q]uit ")

        try:
            getattr(self, 'do_' + cmd)(f)

        except AttributeError:
            self.prompt(f)


    def do_quit(self, args):
        self.set_quit()
    do_q = do_quit


    def do_next(self, f):
        stack, idx = self.get_stack(f, None)
        cf = stack[idx][0]
        self.set_next(cf)
    do_n = do_next


    def do_step(self, args):
        self.set_step()
    do_s = do_step


    def do_return(self, f):
        stack, idx = self.get_stack(f, None)
        cf = stack[idx][0]
        self.set_return(cf)
    do_r = do_return


def r():
    try:
        Ipdb().set_trace(sys._getframe().f_back)
    except AttributeError:
        print >>_out, " bye."
        
