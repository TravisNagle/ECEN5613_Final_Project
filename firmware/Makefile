# File        : Makefile
# Author      : Travis Nagle (drafted with AI assistance, Anthropic Claude)
# Revision    : 1, 2026-11-02
# Project     : ECEN 5613 final project, 8051 firmware
# Description : Builds build/main.hex for the AT89C51RC2 with SDCC 4.6.0.
#                 make         build/main.hex, ready for FLIP
#                 make clean   remove build/
#               Flash with JP_RX in the PC position and SW3 (PSEN) held
#               through reset; move JP_RX back to KB afterwards.
# Leveraged   : none

CC      := sdcc
CFLAGS  := -mmcs51 --model-large
# U4 (NVSRAM) is removed, so only the 1 KB on-chip XRAM exists (AUXR = 0x0C).
LDFLAGS := $(CFLAGS) --xram-size 0x0400 --code-size 0x8000 --iram-size 256

# main.c must come first: SDCC takes the program's entry module from the first object.
SRCS    := src/main.c src/tick.c src/uart.c src/midi.c src/adc.c
OBJS    := $(patsubst src/%.c,build/%.rel,$(SRCS))
HDRS    := $(wildcard src/*.h)

all: build/main.hex

build/%.rel: src/%.c $(HDRS) | build
	$(CC) $(CFLAGS) -c $< -o $@

build/main.ihx: $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) -o $@

build/main.hex: build/main.ihx
	packihx $< > $@

build:
	mkdir build

clean:
ifeq ($(OS),Windows_NT)
	if exist build rmdir /s /q build
else
	rm -rf build
endif

.PHONY: all clean
