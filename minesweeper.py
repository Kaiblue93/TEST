#!/usr/bin/env python3
"""터미널에서 플레이 가능한 지뢰찾기 게임."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable


@dataclass
class GameConfig:
    rows: int = 9
    cols: int = 9
    mines: int = 10


class Minesweeper:
    def __init__(self, config: GameConfig) -> None:
        if config.rows <= 0 or config.cols <= 0:
            raise ValueError("rows와 cols는 1 이상이어야 합니다.")
        if config.mines <= 0 or config.mines >= config.rows * config.cols:
            raise ValueError("mines는 전체 칸 수보다 작고 1 이상이어야 합니다.")

        self.config = config
        self.board = [[0 for _ in range(config.cols)] for _ in range(config.rows)]
        self.visible = [[False for _ in range(config.cols)] for _ in range(config.rows)]
        self.flagged = [[False for _ in range(config.cols)] for _ in range(config.rows)]
        self.mines: set[tuple[int, int]] = set()
        self.initialized = False
        self.game_over = False
        self.win = False

    def _neighbors(self, r: int, c: int) -> Iterable[tuple[int, int]]:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.config.rows and 0 <= nc < self.config.cols:
                    yield nr, nc

    def _place_mines(self, safe_r: int, safe_c: int) -> None:
        forbidden = {(safe_r, safe_c), *self._neighbors(safe_r, safe_c)}
        candidates = [
            (r, c)
            for r in range(self.config.rows)
            for c in range(self.config.cols)
            if (r, c) not in forbidden
        ]
        if len(candidates) < self.config.mines:
            candidates = [
                (r, c)
                for r in range(self.config.rows)
                for c in range(self.config.cols)
                if (r, c) != (safe_r, safe_c)
            ]

        self.mines = set(random.sample(candidates, self.config.mines))

        for r, c in self.mines:
            self.board[r][c] = -1
        for r in range(self.config.rows):
            for c in range(self.config.cols):
                if self.board[r][c] == -1:
                    continue
                self.board[r][c] = sum((nr, nc) in self.mines for nr, nc in self._neighbors(r, c))

        self.initialized = True

    def reveal(self, r: int, c: int) -> None:
        if self.game_over:
            return
        if not (0 <= r < self.config.rows and 0 <= c < self.config.cols):
            raise ValueError("좌표가 보드 범위를 벗어났습니다.")
        if self.flagged[r][c] or self.visible[r][c]:
            return

        if not self.initialized:
            self._place_mines(r, c)

        if (r, c) in self.mines:
            self.visible[r][c] = True
            self.game_over = True
            self.win = False
            return

        queue = [(r, c)]
        while queue:
            cr, cc = queue.pop()
            if self.visible[cr][cc] or self.flagged[cr][cc]:
                continue
            self.visible[cr][cc] = True
            if self.board[cr][cc] == 0:
                for nr, nc in self._neighbors(cr, cc):
                    if not self.visible[nr][nc] and (nr, nc) not in self.mines:
                        queue.append((nr, nc))

        self._check_win()

    def toggle_flag(self, r: int, c: int) -> None:
        if self.game_over:
            return
        if not (0 <= r < self.config.rows and 0 <= c < self.config.cols):
            raise ValueError("좌표가 보드 범위를 벗어났습니다.")
        if self.visible[r][c]:
            return
        self.flagged[r][c] = not self.flagged[r][c]

    def _check_win(self) -> None:
        hidden_non_mine = 0
        for r in range(self.config.rows):
            for c in range(self.config.cols):
                if (r, c) not in self.mines and not self.visible[r][c]:
                    hidden_non_mine += 1
        if hidden_non_mine == 0:
            self.game_over = True
            self.win = True

    def render(self, reveal_all: bool = False) -> str:
        header = "    " + " ".join(f"{c:2d}" for c in range(self.config.cols))
        lines = [header, "   " + "---" * self.config.cols]
        for r in range(self.config.rows):
            cells = []
            for c in range(self.config.cols):
                if reveal_all and (r, c) in self.mines:
                    cell = " *"
                elif self.flagged[r][c]:
                    cell = " F"
                elif not self.visible[r][c]:
                    cell = " ."
                elif self.board[r][c] == 0:
                    cell = "  "
                else:
                    cell = f" {self.board[r][c]}"
                cells.append(cell)
            lines.append(f"{r:2d}|" + "".join(cells))
        return "\n".join(lines)


HELP_TEXT = """
명령어:
  r <행> <열>   : 칸 열기 (reveal)
  f <행> <열>   : 깃발 토글 (flag)
  h             : 도움말
  q             : 종료

예시:
  r 3 4
  f 2 1
""".strip()


def read_int(prompt: str, default: int) -> int:
    raw = input(f"{prompt} [기본값 {default}]: ").strip()
    if not raw:
        return default
    value = int(raw)
    if value <= 0:
        raise ValueError("양의 정수를 입력하세요.")
    return value


def main() -> None:
    print("=== 지뢰찾기 CLI ===")
    print("엔터를 누르면 기본 난이도(9x9, 지뢰 10개)로 시작합니다.")

    try:
        rows = read_int("행 수", 9)
        cols = read_int("열 수", 9)
        max_mines = rows * cols - 1
        mines = read_int("지뢰 수", 10)
        if mines >= max_mines:
            raise ValueError(f"지뢰 수는 {max_mines - 1} 이하로 입력하세요.")
    except ValueError as exc:
        print(f"입력 오류: {exc}")
        return

    game = Minesweeper(GameConfig(rows=rows, cols=cols, mines=mines))
    print(HELP_TEXT)

    while True:
        print()
        print(game.render(reveal_all=game.game_over and not game.win))

        if game.game_over:
            if game.win:
                print("\n🎉 승리! 모든 안전 칸을 열었습니다.")
            else:
                print("\n💥 게임 오버! 지뢰를 밟았습니다.")
            break

        cmd = input("\n명령 입력 > ").strip().lower()
        if not cmd:
            continue
        if cmd == "q":
            print("게임을 종료합니다.")
            break
        if cmd == "h":
            print(HELP_TEXT)
            continue

        parts = cmd.split()
        if len(parts) != 3 or parts[0] not in {"r", "f"}:
            print("잘못된 명령어입니다. h를 입력해 도움말을 확인하세요.")
            continue

        action, rs, cs = parts
        try:
            r, c = int(rs), int(cs)
            if action == "r":
                game.reveal(r, c)
            else:
                game.toggle_flag(r, c)
        except ValueError as exc:
            print(f"입력 오류: {exc}")


if __name__ == "__main__":
    main()
