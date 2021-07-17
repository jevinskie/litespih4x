gdb_port disabled
tcl_port disabled
telnet_port disabled

adapter driver remote_bitbang

verify_ircapture disable
verify_jtag disable

remote_bitbang_host localhost
remote_bitbang_port 2430

verify_ircapture disable
verify_jtag disable

jtag newtap sim tap -irlen 5 -expected-id 0x831050DD
verify_ircapture disable
verify_jtag disable

puts "scan_chain: [scan_chain]"

proc jtag_init {} {
	verify_ircapture disable
	verify_jtag disable
}

init

# puts "Waiting for Any Key"
# gets stdin

irscan sim.tap 0x2

# puts "Waiting for Any Key"
# gets stdin

puts "  IDCODE 32 RES: 0x[drscan sim.tap 32 0xDEADBEEF]"

# puts "00IDCODE 64 RES: 0x[drscan sim.tap 64 0x00000000DEADBEEF]"

# puts "00DEADBEEF 40 RES: 0x[drscan sim.tap 40 0x00DEADBEEF]"

# puts "00DEADBEEF 64 RES: 0x[drscan sim.tap 64 0x00000000DEADBEEF]"

# puts "00DEADBEEF 80 RES: 0x[drscan sim.tap 80 0x000000000000DEADBEEF]"

shutdown
