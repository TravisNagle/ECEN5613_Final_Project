# File        : Makefile
# Author      : Nathan Cohen (drafted with AI assistance, Anthropic Claude)
# Revision    : 1, 2026-11-22
# Project     : ECEN 5613 final project, panel bench-test firmware
# Description : Builds build/bench_test.hex for the AT89C51RC2 with SDCC 4.6.0.
#                 make          build/bench_test.hex
#                 make clean    remove build/
#                 make flash COM_PORT=COM4    Windows only: FLIP's batchisp
#               Flashing: JP_RX in the PC position, hold SW3 (PSEN) through reset,
#               then move JP_RX back to KB afterwards. FLIP has no macOS build, so on
#               a Mac build here and flash the .hex from Windows or Linux.
# Leveraged   : my Lab 4 Makefile (flags and the batchisp command line)

CC      := sdcc
CFLAGS  := -mmcs51 --model-large --std-c11 -Isrc
# U4 (NVSRAM) is removed: only the 1 KB on-chip XRAM exists (AUXR = 0x0C)
LDFLAGS := -mmcs51 --model-large --code-loc 0x0000 --code-size 0x8000 \
           --xram-loc 0x0000 --xram-size 0x0400 --iram-size 0x100 --out-fmt-ihx

# main.c must come first: SDCC takes the entry module and vector table from it
SRCS    := src/main.c src/motor.c src/screen.c src/delay.c src/lcd.c src/i2c.c \
           src/eeprom.c src/mcp3008.c src/pcf8574.c
OBJS    := $(patsubst src/%.c,build/%.rel,$(SRCS))
HDRS    := $(wildcard src/*.h)

COM_PORT ?= COM3
ISP_BAUD ?= 57600

all: build/bench_test.hex

build/%.rel: src/%.c $(HDRS) | build
	$(CC) $(CFLAGS) -c $< -o $@

build/bench_test.ihx: $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) -o $@

build/bench_test.hex: build/bench_test.ihx
	packihx $< > $@

build:
	mkdir build

flash: build/bench_test.hex
	batchisp -device at89c51rc2 -hardware RS232 -port $(COM_PORT) -baudrate $(ISP_BAUD) -operation erase f memory flash blankcheck loadbuffer build/bench_test.hex program verify start reset 1

clean:
ifeq ($(OS),Windows_NT)
	if exist build rmdir /s /q build
else
	rm -rf build
endif

.PHONY: all flash clean
