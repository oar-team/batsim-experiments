#!/usr/bin/ruby

freq = ENV['SLURM_CPU_FREQ_REQ'].to_i
dodo = ARGV[0].to_i

freq_max = 2700
freq_min = 2100

slowdown = 1.4


new_dodo = ( (1 - slowdown)*(freq- freq_min)/(freq_max - freq_min)+slowdown )*dodo

puts "freq: #{freq}\tsleep: #{dodo}\tslowdown: #{(1 - slowdown)*(freq- freq_min)/(freq_max - freq_min)+slowdown}\t new_dodo: #{new_dodo}\n"

sleep(new_dodo)