#!/usr/bin/env python3
"""CH32V203 CHV firmware: selectively omit the HEART mode (verified patch).

This is intentionally not a general-purpose RISC-V state-machine rewriter.
Other combinations need separately verified instruction patches.
"""
import argparse
from pathlib import Path

SIZE = 65536
# Expected bytes at the two verified modification sites.
CHANGES = (
    (0x1F1E, bytes.fromhex('04'), bytes.fromhex('f4')),
    (0x1F25, bytes.fromhex('f0 9f dc'), bytes.fromhex('e0 6f f2')),
)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path, help='Original or previously patched 64 KiB dump')
    p.add_argument('output', type=Path, help='New binary file (never overwrites input)')
    p.add_argument('--omit', choices=['heart', 'none'], required=True,
                   help='heart: skip mode 0 during cycling; none: make no changes')
    args = p.parse_args()
    if args.input.resolve() == args.output.resolve():
        p.error('Output must be a different file from input')
    data = bytearray(args.input.read_bytes())
    if len(data) != SIZE:
        p.error(f'Expected {SIZE} bytes, got {len(data)}')
    if args.omit == 'heart':
        statuses = []
        for off, old, new in CHANGES:
            found = bytes(data[off:off+len(old)])
            if found == old:
                statuses.append('original')
            elif found == new:
                statuses.append('already patched')
            else:
                p.error(f'Unexpected bytes at 0x{off:04X}: {found.hex(" ")}; refusing to patch')
        if len(set(statuses)) > 1:
            p.error('Mixed original/patched instructions; refusing inconsistent input')
        for off, _, new in CHANGES:
            data[off:off+len(new)] = new
        print('Heart-skip patch:', statuses[0], '-> patched')
        print('Changes: 0x1F1E and 0x1F25..0x1F27 (4 bytes total)')
    else:
        print('No mode changes requested')
    args.output.write_bytes(data)
    print('Wrote:', args.output, f'({len(data)} bytes)')
    print('Note: saved startup mode is NOT modified; a stored heart mode may still start.')

if __name__ == '__main__':
    main()
