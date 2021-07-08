source [find interface/altera-usb-blaster2.cfg]
source [find fpga/altera-10m50.cfg]

gdb_port disabled
tcl_port disabled
telnet_port disabled
init

irscan 10m50.tap 0xc

puts "Waiting for Any Key"
gets stdin

irscan 10m50.tap 0xe

shutdown
