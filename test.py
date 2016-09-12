import ipdb
import pdb


def do_max(_array):
    val = 0
    for i in _array:
        if i > val:
            val = i
    return val


def do_sum(_array):
    val = 0
    for i in _array:
        val += i
    return val


def main():
    ipdb.r()
    #pdb.set_trace()
    array = [1, 2, 3, 4]
    sm = do_sum(array)
    mx = do_max(array)
    v = mx / sm
    return v

if __name__ == "__main__":
    main()

