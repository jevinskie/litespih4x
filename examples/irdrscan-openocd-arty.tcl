interface ftdi
ftdi_vid_pid 0x0403 0x6010
ftdi_channel 0
ftdi_layout_init 0x00e8 0x60eb
# ftdi_tdo_sample_edge falling
reset_config none

source [find cpld/xilinx-xc7.cfg]
source [find cpld/jtagspi.cfg]
adapter speed 5000

gdb_port disabled
tcl_port disabled
telnet_port disabled
init

puts "Waiting for Any Key"
gets stdin

irscan xc7.tap 0x2

puts "Waiting for Any Key"
gets stdin

puts "  DEADBEEF 32 RES: 0x[drscan xc7.tap 32 0xDEADBEEF]"

puts "00DEADBEEF 40 RES: 0x[drscan xc7.tap 40 0x00DEADBEEF]"

puts "00DEADBEEF 64 RES: 0x[drscan xc7.tap 64 0x00000000DEADBEEF]"

puts "00DEADBEEF 80 RES: 0x[drscan xc7.tap 80 0x000000000000DEADBEEF]"

shutdown
