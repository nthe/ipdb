
import pdb
import os
# commentary
# TODO: nothing
# ipdb: or other token

def do_max(_array):
    val = 0
    for i in _array:
        if i > val:
            val = i
    return val


def do_sum(_array, *args, **kwargs):
    val = 0
    for i in _array:
        val += i
    return val


class CompletelyUselessClass(object):

    def __init__(self, _something):
        self._something = _something
        self._v = 2 * 3

    def __call__(self):
        print repr(self)
    
    @staticmethod
    def calc(ins):
        for prop in ins.__dict__:
            print repr(prop)

def main():
    array = [1, 2, 3, 4]
    sm = do_sum(array)
    print "output"
    cuc = CompletelyUselessClass(4)
    mx = do_max(array)
    v = mx / float(sm)
    print """
 something 
 over
 several
 lines
"""
    cuc()
    cuc.calc(cuc)

    return v

if __name__ == "__main__":
    main()

