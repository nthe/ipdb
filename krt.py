#! /usr/bin/env python

from time import sleep
import bdb
import sys
import subprocess
import cStringIO
from linecache import getline

__all__ = ['run', 'track']
__version__ = 0.1
__author__ = "nthe | Juraj Onuska | 2016"

_obuff = cStringIO.StringIO()
_out = sys.stdout
_in = sys.stdin
_pf = sys.platform.lower()
_W = 80
_H = 35
_max_output_buffer_size = 100
_code_section_height = 20

_small_help = """\
[ ]next  [s]tep-in  [r]eturn  [c]ontinue  [h]elp   [o]utput  [q]uit"""

_full_help = """

 [ ]next (enter pressed)    Evaluate current line and go to next line.
 [s]tep-in                  Step inside if callable, else go to next line.
 [r]eturn                   Return from call to outer frame.

 [j]ump [<file>] ['disp'] <line> <verbose>    

                            Jump to line in current file. Setting verbose to True or 1
                            will perform jump in 'visible' mode. This mode can take
                            certain amount of time to complete. Consider turning off
                            code display.
                            
                            When 'disp' is stated, the number refers to dispatch number,
                            counted from beginning of program evaluation. Using dispatch
                            jumping in combination with line jumping will NOT work.

                            Use '.' as reference to currently debugged file.

                            Examples:
                                $ jump . 20
                                $ jump disp 3000 True
                                $ jump 20
                                $ jump disp 300
        
 [c]ontinue                 Continue evaluation of file.
 [w]atch <variable>         Add local 'variable' to watches.
 [u]n-watch <variable>      Remove local 'variable' from watches.
 [o]utput                   Show / hide output of debugged program (replaces whole ui).
 [v]ars                     Show / hide local variables.
 [st]ack                    Show / hide current stack of stack frames.
 [co]de                     Show / hide code display.
 [re]size                   Adjust number of lines of code display.
 [h]elp                     Display small / large help panel.
 [q]uit                     Leave debugger.
"""

def unix_prompter():
    curses.filter()
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    k = stdscr.getch()
    curses.nocbreak()
    curses.echo()
    curses.endwin()
    return k

if _pf == 'darwin':
    import curses
    prompter = unix_prompter
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


