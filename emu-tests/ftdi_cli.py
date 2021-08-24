#!/usr/bin/env python3

import sys

from pyftdi.spi import SpiController, SpiPort

spi = SpiController()

spi.configure(sys.argv[1])

periph = spi.get_port(cs=0, freq=12E6, mode=0)

jedec_id = periph.exchange([0x9f], 3)
print(f'jedec_id: {jedec_id.hex()}')

first_four_bytes = periph.exchange([0x03, 0x00, 0x00, 0x00], 4)
print(f'first_four_bytes: {first_four_bytes.hex()}')
