# Lab 3 memory map, and internal vs external XRAM on the AT89C51RC2

| Field | Value |
|---|---|
| File name | `memory_map_and_xram.md` |
| Author | Nathan Cohen |
| Course | ECEN 5613 Embedded System Design, Fall 2026 |
| Assignment | Lab 3, Step 3: 1 KB + 31 KB XRAM (Core). Supports Steps 4 and 5 |
| Target | AT89C51RC2 at 11.0592 MHz (/EA = Vcc), U7 ATF16V8B decode, U4 M48Z35Y NVSRAM |
| Leveraged | AT89C51RC2 datasheet (XRAM / AUXR / HSB sections); my `spld/lab3.pld`. Drafted with AI assistance (Anthropic Claude); reviewed/modified by the student. Acknowledge this per the honor code. |
| Status | DRAFTED, not yet verified on hardware |

---

## 1. Memory map

The 8051 has separate address spaces. The same address means different memory depending on the instruction:
**code** (instruction fetch / MOVC, read with /PSEN), **XRAM data** (MOVX, read/write with /RD and /WR),
**internal data** (MOV direct/indirect), and **SFRs** (direct 0x80-0xFF).

```
 CODE SPACE (/EA = Vcc)                         XRAM DATA SPACE (MOVX)
 0xFFFF +-------------------------------+       0xFFFF +-------------------------------+ <- Virtual Debug Port
        | external code: nothing        |              | nothing responds              |    (write-only marker
        | installed in Lab 3            |       0xF000 |  (CSPERIPH page, Lab 4)       |     for the logic analyzer)
        | (FLIP bootloader: separate    |              |                               |
        |  boot ROM, not in this map)   |              |  0xAA block-fill test region  |
 0x8000 +-------------------------------+       0x8000 +-------------------------------+
 0x7FFF +-------------------------------+ emem  0x7FFF +-------------------------------+
        | user programs                 |              |                               |
        | (SDCC code at 0x0000 when     |              |  U4 M48Z35Y NVSRAM, 31KB      |
        |  flashed alone; 0x2000/0x3000 |              |  /E = A15 # (RD & WR)         |
        |  when run under PAULMON)      |              |  /G = RD,  /W = /WR           |
 0x2000 +-------------------------------+ vector,pgm   |                               |
        | extra.asm (L, S, E commands)  |              |                               |
 0x1000 +-------------------------------+ bmem  0x0400 +-------------------------------+
        | PAULMON2 (base = 0x0000)      |              | internal XRAM 1KB             |
 0x0000 +-------------------------------+       0x0000 +-------------------------------+
   (32KB internal flash)                        (AUXR = 0x0C: XRS1:XRS0=11, EXTRAM=0)

 INTERNAL DATA: 0x00-0x7F direct/indirect (register banks, bits, variables)
                0x80-0xFF indirect only (stack in SDCC builds: SP starts 0x21, see .mem)
 SFRs:          0x80-0xFF direct only (AUXR = 0x8E, BRL = 0x9A, BDRCON = 0x9B, ...)
```

| Range (XRAM) | Device | Size | Selected by |
|---|---|---|---|
| 0x0000-0x03FF | Internal XRAM | 1 KB | AUXR XRS1:XRS0 = 11 and EXTRAM = 0. Internal access: /RD and /WR are not pulsed |
| 0x0400-0x7FFF | U4 M48Z35Y | 31 KB | SPLD: A15 = 0 and /RD or /WR low |
| 0x8000-0xFFFF | none | 32 KB | Open bus. 0xFFFF is the virtual debug port address (Step 5) |

Total usable XRAM: 1 KB + 31 KB = **32 KB = 0x8000** bytes. That is exactly what `--xram-size 0x8000` tells SDCC.

---

## 2. How internal vs external XRAM is selected

For every `MOVX` the CPU decides where the access goes:

```
           MOVX to address X
                 |
     EXTRAM (AUXR bit 1) = 1 ? ---yes---> external bus (ALE, P0/P2 address, /RD or /WR pulse)
                 | no
     X < internal XRAM size ? ---no----> external bus
     (256/512/768/1024 per XRS1:XRS0)
                 | yes
          internal XRAM: no /RD, no /WR, no bus cycle
          (P0/P2 are not driven as an address bus)
```

- **XRS1:XRS0** (AUXR bits 3:2) set the internal size: 00 = 256 B (**reset default**), 01 = 512 B, 10 = 768 B, 11 = 1024 B.
- **EXTRAM** (AUXR bit 1): 0 means internal XRAM is used for addresses in range, 1 means everything goes external.
- **HSB XRAM bit.** This configuration bit in the Hardware Security Byte is set with a programmer or ISP, not by code. It determines the **power-up value of EXTRAM**. Software can still write AUXR afterward, which is why both PAULMON2 and my C code write AUXR = 0x0C explicitly rather than relying on the fuse. **VERIFY** the datasheet HSB table wording.
- AUXR is **not bit-addressable**, so you can't use `SETB`. Write the whole byte, or use ORL/ANL.
- Every reset returns AUXR to its default (256 B). That's why the write has to sit in PAULMON's power-on code and in `__sdcc_external_startup()`, which run after every reset.
- `MOVX @Ri` (8-bit address, the `__pdata` page) also obeys these rules. The upper address byte comes from P2.

