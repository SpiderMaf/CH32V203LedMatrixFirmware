#!/usr/bin/env python3
"""Replace the four existing CHV LED bitmaps (15x16, 1 byte per pixel).

Built-in glyphs: LOVE and SUBS. Supply other glyphs with --glyphs JSON.
The JSON format is {"A": [16 strings of 15 '.' or '#' characters], ...}.
The script modifies bitmap bytes only, not animation or mode logic.
"""
import argparse
import json
from pathlib import Path

SIZE = 65536
WIDTH, HEIGHT = 15, 16
# Display order L,O,V,E. Data stored E,V,O,L in firmware.
OFFSETS = (0x4380, 0x4290, 0x41A0, 0x40B0)

GLYPHS = {'B': ['...............',
       '.##########....',
       '.###########...',
       '.##........###.',
       '.##.........##.',
       '.##.........##.',
       '.##........###.',
       '.###########...',
       '.###########...',
       '.##........###.',
       '.##.........##.',
       '.##.........##.',
       '.##........###.',
       '.###########...',
       '.##########....',
       '...............'],
 'E': ['...............',
       '..##########...',
       '..##########...',
       '..##...........',
       '..##...........',
       '..##...........',
       '..##...........',
       '..#########....',
       '..#########....',
       '..##...........',
       '..##...........',
       '..##...........',
       '..##...........',
       '..##########...',
       '..##########...',
       '...............'],
 'L': ['...............',
       '..##...........',
       '..##...........',
       '..##...........',
       '..##...........',
       '..##...........',
       '..##...........',
       '..##...........',
       '..##...........',
       '..##...........',
       '..##...........',
       '..##...........',
       '..##...........',
       '..###########..',
       '..###########..',
       '...............'],
 'O': ['...............',
       '...#########...',
       '..###########..',
       '.###.......###.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.###.......###.',
       '..###########..',
       '...#########...',
       '...............'],
 'S': ['...............',
       '...#########...',
       '..###########..',
       '.###.......###.',
       '.##............',
       '.##............',
       '.###...........',
       '..##########...',
       '...##########..',
       '...........###.',
       '............##.',
       '............##.',
       '.###.......###.',
       '..###########..',
       '...#########...',
       '...............'],
 'U': ['...............',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.##.........##.',
       '.###.......###.',
       '..###########..',
       '...#########...',
       '...............'],
 'V': ['...............',
       '...............',
       '##...........##',
       '##...........##',
       '.##.........##.',
       '.##.........##.',
       '..##.......##..',
       '..##.......##..',
       '...##.....##...',
       '...##.....##...',
       '....##...##....',
       '....##...##....',
       '.....##.##.....',
       '.....#####.....',
       '......###......',
       '...............']}

def validate_glyph(letter, rows):
    if not isinstance(rows, list) or len(rows) != HEIGHT:
        raise ValueError(f'{letter}: expected {HEIGHT} rows')
    if any(not isinstance(row, str) or len(row) != WIDTH or set(row) - set('.#') for row in rows):
        raise ValueError(f'{letter}: every row must be exactly {WIDTH} characters of . or #')
    return bytes(1 if c == '#' else 0 for row in rows for c in row)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--text', required=True, help='Exactly 4 characters, e.g. SUBS')
    p.add_argument('--glyphs', type=Path, help='Optional JSON file defining additional 15x16 glyphs')
    args = p.parse_args()
    if args.input.resolve() == args.output.resolve():
        p.error('Output must be different from input')
    letters = args.text.upper()
    if len(letters) != 4:
        p.error('--text must be exactly 4 characters')
    data = bytearray(args.input.read_bytes())
    if len(data) != SIZE:
        p.error(f'Expected {SIZE} bytes, got {len(data)}')
    glyphs = dict(GLYPHS)
    if args.glyphs:
        try:
            custom = json.loads(args.glyphs.read_text())
            if not isinstance(custom, dict):
                raise ValueError('Expected JSON object')
            glyphs.update(custom)
        except (ValueError, OSError) as exc:
            p.error(f'Cannot load glyphs: {exc}')
    for letter, offset in zip(letters, OFFSETS):
        if letter not in glyphs:
            p.error(f'No glyph for {letter!r}; supply --glyphs JSON')
        try:
            bitmap = validate_glyph(letter, glyphs[letter])
        except ValueError as exc:
            p.error(str(exc))
        existing = data[offset:offset+240]
        if set(existing) - {0, 1}:
            p.error(f'Unexpected non-bitmap data at 0x{offset:04X}; refusing to patch')
        data[offset:offset+240] = bitmap
        print(f'{letter}: 0x{offset:04X}, {sum(bitmap)} lit pixels')
    args.output.write_bytes(data)
    print('Wrote:', args.output, f'({len(data)} bytes)')

if __name__ == '__main__':
    main()
