"""Measure frame rectangles for a 4 x 3 enemy spritesheet.

Usage:  python tools/measure_frames.py "assets/Sprites/Enemies/Mire_Maw_Spritesheet/Mire_Maw.png"
Needs:  pip install numpy pillow   (only for this tool; the game doesn't need them)

The art on our sheets spills over the grid lines, so cutting exactly on the
grid grabs pieces of the neighbouring frames. Instead, near each grid line
this looks for the row/column with the FEWEST opaque pixels and cuts there.
Paste the printed lists into the enemy's 'frames' entry in enemies.py.
Anything that still pokes in from a neighbour is removed in-game by
sprites.clean_frame().
"""
import sys
import numpy as np
from PIL import Image

COLUMNS, ROWS = 4, 3
SEARCH = 70  # how far (pixels) either side of a grid line to look for a better cut


def best_cut(counts_for, grid_line, size):
    if grid_line <= 0 or grid_line >= size:
        return max(0, min(size, grid_line))
    candidates = range(max(1, grid_line - SEARCH), min(size - 1, grid_line + SEARCH))
    counts = [counts_for(i) for i in candidates]
    fewest = min(counts)
    best = [i for i, c in zip(candidates, counts) if c == fewest]
    return min(best, key=lambda i: abs(i - grid_line))  # closest to the grid line


def measure(path):
    alpha = np.array(Image.open(path).convert("RGBA"))[:, :, 3] > 127
    height, width = alpha.shape
    cell_w, cell_h = width / COLUMNS, height / ROWS
    rows = []
    for r in range(ROWS):
        gy0, gy1 = int(r * cell_h), int((r + 1) * cell_h)
        row = []
        for c in range(COLUMNS):
            gx0, gx1 = int(c * cell_w), int((c + 1) * cell_w)
            column_count = lambda x: alpha[gy0:gy1, x].sum()
            row_count = lambda y: alpha[y, gx0:gx1].sum()
            x0, x1 = best_cut(column_count, gx0, width), best_cut(column_count, gx1, width)
            y0, y1 = best_cut(row_count, gy0, height), best_cut(row_count, gy1, height)
            row.append((x0, y0, x1 - x0, y1 - y0))
        rows.append(row)
    return rows


if __name__ == "__main__":
    for name, row in zip(("idle", "hurt", "attack"), measure(sys.argv[1])):
        print(f"            '{name}': [" + ", ".join(str(tuple(int(v) for v in r)) for r in row) + "],")