### Before AUXR is written (a subtle trap)
With only 256 internal bytes, a `MOVX` to 0x0100-0x03FF goes **outside** the chip. A15 = 0 there, and /RD or /WR pulses,
so the SPLD selects U4 and the access lands in U4's **physical** cells 0x0100-0x03FF. After AUXR is written, the same
addresses hit **internal** XRAM. These are two different memories at the same address, depending on timing. That's why:
- SDCC must enable XRAM in `__sdcc_external_startup()`, before the runtime clears and initializes `__xdata` variables.
- PAULMON2 must enable it as its very first instruction.

---

## 3. Why the low 1 KB of the SRAM is unused

U4 has 32 K cells (A0-A14). Its cells 0x0000-0x03FF are reachable only through XRAM addresses 0x0000-0x03FF, and after
AUXR is written those addresses are always serviced **internally**. The CPU never pulses /RD or /WR for them, so U4 is
never selected there. Those 1024 cells are **shadowed** and effectively unused.

The benefit (handout: "leaving 1KB of SRAM memory unused will simplify the decoding logic"): the chip select is just
**A15 = 0**, optionally qualified by the strobes. There's no need to decode A10-A14 to carve out 0x0000-0x03FF, which
would take five more SPLD inputs and a wider product term. 32 KB − 1 KB = 31 KB used.

(Optional challenge: the same shadowed 1 KB can be reused as an executable code window at 0x8000-0x83FF. See the
commented-out block in `spld/lab3.pld`.)

---

## 4. The virtual debug port at 0xFFFF (Step 5 preview)

- Nothing in the system responds to XRAM writes at 0xFFFF. A15 = 1, so U4 is deselected, and CSPERIPH has no device yet.
- So `*(volatile __xdata unsigned char *)0xFFFF = value;` is a harmless write that is **fully visible on the bus**: ALE latches 0xFF on P0, P2 = 0xFF, /WR pulses, and P0 carries `value` during /WR.
- A logic analyzer triggered on /WR low with address = 0xFFFF captures `value`. This is a "printf" with no UART and almost no time cost (a single MOVX, about 2 µs).
- The optional SPLD output `VDP_WR_n` (U7 pin 16) goes low only for writes to 0xF000-0xFFFF, which makes a convenient trigger.
- Because the low byte comes through the '373, use the latched A0-A7 (or AD0-AD7 sampled at the ALE falling edge) for the address and AD0-AD7 sampled while /WR is low for the data.
- It must stay **outside** `--xram-size`. With 0x8000 it does, so the linker will never place a variable there.

---

## 5. Likely TA questions

| Question | Answer |
|---|---|
| Why does /E = A15 work even though U4 also has cells at 0x0000-0x03FF? | After AUXR = 0x0C, MOVX to 0x0000-0x03FF stays internal and doesn't pulse /RD or /WR. U4 is never asked for those cells, so they're simply unused (shadowed). |
| Why qualify /E with /RD and /WR? | So U4 is enabled only during real external data cycles. That means lower power, and both /E and /W must be low to write, so a glitch on one line can't corrupt memory. It costs one SPLD delay (≤ 15 ns) against a 287 ns read budget. The tradeoff is spelled out in `lab3.pld`. |
| Why isn't /PSEN connected to U4 any more? | In Lab 3, U4 is data memory. Code below 0x8000 comes from internal flash (/EA = Vcc), and nothing in Lab 3 executes from U4. |
| What happens if you forget the AUXR write? | Only 256 B are internal. MOVX to 0x0100-0x03FF goes to U4's shadowed cells. Fill tests may still "pass", but the 1 KB internal XRAM isn't being used, and C globals can be initialized in one memory and then read from the other. |
| What is EXTRAM for? | It forces all MOVX accesses external, for example to use the full external chip from 0x0000. It must be 0 for this lab. |
| What does the HSB XRAM bit do? | It sets the reset value of EXTRAM (internal XRAM on or off at power-up). Code can override it through AUXR. |
| Where are SDCC's large-model variables? | XSEG at 0x0000-0x0040 in `hello.map` (65 bytes), which is internal XRAM. The stack is in internal RAM at 0x21-0xFF (`hello.mem`). |
| Why is `--xram-size 0x8000` correct? | 0x0000-0x7FFF is all enabled (1 KB + 31 KB). If AUXR weren't written, 0x8000 would still be "correct" in size, but 0x0100-0x03FF would be the wrong memory. If you only had internal XRAM, you'd have to use 0x400. |
| Can PAULMON2 run code downloaded with `D`? | No. `D` writes data space with MOVX. Fetches use /PSEN, which reads internal flash below 0x8000 and nothing above. |
| What responds at 0x8000-0xFFFF? | Nothing. A dump there shows floating-bus values (often 0xFF or the last address byte), not the 0xAA that was written. |
| Why do the NVSRAM contents survive power-off? | The M48Z35Y has an internal lithium cell, and its control circuit write-protects and deselects the chip when Vcc drops below the power-fail threshold. Internal XRAM loses its data. |
| Heap note for Part 2 | With SDCC 4.6, if `___sdcc_heap` is linked at 0x0000, `malloc()` always returns NULL (the free-list pointer value 0 means "none"). Check the `.map`, or use `--xram-loc 0x0100`. |
