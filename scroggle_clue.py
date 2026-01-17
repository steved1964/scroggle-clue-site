import sys
from collections import defaultdict
import requests

TERM_FILEPATH = "cleaned_words.txt"
MIN_LEN = 4
API_URL = "https://www.dailyscroggle.com/api/scroggle/puzzle"
OUTPUT_FILE = "clue.txt"


class Node:
    __slots__ = ("children", "terminal")
    def __init__(self):
        self.children = {}
        self.terminal = False


class Tree:
    __slots__ = ("root",)
    def __init__(self):
        self.root = Node()

    def add(self, s: str) -> None:
        n = self.root
        for ch in s:
            nxt = n.children.get(ch)
            if nxt is None:
                nxt = Node()
                n.children[ch] = nxt
            n = nxt
        n.terminal = True

    def step(self, n: Node, ch: str):
        return n.children.get(ch)


def load_tree(path: str) -> Tree:
    t = Tree()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip().lower()
                if len(s) >= MIN_LEN and s.isalpha():
                    t.add(s)
    except FileNotFoundError:
        sys.stdout.write(f"ERROR: missing {path}\n")
        sys.exit(1)
    except Exception:
        sys.stdout.write("ERROR: could not load file\n")
        sys.exit(1)
    return t


def fetch_letterlist() -> str:
    try:
        r = requests.get(API_URL, timeout=10)
        r.raise_for_status()
        j = r.json()
        s = j.get("LetterList", "")
        if not s:
            raise ValueError("missing LetterList")
        return s
    except Exception:
        sys.stdout.write("ERROR: could not fetch puzzle\n")
        sys.exit(1)


def parse_grid(letter_list_str: str):
    chunks = letter_list_str.split()
    if len(chunks) != 7:
        sys.stdout.write("ERROR: unexpected puzzle format\n")
        sys.exit(1)

    cols = [c.split(",") for c in chunks]
    for col in cols:
        if len(col) != 7:
            sys.stdout.write("ERROR: unexpected puzzle format\n")
            sys.exit(1)

    flat = []
    for col in cols:
        for tile in col:
            t = tile.strip().upper()
            flat.append("Q" if t in ("Q", "QU") else t)

    grid = [["" for _ in range(7)] for _ in range(7)]
    idx = 0
    for c in range(7):
        for r in range(7):
            ch = flat[idx]
            idx += 1
            grid[r][c] = "qu" if ch == "Q" else ch.lower()

    return grid


def neighbor_offsets(col: int):
    base = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    if col % 2 == 1:
        base.extend([(-1, -1), (-1, 1)])
    else:
        base.extend([(1, -1), (1, 1)])
    return base


def explore(grid, tree: Tree, r: int, c: int, node: Node, buf: list, seen: set, counts):
    tile = grid[r][c]

    cur = node
    for ch in tile:
        cur = tree.step(cur, ch)
        if cur is None:
            return

    visited[r][c] = True
    buf.append(tile)

    if cur.terminal:
        s = "".join(buf)
        if len(s) >= MIN_LEN and s not in seen:
            seen.add(s)
            counts[s[:2]] += 1

    for dr, dc in neighbor_offsets(c):
        nr, nc = r + dr, c + dc
        if 0 <= nr < 7 and 0 <= nc < 7 and not visited[nr][nc]:
            explore(grid, tree, nr, nc, cur, buf, seen, counts)

    buf.pop()
    visited[r][c] = False


def build_line(counts) -> str:
    parts = [f"{counts[k]}{k}" for k in sorted(counts.keys())]
    return (" ".join(parts) + " ✔️") if parts else "✔️"


if __name__ == "__main__":
    tree = load_tree(TERM_FILEPATH)
    grid = parse_grid(fetch_letterlist())

    counts = defaultdict(int)
    seen = set()

    visited = [[False] * 7 for _ in range(7)]

    for rr in range(7):
        for cc in range(7):
            explore(grid, tree, rr, cc, tree.root, [], seen, counts)

    total_line = f"Total: {len(seen)}"
    clue_line = build_line(counts)

    # Output: total on its own line, then the clue line
    sys.stdout.write(total_line + "\n")
    sys.stdout.write(clue_line + "\n")

    # Also write both lines to a file
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(total_line + "\n")
            f.write(clue_line + "\n")
    except Exception:
        pass

    # Keep the window open if you double-click the script
    try:
        input()
    except EOFError:
        pass
