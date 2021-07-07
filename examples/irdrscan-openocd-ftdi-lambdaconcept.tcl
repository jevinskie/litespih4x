source [find fpga/altera-10m50.cfg]

gdb_port disabled
tcl_port disabled
telnet_port disabled
init

irscan 10m50.tap 0xc

puts "  DEADBEEF 32 RES: 0x[drscan 10m50.tap 32 0xDEADBEEF]"

puts "00DEADBEEF 40 RES: 0x[drscan 10m50.tap 40 0x00DEADBEEF]"

puts "00DEADBEEF 64 RES: 0x[drscan 10m50.tap 64 0x00000000DEADBEEF]"

puts "00DEADBEEF 80 RES: 0x[drscan 10m50.tap 80 0x000000000000DEADBEEF]"

shutdown
