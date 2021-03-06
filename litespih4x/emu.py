# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations

from .emu_mem import FlashEmuMem

from rich import print

from migen import *
from migen.genlib.cdc import MultiReg
from migen.genlib.resetsync import AsyncResetSingleStageSynchronizer

from litex.build.generic_platform import Subsignal, Pins, IOStandard
from litex.soc.interconnect import stream
from litedram.core.crossbar import LiteDRAMNativeReadPort
from litespih4x.emu_dram import FlashEmuDRAMLite

from typing import Final, Optional, Union

import attr

import cocotb

SigType = Signal
if cocotb.top is not None:
    SigType = cocotb.handle.ModifiableObject


def flashemu_pmod_io(pmod):
    return [
        ("flashemu", 0,
            Subsignal("cs_n", Pins(f"{pmod}:0")),
            Subsignal("mosi", Pins(f"{pmod}:1")),
            Subsignal("clk", Pins(f"{pmod}:2")), # P side clock input on FPGA required for nice global clock routing
            Subsignal("miso", Pins(f"{pmod}:3")),
            Subsignal("rst_n", Pins(f"{pmod}:5")),
            Subsignal("wp", Pins(f"{pmod}:6")),
            Subsignal("hold", Pins(f"{pmod}:7")),
            IOStandard("LVCMOS33"),
         ),
    ]


@attr.s(auto_attribs=True)
class SPISigs:
    sclk: SigType
    csn: SigType
    si: SigType
    so: SigType

    @classmethod
    def from_pads(cls, pads: Record) -> SPISigs:
        sig_dict = {p[0]: getattr(pads, p[0]) for p in pads.layout}
        return cls(**sig_dict)


@attr.s(auto_attribs=True)
class QSPISigs:
    sclk: SigType
    rstn: Optional[SigType]
    csn: SigType
    si: Union[SigType, TSTriple]
    so: Union[SigType, TSTriple]
    wpn: Union[SigType, TSTriple]
    sio3: Union[SigType, TSTriple]

    @classmethod
    def from_pads(cls, pads: Record) -> QSPISigs:
        sig_dict = {p[0]: getattr(pads, p[0]) for p in pads.layout}
        return cls(**sig_dict)


CMD_READ: Final = 0x03
CMD_QREAD: Final = 0x6b

CMD_RDID: Final = 0x9f
IDCODE: Final = 0xc22539
# IDCODE: Final = 0xAA550F

CMD_RDSR: Final = 0x05
CMD_RDCR: Final = 0x15
CMD_WRSR: Final = 0x01

CMD_WREN: Final = 0x06


