# Build the firmware simulator from the real sketch and the generated header.
#
#   make            -> ./sim  (uses ../../firmware/robot_mcu)
#   make FW=/path   -> a sketch folder elsewhere (tests use this)
#
# Needs only g++ (sudo apt install build-essential).

FW ?= ../../firmware/robot_mcu
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wno-unused-function -Wno-unused-variable

sim: sim.cpp Arduino.h $(FW)/robot_mcu.ino $(FW)/robot_config.h
	g++ $(CXXFLAGS) -DENCODER_BACKEND=ENC_ISR -I. -I$(FW) \
	    -x c++ $(FW)/robot_mcu.ino -x c++ sim.cpp -o sim

clean:
	rm -f sim

.PHONY: clean
