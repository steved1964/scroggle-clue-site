from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests

MIN_LEN = 4
API_URL = "https://www.dailyscroggle.com/api/scroggle/puzzle"
WORDS_FILE = Path(__file__).resolve().parent / "cleaned_words.txt"


class Node:
    __slots__ = ("children", "terminal")

    def __init__(self) -> None:
        self.children: Dict[str, "Node"] = {}
        self.terminal = False


class Trie:
    __slots__ = ("root",)

    def __init__(self) -> None:
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

    def step(self, n: Node, ch: str) -> Optional[Node]:
        return n.children.get(ch)


def load_trie(path: Path) -> Trie:
    t = Trie()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip().lower()
            if len(s) >= MIN_LEN and s.isalpha():
                t.add(s)
    return t


def fetch_letterlist() -> str:
    r = requests.get(API_URL, timeout=15)
    r.raise_for_status()
    j = r.json()
    s = j.get("LetterList", "")
    if not s:
        raise RuntimeError("Missing LetterList in API response")
    return s


def parse_grid(letter_list_str: str) -> List[List[str]]:
    chunks = letter_list_str.split()
    if len(chunks) != 7:
        raise RuntimeError("Unexpected puzzle format (cols != 7)")

    cols = [c.split(",") for c in chunks]
    if any(len(col) != 7 for col in cols):
        raise RuntimeError("Unexpected puzzle format (rows != 7)")

    flat: List[str] = []
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


def neighbor_offsets(col: int) -> List[Tuple[int, int]]:
    base = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    if col % 2 == 1:
        base.extend([(-1, -1), (-1, 1)])
    else:
        base.extend([(1, -1), (1, 1)])
    return base


def explore(
    grid: List[List[str]],
    trie: Trie,
    r: int,
    c: int,
    node: Node,
    buf: List[str],
    seen: Set[str],
    counts: defaultdict[str, int],
    visited: List[List[bool]],
) -> None:
    tile = grid[r][c]
    cur = node
    for ch in tile:
        cur = trie.step(cur, ch)
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
            explore(grid, trie, nr, nc, cur, buf, seen, counts, visited)

    buf.pop()
    visited[r][c] = False


def build_clue(counts: defaultdict[str, int]) -> str:
    parts = [f"{counts[k]}{k}" for k in sorted(counts.keys())]
    return (" ".join(parts) + " ✔️") if parts else "✔️"


def main() -> None:
    trie = load_trie(WORDS_FILE)
    grid = parse_grid(fetch_letterlist())

    counts: defaultdict[str, int] = defaultdict(int)
    seen: Set[str] = set()
    visited = [[False] * 7 for _ in range(7)]

    for rr in range(7):
        for cc in range(7):
            explore(grid, trie, rr, cc, trie.root, [], seen, counts, visited)

    print(f"Total: {len(seen)}")
    print(build_clue(counts))


if __name__ == "__main__":
    main()
