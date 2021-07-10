#!/usr/bin/env python3

import sys

from pyDigitalWaveTools.vcd.parser import VcdParser

def dump(path: str):
	with open(path) as vcd_file:
		vcd = VcdParser()
		vcd.parse(vcd_file)
		print(vcd)
		print()
		print(vcd.scope)
	return


if __name__ == '__main__':
	dump(sys.argv[1])