class KRT(bdb.Bdb, object):
    """ Simple, small, interactive, console-based Python debugger."""

    def __init__(self):
        self._curr = " " + repr(None)
        self._vars = []
        self._watches = []
        self._error_msg = repr(None)
        self._show_vars = False
        self._show_stack = False
        self._show_code = True
        self._show_help = False
        self._show_output = False
        self._wait = False
        self._jumping = False
        self._jump_to_dispatch = False
        self._jump_to_dispatch_id = 0
        self._jump_line_no = None
        self._jump_file = None
        self._verbose_jump = False
        self._scriptfile = None
        self.curframe = None
        self._prev = None
        self._dispatch_counter = 0
        self._w = 80
        self._h = 25
        self._delimiter = ""
        super(KRT, self).__init__()

    def handle_resize(self):
        self._w, self._h = _resize_handler()
        self._delimiter = " %s " % ("-" * (self._w - 2))

    def get_line(self, line_no=None, filename=None):
        if line_no is None:
            line_no = self.curframe.f_lineno
        if filename is None:
            filename = self.curframe.f_code.co_filename
        return getline(filename, line_no, self.curframe.f_globals)

    def update_ui(self):
        subprocess.Popen([CLEAR], shell=True)
        self.handle_resize()
        print >> _out 
        if not self._show_output:
            print >> _out, "      KRT >",
            print >> _out, _full_help if self._show_help else _small_help
    
            if any([watch in self.curframe.f_locals for watch in self._watches]):
                print >> _out, self._delimiter
                for watch in self._watches:
                    if watch in self.curframe.f_locals:
                        watch_val = repr(self.curframe.f_locals[watch])
                        print >> _out, "%s" % ((" watching > %s" % watch) + " : " + watch_val)

            if self._show_vars:
                print >> _out, self._delimiter 
                i = 0
                for vari in self._vars:
                    if vari in self.curframe.f_locals:
                        label = "locals" if i == 0 else "      "
                        var_val = repr(self.curframe.f_locals[vari])
                        print >> _out, "%s" % (("   %s > %s" % (label, vari)) + " : " + var_val)
                        i += 1
                if i == 0:
                    print >> _out, "   locals > " 

            if self._show_stack:
                print >> _out, self._delimiter
                rec = self.curframe
                i = 0
                while rec.f_back:
                    label = "stack" if i == 0 else "     "
                    print >> _out, "    %s > %6s" % (label, str(rec.f_lineno)) + " : " + self.get_line(rec.f_lineno, rec.f_code.co_filename).strip()
                    rec = rec.f_back
                    i += 1
            
            print >> _out, self._delimiter

            print >> _out, "    error > %s" % self._error_msg
            prev = self.curframe.f_back
            
            print >> _out, self._delimiter
            print >> _out, "%s" % (" previous >" + self._prev)
            print >> _out, self._delimiter

            if self._show_code:
                first = max(1, self.curframe.f_lineno - (_code_section_height / 2))
                last = first + _code_section_height
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
                            s += '~>'
                        print >> _out, s + '\t' + line,

                print >> _out, self._delimiter 
                print >> _out, "  disp id > %s" % self._dispatch_counter
                print >> _out, self._delimiter

            if not self._show_code:
                print >> _out, "%s" % ("  current >" + self._curr)
                print >> _out, self._delimiter

        else:
            print >> _out, "--- program output ---\n"
            for line in _obuff.getvalue().split('\n'):
                if line.strip():
                    print >> _out, line 
            print >> _out, "\n-------- end ---------"

    def jump_handler(self, frame):
        if self._jump_to_dispatch:
            if self._jump_to_dispatch_id == self._dispatch_counter:
                self._jumping = False
                self._jump_to_dispatch = False
        c_file =self.canonic(frame.f_code.co_filename)
        if frame.f_lineno == self._jump_line_no and c_file == self._jump_file:
            self._jumping = False
        self.set_step()
        return not self._jumping

    def user_call(self, frame, args):
        self._dispatch_counter += 1
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
        self._dispatch_counter += 1
        if self._jumping:
            st = self.jump_handler(frame)
            if not st:
                if self._verbose_jump:
                    self.curframe = frame
                    self.update_ui()
                    sleep(0.1)
                return
        if self._wait:
            if self._scriptfile != self.canonic(frame.f_code.co_filename):
                return
            else:
                self._wait = False
        self._vars = frame.f_code.co_varnames
        fn = self.canonic(frame.f_code.co_filename)
        line = getline(fn, frame.f_lineno, frame.f_globals)
        self._prev = self._curr
        self._curr = ' executed [%s] %s' % (frame.f_lineno, line.strip())
        self.prompt(frame)

    def user_return(self, frame, retval):
        self._dispatch_counter += 1
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
        self._dispatch_counter += 1
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
        args = raw_input()
        line = args
        args = args.split(" ")
        cmd = args.pop(0)
        try:
            if cmd is not None:
                getattr(self, 'do_' + cmd)(*args)

        except AttributeError:
            try:
                print >> _out
                self.execute(line)
                if "print" in line:
                    raw_input()
                self.prompt(f)

            except Exception as e:
                self.prompt(f)

        finally:
            pass

    def displayhook(self, obj):
        if obj is not None:
            print repr(obj)

    def execute(self, line):
        locals = self.curframe.f_locals
        globals = self.curframe.f_globals
        try:
            code = compile(line + '\n', '<stdin>', 'single')
            save_stdout = sys.stdout
            save_stdin = sys.stdin
            save_displayhook = sys.displayhook
            try:
                sys.stdin = _in
                sys.stdout = _out
                sys.displayhook = self.displayhook
                exec code in globals, locals
            finally:
                sys.stdout = save_stdout
                sys.stdin = save_stdin
                sys.displayhook = save_displayhook
        except:
            t, v = sys.exc_info()[:2]
            if type(t) == type(''):
                exc_type_name = t
            else: exc_type_name = t.__name__
            print >>_out, '***', exc_type_name + ':', v

    def do_code(self, *args):
        self._show_code = not self._show_code
        self.prompt(self.curframe)

    do_co = do_code

    def do_resize(self, *args):
        global _code_section_height
        if len(args) < 2:
            if int(args[0]) < 1:
                self._error_msg = "Usage: resize <int: size>"
            else:
                _code_section_height = int(args[0])
        else:
            self._error_msg = "Usage: resize <int: size>"
        self.prompt(self.curframe)

    do_re = do_resize

    def do_clear(self, *args):
        pass

    def do_continue(self, *args):
        self.set_continue()

    do_c = do_continue

    def do_help(self, *args):
        self._show_help = not self._show_help
        self.prompt(self.curframe)

    do_h = do_help

    def do_quit(self, *args):
        self.set_quit()

    do_q = do_quit

    def do_stack(self, *args):
        self._show_stack = not self._show_stack
        self.prompt(self.curframe)

    do_st = do_stack

    def do_jump(self, *args):
        script_file = None
        verbose = False
        try:
            try:
                if len(args) == 1:
                    line_no = args[0]

                elif len(args) == 2:
                    script_file, line_no = args

                else:
                    sciprt_file, line_no, verbose = args

                line_no = int(line_no)
                verbose = bool(verbose)

            except (ValueError, IndexError):
                self._error_msg = "Usage: jump [<file>] <line>"
                self.prompt(self.curframe)
                return
           
            self._verbose_jump = verbose
            if script_file:
                if script_file.strip() == "disp":
                    self._jump_to_dispatch = True
                    self._jumping = True
                    self._jump_to_dispatch_id = int(line_no)
                    return
            
            if script_file == '.':
                script_file = None

            line = self.get_line(line_no, script_file).strip()
            if line != '':
                self._jump_line_no = line_no
                self._jump_file = self.canonic(self.curframe.f_code.co_filename)
                self._jumping = True

            else:
                self._error_msg = "Cannot jump on empty line."
                self.prompt(self.curframe)

        except Exception as e:
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
    
    def do_output(self, *args):
        self._show_output = not self._show_output
        self.prompt(self.curframe)

    do_o = do_output

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

    def run(self, cmd, globals=None, locals=None):
        if globals is None:
            import __main__
            globals = __main__.__dict__
        if locals is None:
            locals = globals
        self.reset()
        sys.settrace(self.trace_dispatch)
        if not isinstance(cmd, bdb.types.CodeType):
            cmd = cmd+'\n'
        try:
            _tmp = sys.stdout
            sys.stdout = _obuff 
            exec cmd in globals, locals
        except bdb.BdbQuit:
            print
        finally:
            sys.stdout = _tmp
            _obuff.close()
            self.quitting = 1
            sys.settrace(None)


def run(_script):
    import __main__
    ip = KRT()
    ip._wait = True
    ip._scriptfile = ip.canonic(_script)
    statement = "execfile(%r)" % _script
    ip.run(statement)


def track():
    try:
        KRT().set_trace(sys._getframe().f_back)
    except (AttributeError, bdb.BdbQuit):
        print >> _out, " bye."


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print " usage: python {} <script.py>".format(__file__)
        sys.exit(1)
    run(sys.argv[1])