class FlashEmu(Module):
    def __init__(self, cd_sys: ClockDomain, qrs: QSPISigs, qes: QSPISigs, sz_mbit: int, idcode: int):
        self.qrs = qrs
        self.qes = qes
        self.sz_mbit = sz_mbit
        self.idcode = idcode = Signal(24, reset=idcode)


        if qrs.rstn is None:
            qrs.rstn = Signal()
            self.comb += qrs.rstn.eq(~ResetSignal())

        if qes.rstn is None:
            qes.rstn = Signal()
            self.comb += qes.rstn.eq(~ResetSignal())

        # else if both have reset, wire them up?


        self.cd_spi = self.clock_domains.cd_spi = cd_spi = ClockDomain('spi')
        self.comb += ClockSignal('spi').eq(qes.sclk) # & ~qes.csn & qes.rstn
        self.specials.reset_syncer = AsyncResetSingleStageSynchronizer(cd_spi, ~qes.rstn | qes.csn)

        self.clock_domains.cd_spi_inv = cd_spi_inv = ClockDomain('spi_inv')
        self.comb += ClockSignal('spi_inv').eq(~ClockSignal('spi'))
        self.specials.reset_syncer_inv = AsyncResetSingleStageSynchronizer(cd_spi_inv, ~qes.rstn | qes.csn)

        self.rsi_ts = rsi_ts = TSTriple()
        self.rso_ts = rso_ts = TSTriple()
        self.rwpn_ts = rwpn_ts = TSTriple()
        self.rsio3_ts = rsio3_ts = TSTriple()

        self.specials += rsi_ts.get_tristate(qrs.si)
        self.specials += rso_ts.get_tristate(qrs.so)
        self.specials += rwpn_ts.get_tristate(qrs.wpn)
        self.specials += rsio3_ts.get_tristate(qrs.sio3)


        self.esi_ts = esi_ts = TSTriple()
        self.eso_ts = eso_ts = TSTriple()
        self.ewpn_ts = ewpn_ts = TSTriple()
        self.esio3_ts = esio3_ts = TSTriple()

        self.specials += esi_ts.get_tristate(qes.si)
        self.specials += eso_ts.get_tristate(qes.so)
        self.specials += ewpn_ts.get_tristate(qes.wpn)
        self.specials += esio3_ts.get_tristate(qes.sio3)


        # self.comb += [
        #     qrs.sclk.eq(qes.sclk),
        #     qrs.rstn.eq(qes.rstn),
        #     qrs.csn.eq(qes.csn),
        #     qrs.si.eq(qes.si),
        #     qrs.so.eq(qes.so),
        #     qrs.wpn.eq(qes.wpn),
        #     qrs.sio3.eq(qes.sio3),
        # ]

        self.esi = esi = Signal()
        self.eso = eso = Signal()
        self.eso_oe = eso_oe = Signal()
        self.ewpn = ewpn = Signal()
        self.esio3 = esio3 = Signal()

        # self.comb += [
        #     esi.eq(esi_ts.i),
        #     eso.eq(rso_ts.i),
        # ]

        self.comb += [
            qrs.sclk.eq(qes.sclk),
            qrs.rstn.eq(qes.rstn),
            qrs.csn.eq(qes.csn),
            esi.eq(esi_ts.i),
            rsi_ts.o.eq(esi_ts.i),
            eso_ts.o.eq(eso),
            # eso_ts.o.eq(rso_ts.i),
            # eso_ts.oe.eq(1),
        ]

        self.eso_delayed = eso_delayed = Signal()
        self.comb += eso_ts.o.eq(eso_delayed)
        self.sync.spi_inv += eso_delayed.eq(eso)

        self.eso_oe_delayed = eso_oe_delayed = Signal()
        self.comb += eso_ts.oe.eq(eso_oe_delayed & ~ResetSignal('spi_inv'))
        self.sync.spi_inv += eso_oe_delayed.eq(eso_oe)

        self.comb += [
            esi_ts.oe.eq(0),
            eso_oe.eq(0),
        ]

        self.comb += [
            rsi_ts.oe.eq(1),
            rso_ts.oe.eq(0),
            rwpn_ts.oe.eq(0),
            rsio3_ts.oe.eq(0),
        ]

        self.cmd_bit_cnt = cmd_bit_cnt = Signal(max=8, reset=1)
        self.cmd = cmd = Signal(8, reset=esi, init=0)
        self.cmd_next = cmd_next = Signal(8)

        self.addr = addr = Signal(24)
        self.addr_next = addr_next = Signal(24)
        self.addr_cnt = addr_cnt = Signal(max=24)
        self.dr = dr = Signal(8)
        self.dr_bit_cnt = dr_bit_cnt = Signal(max=8)
        self.qmode = qmode = Signal()

        # self.specials.flash_mem = flash_mem = Memory(8, 0x100, init=[self.val4addr(a) for a in range(0x100)], name='flash_mem')
        # self.specials.fmrp = fmrp = flash_mem.get_port(clock_domain='spi')
        # self.comb += fmrp.adr.eq(addr_next)
        self.flash_mem = self.submodules.flash_mem = flash_mem = FlashEmuMem(cd_sys, cd_spi, 0x100)
        self.fmp = fmp = flash_mem.spiemu_port
        self.lmp = lmp = flash_mem.loader_port
        self.comb += fmp.adr.eq(addr_next)

        cmd_fsm = FSM(reset_state='get_cmd')
        cmd_fsm = ClockDomainsRenamer('spi')(cmd_fsm)
        self.submodules.cmd_fsm = cmd_fsm

        self.get_cmd_flag = get_cmd_flag = Signal()
        cmd_fsm.act('get_cmd',
            cmd_next.eq(Cat(esi, cmd[:-1])),
            get_cmd_flag.eq((cmd_bit_cnt == 7) & (cmd_next[0])),
            NextValue(cmd, cmd_next),
            NextValue(cmd_bit_cnt, cmd_bit_cnt + 1),

            If(cmd_bit_cnt == 7,
                If(cmd_next == CMD_READ,
                    NextState('read_get_addr'),
                ).Elif(cmd_next == CMD_QREAD,
                    NextState('read_get_addr'),
                    NextValue(qmode, 1),
                ).Elif(cmd_next == CMD_RDID,
                    NextState('rdid'),
                ).Else(
                    NextState('bad_cmd_err'),
                )
            ),
        )

        cmd_fsm.act('rdid',
            eso_oe.eq(1),
            eso.eq(idcode[-1]),
            NextValue(idcode, Cat(idcode[-1], idcode[:-1])),
        )

        cmd_fsm.act('read_get_addr',
            addr_next.eq(Cat(esi, addr[:-1])),
            NextValue(addr, addr_next),
            NextValue(addr_cnt, addr_cnt + 1),
            If(addr_cnt == 23,
               NextState('read_get_data'),
            )
        )

        self.dr_tmp = dr_tmp = Signal(8)
        cmd_fsm.act('read_get_data',
            If(dr_bit_cnt == 0,
                dr_tmp.eq(fmp.dat_r)
            ).Else(
                dr_tmp.eq(dr)
            ),
            addr_next.eq(addr + 1),
            If(~qmode,
                NextValue(dr_bit_cnt, dr_bit_cnt + 1),
            ).Else(
                NextValue(dr_bit_cnt, dr_bit_cnt + 4),
            ),
            NextValue(dr, Cat(0, dr_tmp[:-1])),
            If((dr_bit_cnt == 7) | ((dr_bit_cnt == 4) & qmode),
                NextValue(addr, addr_next),
            ),
            eso_oe.eq(1),
            eso.eq(dr_tmp[-1]),
        )

        self.bad_cmd_err = bad_cmd_err = Signal()
        cmd_fsm.act('bad_cmd_err',
            bad_cmd_err.eq(1),
        )

        self.cnt = cnt = Signal(16)
        self.sync.spi += cnt.eq(cnt + 1)

    @staticmethod
    def val4addr(addr: int) -> int:
        return (addr & 0xff) ^ ((addr >> 8) & 0xff) ^ ((addr >> 16) & 0xff) ^ ((addr >> 24) & 0xff)

    def get_memories(self):
        return self.flash_mem.get_memories()

    def get_csrs(self):
        return self.flash_mem.get_csrs()


