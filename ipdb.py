import bdb
import os
import inspect
import sys
import subprocess
import linecache

class Ipdb(bdb.Bdb, object):

    def __init__(self):
        self._currout = " " + repr(None)
        super(Ipdb, self).__init__()


    def handle_resize(self):
        self._w = int(subprocess.check_output('tput cols', shell=True))
        self._h = int(subprocess.check_output('tput lines', shell=True))


    def update_ui(self):
        os.system('clear')
        self.handle_resize()
        el = " " * (self._w - 2) + "\n"
        self.ui = "{}{}{}{}{}".format(el, " [curr]" + self._currout + (" " * (self._w - 7 - len(self._currout))) + "\n", " [prev]" + self._prev + (" " * (self._w - 7 - len(self._prev))), el, " :: ")
        print
        first = max(1, self.curframe.f_lineno - 5)
        last = first + 15
        filename = self.curframe.f_code.co_filename
        breaklist = self.get_file_breaks(filename)
        for lineno in range(first, last+1):
            line = linecache.getline(filename, lineno,
                                     self.curframe.f_globals)
            if not line:
                print '[EOF]'
                break
            else:
                s = repr(lineno).rjust(3)
                if len(s) < 4: s = s + ' '
                if lineno in breaklist: s = s + 'B'
                else: s = s + ' '
                if lineno == self.curframe.f_lineno:
                    s = s + '->'
                print s + '\t' + line,
                self.lineno = lineno

        print " |\n" * (15 - (lineno - first))     
    
    def user_call(self, frame, args):
        name = frame.f_code.co_name
        if not name: name = '???'
        self._prev = self._currout
        self._currout = ' call: {} {}'.format(name, args)
        self.prompt(frame)


    def user_line(self, frame):
        name = frame.f_code.co_name
        if not name: name = '???'
        fn = self.canonic(frame.f_code.co_filename)
        line = linecache.getline(fn, frame.f_lineno, frame.f_globals)
        self._prev = self._currout
        self._currout = ' {}: {}'.format(frame.f_lineno, line.strip())
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
        cmd = raw_input(self.ui)

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

def r():
    Ipdb().set_trace(sys._getframe().f_back)

