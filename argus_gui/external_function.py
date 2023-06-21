import time
import sys

def external_function():
    for i in range(5):
        print(f'Line {i+1}')
        sys.stdout.flush()
        time.sleep(2)

if __name__ == '__main__':
    external_function()
