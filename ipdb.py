import bdb
import inspect
import time
import os
import sys
import subprocess
import linecache

_out = sys.stdout
_pf = sys.platform.lower()
_W = 80
_H = 35

_prompt = """\
 [ ]next [s]tep-in [r]eturn [w]atch [u]nwatch  [v]ars 
 [a]uto  [j]ump    [st]ack  [l]og   [c]ontinue [q]uit
 $ """

_banner = """
 > Minimal Interactive Python Debugger
 """

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
            (bufx, bufy, curx, cury, wattr, left, top, right, bottom, maxx, maxy) = struct.unpack("hhhhHhhhhhh",
                                                                                                  csbi.raw)
            sizex = right - left + 1
            sizey = bottom - top + 1
        else:
            sizex, sizey = _W, _H
        return sizex, sizey

else:
    def _resize_handler():
        return _W, _H


class Ipdb(bdb.Bdb, object):
    """ Simple, small, interactive, console-based Python debugger."""

    def __init__(self):
        self._curr = " " + repr(None)
        self._vars = []
        self._watches = []
        self._error_msg = repr(None)
        self._show_vars = False
        self._show_stack = False
        self._wait = False
        self._jumping = False
        self._jump_line_no = None
        self._jump_file = None
        self._scriptfile = None
        self.curframe = None
        self._prev = None
        self.ui = ""
        self.lino_no = 0
        self._w = 80
        self._h = 25
        super(Ipdb, self).__init__()

    def handle_resize(self):
        self._w, self._h = _resize_handler()

    def get_line(self, line_no=None, filename=None):
        if line_no is None:
            line_no = self.curframe.f_lineno
        if filename is None:
            filename = self.curframe.f_code.co_filename
        return linecache.getline(filename, line_no, self.curframe.f_globals)

    def update_ui(self):
        os.system(CLEAR)
        self.handle_resize()

        self.ui = "%s" % (" previous>" + self._prev + (" " * (self._w - 10 - len(self._prev))))

        if any([watch in self.curframe.f_locals for watch in self._watches]):
            self.ui += "\n\n"
            for watch in self._watches:
                if watch in self.curframe.f_locals:
                    watch_val = repr(self.curframe.f_locals[watch])
                    self.ui += "%s" % (
                        (" watching> %7s" % watch) + " : " + watch_val + (" " * (self._w - 21 - (len(watch_val)))))

        first = max(1, self.curframe.f_lineno - 5)
        last = first + (self._h / 2)

        if self._show_vars:
            self.ui += "\n\n"
            for vari in self._vars:
                if vari in self.curframe.f_locals:
                    var_val = repr(self.curframe.f_locals[vari])
                    self.ui += "%s" % (
                        ("   locals> %7s" % vari) + " : " + var_val + (" " * (self._w - 21 - (len(var_val)))))

        self.ui += "\n"
        print >> _out, _banner
        prev = self.curframe.f_back

        print >> _out, " (prev) %s" % (prev.f_code.co_name if prev is not None else repr(None))
        print >> _out, " (curr) %s\n" % self.curframe.f_code.co_name

        first = max(1, self.curframe.f_lineno - 5)
        filename = self.curframe.f_code.co_filename
        break_list = self.get_file_breaks(filename)

        for line_no in range(first, last + 1):
            line = self.get_line(line_no)
            if not line:
                print >> _out, '[EOF]'
                break
            else:
                s = repr(line_no).rjust(3)
                if len(s) < 4:
                    s += ' '
                if line_no in break_list:
                    s += 'B'
                else:
                    s += ' '
                if line_no == self.curframe.f_lineno:
                    s += '->'
                print >> _out, s + '\t' + line,
                self.lino_no = line_no

        print >> _out, " ||\n" * ((self._h / 2) - (self.lino_no - first))
        
        if self._show_stack:
            self.ui += "\n"
            rec = self.curframe
            while rec.f_back:
                self.ui += "    stack> " + str(rec.f_lineno) + " : " + self.get_line(rec.f_lineno, rec.f_code.co_filename).strip() + "\n"
                rec = rec.f_back
        
        print >> _out, self.ui
        print >> _out, " <error> %s\n" % self._error_msg

    def jump_handler(self, frame):
        c_file = self.canonic(frame.f_code.co_filename)
        if frame.f_lineno == self._jump_line_no and c_file == self._jump_file:
            self._jumping = False
        return not self._jumping

    def user_call(self, frame, args):
        if self._jumping:
            st = self.jump_handler(frame)
            if not st:
                return
        if self._wait:
            return
        self._vars = frame.f_code.co_varnames
        name = frame.f_code.co_name
        if not name:
            name = '???'
        self._prev = self._curr
        self._curr = ' called %s, args: %s' % (name, args)
        self.prompt(frame)

    def user_line(self, frame):
        if self._jumping:
            st = self.jump_handler(frame)
            if not st:
                return
        if self._wait:
            if self._scriptfile != self.canonic(frame.f_code.co_filename):
                return
            else:
                self._wait = False
        self._vars = frame.f_code.co_varnames
        fn = self.canonic(frame.f_code.co_filename)
        line = linecache.getline(fn, frame.f_lineno, frame.f_globals)
        self._prev = self._curr
        self._curr = ' executed [%s] %s' % (frame.f_lineno, line.strip())
        self.prompt(frame)

    def user_return(self, frame, retval):
        if self._jumping:
            st = self.jump_handler(frame)
            if not st:
                return
        if self._wait:
            return
        self._prev = self._curr
        self._curr = ' returned ' + repr(retval)
        self.prompt(frame)

    def user_exception(self, frame, exc_stuff):
        if self._jumping:
            st = self.jump_handler(frame)
            if not st:
                return
        if self._wait:
            return
        self._curr = ' raised exception %s %s %s' % exc_stuff
        self.prompt(frame)

    def prompt(self, f):
        self.curframe = f
        self.update_ui()
        args = raw_input(_prompt)
        args = args.split(" ")
        cmd = args.pop(0)
        try:
            if cmd is not None:
                getattr(self, 'do_' + cmd)(*args)
        except AttributeError:
            self.prompt(f)

    def do_clear(self, *args):
        pass

    def do_continue(self, *args):
        self.set_continue()

    do_c = do_continue

    def do_quit(self, *args):
        self.set_quit()

    do_q = do_quit

    def do_stack(self, *args):
        self._show_stack = not self._show_stack
        self.prompt(self.curframe)

    do_st = do_stack

    def do_jump(self, *args):
        script_file = None
        try:
            if len(args) < 2:
                line_no = int(args[0])
            else:
                script_file, line_no = args
                line_no = int(line_no)
        except (ValueError, IndexError):
            self._error_msg = "Usage: jump [<file>] <line>"
            self.prompt(self.curframe)
            return
    
        line = self.get_line(line_no, script_file).strip()
        if line != '':
            self._jump_line_no = line_no
            self._jump_file = self.canonic(self.curframe.f_code.co_filename)
            self._jumping = True

        else:
            self._error_msg = "Cannot jump on empty line."
            self.prompt(self.curframe)

    do_j = do_jump

    def do_next(self, *args):
        self.set_next(self.curframe)

    do_ = do_next

    def do_step(self, *args):
        self.set_step()

    do_s = do_step

    def do_vars(self, *args):
        self._show_vars = not self._show_vars
        self.prompt(self.curframe)

    do_v = do_vars

    def do_return(self, *args):
        self.set_return(self.curframe)

    do_r = do_return

    def do_watch(self, *args):
        if args[0] not in self._watches:
            self._watches.append(args[0])
        self.prompt(self.curframe)

    do_w = do_watch

    def do_unwatch(self, *args):
        if args[0] in self._watched:
            self._watches.pop(_self.watches.index(args[0]))
        self.prompt(self.curframe)

    do_u = do_watch

    def do_brake(self, *args):
        if len(args) < 2:
            line_no = int(args[0])
            filename = self._scriptfile
        else:
            filename, line_no = args
            line_no = int(line_no)
        self.stoplineno = line_no
        try:
            self.set_brake(filename, line_no, 0, None, None)
        except Exception as e:
            print e
            from pprint import pprint
            pprint(self.__dict__)

    do_b = do_brake


def run(_script):
    import __main__
    ip = Ipdb()
    ip._wait = True
    ip._scriptfile = ip.canonic(_script)
    statement = "execfile(%r)" % _script
    ip.run(statement)


def track():
    try:
        Ipdb().set_trace(sys._getframe().f_back)
    except (AttributeError, bdb.BdbQuit):
        print >> _out, " bye."


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print " usage: python {} <script.py>".format(__file__)
        sys.exit(1)
    run(sys.argv[1])
