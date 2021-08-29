#!/usr/bin/env python3

import math

from rich import print

dfi_latency = 8
clk_ratio = 4
word_width = 16

def sys_clk_for_read_n(n):
    return dfi_latency + n

def sys_clk_to_read_n(n):
    return n - dfi_latency



for i in range(0):
    sys_lat = dfi_latency + i
    spi_lat = sys_lat / 4
    num_guesses = 2**spi_lat
    num_bytes = word_width * (i+1)
    print(f'latency: {sys_lat} sys clk, {spi_lat} spi clk num bytes: {num_bytes} num guesses: {num_guesses}')

for i in range(10):
    num_guesses = 2**i
    spi_clks = i
    sys_clks = clk_ratio * spi_clks
    n_reads = sys_clk_to_read_n(sys_clks) + 1
    num_bytes = word_width * n_reads
    n_reads_to_get_guesses = math.ceil(num_guesses / word_width)
    sys_clks_to_get_guesses = sys_clk_for_read_n(n_reads_to_get_guesses-1)
    slack_sys_clks = sys_clks - sys_clks_to_get_guesses
    print(f'spi clk: {spi_clks} # guesses: {num_guesses} sys clks: {sys_clks} # read TX: {n_reads} # bytes readahead: {num_bytes}')
    print(f'# reads to get guesses: {n_reads_to_get_guesses} # sys clks: {sys_clks_to_get_guesses}')
    print(f'slack sys clks: {slack_sys_clks}')
    print()

