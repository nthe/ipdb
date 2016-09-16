import sys
from krt import run

def main(args=None):
    if len(sys.argv) < 2:
        print " usage: python {} <script.py>".format(__file__)
        sys.exit(1)
    run(sys.argv[1], *sys.argv[2:])

if __name__ == "__main__":
    main()

