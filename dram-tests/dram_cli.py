#!/usr/bin/env python3

from litex import RemoteClient

from rich import print

def main():
    bus = RemoteClient()
    bus.open()
    buf = bus.read(0x4000aaa0, 4)
    print(f'buf: {buf}')

if __name__ == '__main__':
    main()