class FlashEmuLite(Module):
    def __init__(self, cd_sys: ClockDomain, sigs: SPISigs, dram_port: LiteDRAMNativeReadPort,
                 sz_mbit: int, idcode: int, prefetch_bits = 6):
        self.spi_sigs = sigs
        self.dram_port = dram_port
        self.sz_mbit = sz_mbit
        self.idcode = idcode = Signal(24, reset=idcode)
        if prefetch_bits < 1:
            raise ValueError('prefetch_bits must be >= 1')
        self.prefetch_bits = prefetch_bits


        self.cd_spi = self.clock_domains.cd_spi = cd_spi = ClockDomain('spi')
        self.comb += ClockSignal('spi').eq(sigs.sclk & ~sigs.csn)
        self.specials.reset_syncer = AsyncResetSingleStageSynchronizer(cd_spi, sigs.csn)

        self.clock_domains.cd_spi_inv = cd_spi_inv = ClockDomain('spi_inv')
        self.comb += ClockSignal('spi_inv').eq(~ClockSignal('spi'))
        self.specials.reset_syncer_inv = AsyncResetSingleStageSynchronizer(cd_spi_inv, sigs.csn)

        self.eso = eso = Signal()
        self.eso_delayed = eso_delayed = Signal()
        self.sync.spi_inv += eso_delayed.eq(eso)
        self.comb += sigs.so.eq(eso_delayed)

        self.cmd_bit_cnt = cmd_bit_cnt = Signal(max=8, reset=1)
        self.cmd = cmd = Signal(8, reset=sigs.si, init=0)
        self.cmd_next = cmd_next = Signal(8)

        self.addr = addr = Signal(24)
        self.addr_next = addr_next = Signal(24)
        self.addr_cnt = addr_cnt = Signal(max=24)
        self.dr = dr = Signal(8)
        self.dr_bit_cnt = dr_bit_cnt = Signal(max=8)

        self.partial_addr_valid = paddr_valid = Signal()
        self.partial_addr_valid_sys = paddr_valid_sys = Signal()
        self.specials.paddr_valid_sync = MultiReg(paddr_valid, paddr_valid_sys, cd_sys.name)
        self.partial_addr = paddr = Signal(addr.nbits - prefetch_bits)
        self.partial_addr_fw = paddr_fw = Signal(addr.nbits)
        self.comb += paddr_fw.eq(Cat(C(0, prefetch_bits), paddr))

        self.submodules.flash_mem = flash_mem = FlashEmuDRAMLite(dram_port, prefetch_bits, paddr_fw, paddr_valid_sys)
        self.pfr_idx = pfr_idx = Signal(max=prefetch_bits)
        self.pfr_sel = pfr_sel = Signal(dram_port.data_width)
        self.nbytes_per_mt = dram_port.data_width//8
        self.byte_idx = byte_idx = Signal(max=self.nbytes_per_mt)
        self.byte_arr = byte_arr = Array([pfr_sel[i*8:(i+1)*8] for i in range(self.nbytes_per_mt)])
        self.byte_sel = byte_sel = Signal(8)
        self.comb += [
            pfr_idx.eq(addr[byte_idx.nbits:]),
            pfr_sel.eq(flash_mem.prefetch_regs[pfr_idx]),
            byte_idx.eq(addr[:byte_idx.nbits]),
            byte_sel.eq(byte_arr[byte_idx]),
        ]

        cmd_fsm = FSM(name='cmd_fsm', reset_state='get_cmd')
        cmd_fsm = ClockDomainsRenamer('spi')(cmd_fsm)
        self.submodules.cmd_fsm = cmd_fsm

        self.get_cmd_flag = get_cmd_flag = Signal()
        cmd_fsm.act('get_cmd',
            cmd_next.eq(Cat(sigs.si, cmd[:-1])),
            get_cmd_flag.eq(1),
            NextValue(cmd, cmd_next),
            NextValue(cmd_bit_cnt, cmd_bit_cnt + 1),

            If(cmd_bit_cnt == 7,
                If(cmd_next == CMD_READ,
                    NextState('read_get_addr'),
                ).Elif(cmd_next == CMD_RDID,
                    NextState('rdid'),
                ).Else(
                    NextState('bad_cmd_err'),
                )
            ),
        )

        cmd_fsm.act('rdid',
            eso.eq(idcode[-1]),
            NextValue(idcode, Cat(idcode[-1], idcode[:-1])),
        )

        cmd_fsm.act('read_get_addr',
            addr_next.eq(Cat(sigs.si, addr[:-1])),
            NextValue(addr, addr_next),
            NextValue(addr_cnt, addr_cnt + 1),
            If(addr_cnt == 23 - prefetch_bits,
                NextValue(paddr, addr_next),
            ),
            If(addr_cnt == 23 - (prefetch_bits - 1),
                paddr_valid.eq(1),
            ),
            If(addr_cnt == 23,
               NextState('read_get_data'),
            ),
        )

        self.dr_tmp = dr_tmp = Signal(8)
        cmd_fsm.act('read_get_data',
            If(dr_bit_cnt == 0,
                dr_tmp.eq(byte_sel)
            ).Else(
                dr_tmp.eq(dr)
            ),
            addr_next.eq(addr + 1),
            NextValue(dr_bit_cnt, dr_bit_cnt + 1),
            NextValue(dr, Cat(0, dr_tmp[:-1])),
            If(dr_bit_cnt == 7,
                NextValue(addr, addr_next),
            ),
            eso.eq(dr_tmp[-1]),
        )

        self.bad_cmd_err = bad_cmd_err = Signal()
        cmd_fsm.act('bad_cmd_err',
            bad_cmd_err.eq(1),
        )

        self.cnt = cnt = Signal(16)
        self.sync.spi += cnt.eq(cnt + 1)

    @staticmethod
    def val4addr(addr: int) -> int:
        return (addr & 0xff) ^ ((addr >> 8) & 0xff) ^ ((addr >> 16) & 0xff) ^ ((addr >> 24) & 0xff)
