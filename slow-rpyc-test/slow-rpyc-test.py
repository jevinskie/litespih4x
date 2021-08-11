#!/usr/bin/env python3


import argparse
import socket
import time
from typing import Final

from migen import *
from migen.fhdl import verilog

from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig
from litex.build.sim.cocotb import start_sim_server, SimServer, SimService
from litex.build.sim.common import CocotbVCDDumperSpecial

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

import cocotb
from cocotb.triggers import Timer, ReadWrite, ReadOnly, NextTimeStep
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase, ModifiableObject

from pyftdi.jtag import *

import attr
from rich import inspect as rinspect


def get_parent_srv(build_name: str = 'slow_rpyc_test', platform='platform_str', soc='soc_str', namespace='namespace_str'):
    socket_path = f'{build_name}.pipe'
    cocotb.top = None
    local_sim_server = start_sim_server(socket_path)
    local_sim_server.srv.service.exposed_platform = platform
    local_sim_server.srv.service.exposed_soc = soc
    local_sim_server.srv.service.exposed_ns = namespace
    return local_sim_server

def get_child_srv(build_name='slow_rpyc_test'):
    os.environ["TOPLEVEL"] = build_name
    cocotb.top = True
    srv = start_sim_server(None)
    return srv

parent_srv = get_parent_srv()
print(f'parent_srv: {parent_srv}')

print(f'parent_srv: soc: {parent_srv.srv.service.exposed_soc}')

child_srv = get_child_srv()
print(f'child_srv: {child_srv}')
print(f'child_srv: soc: {child_srv.root.soc}')

