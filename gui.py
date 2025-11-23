import os
import sys
from typing import Tuple, Optional, List

import numpy as np
import pygame

from environment import (
    ShoverWorldEnv,
    EMPTY,
    LAVA,
    BARRIER,
    BOX_MIN,
    BOX_MAX,
    DIRECTION_VECS,
)

CELL_SIZE = 64
HUD_HEIGHT = 90
FPS = 30


class AnimatedGif:
    def __init__(self, path: str, size: Optional[Tuple[int, int]] = None):
        self.frames: List[pygame.Surface] = []
        self.durations: List[int] = []
        self.total_duration: int = 0
        self.index: int = 0
        self.time_acc: int = 0

        try:
            from PIL import Image
        except ImportError:
            self._load_static(path, size)
            return

        if not os.path.exists(path):
            self._make_placeholder(size)
            return

        try:
            img = Image.open(path)
        except Exception:
            self._load_static(path, size)
            return

        try:
            while True:
                frame = img.convert("RGBA")
                mode_str = frame.tobytes()
                py_img = pygame.image.fromstring(
                    mode_str, frame.size, "RGBA"
                ).convert_alpha()
                if size is not None:
                    py_img = pygame.transform.smoothscale(py_img, size)
                duration = img.info.get("duration", 80)
                self.frames.append(py_img)
                self.durations.append(max(duration, 20))
                self.total_duration += max(duration, 20)
                img.seek(img.tell() + 1)
        except EOFError:
            pass

        if not self.frames:
            self._load_static(path, size)
        else:
            if self.total_duration <= 0:
                self.durations = [80] * len(self.frames)
                self.total_duration = 80 * len(self.frames)

    def _load_static(self, path: str, size: Optional[Tuple[int, int]]):
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            if size is not None:
                img = pygame.transform.smoothscale(img, size)
        else:
            img = pygame.Surface(size or (64, 64), pygame.SRCALPHA)
            img.fill((255, 0, 255, 160))
        self.frames = [img]
        self.durations = [100]
        self.total_duration = 100

    def _make_placeholder(self, size: Optional[Tuple[int, int]]):
        surf = pygame.Surface(size or (64, 64), pygame.SRCALPHA)
        surf.fill((255, 0, 255, 160))
        self.frames = [surf]
        self.durations = [100]
        self.total_duration = 100

    def update(self, dt_ms: int) -> None:
        if len(self.frames) <= 1:
            return
        self.time_acc = (self.time_acc + dt_ms) % self.total_duration
        t = self.time_acc
        cumulative = 0
        for i, dur in enumerate(self.durations):
            cumulative += dur
            if t < cumulative:
                self.index = i
                break

    def get_frame(self) -> pygame.Surface:
        return self.frames[self.index]


def draw_scene(
    screen: pygame.Surface,
    env: ShoverWorldEnv,
    img_space: pygame.Surface,
    img_box: pygame.Surface,
    img_barrier: pygame.Surface,
    lava_bg: AnimatedGif,
    selected_cell: Optional[Tuple[int, int]],
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    total_reward: float,
    dt_ms: int,
    show_overlay: bool = False,
    overlay_text: Optional[str] = None,
):
    n_rows, n_cols = env.grid.shape
    width, height = screen.get_size()

    lava_bg.update(dt_ms)

    for y in range(height):
        t = y / max(1, height)
        r = int(10 + 80 * t)
        g = int(10 + 40 * t)
        b = int(30 + 60 * (1 - t))
        pygame.draw.line(screen, (r, g, b), (0, y), (width, y))

    pygame.draw.rect(screen, (20, 22, 40), (0, 0, width, HUD_HEIGHT))

    hud1 = (
        f"t={env.timestep}  stamina={env.stamina:.1f}  "
        f"boxes={env._count_boxes()}"
    )
    hud2 = "Click box: select | Arrows/WASD: push | B: Barrier | H: Hellify | Esc: menu"
    surf1 = font.render(hud1, True, (240, 240, 255))
    surf2 = small_font.render(hud2, True, (210, 210, 230))
    surf3 = small_font.render(
        f"Episode return: {total_reward:.1f}", True, (255, 220, 120)
    )
    screen.blit(surf1, (10, 5))
    screen.blit(surf2, (10, 30))
    screen.blit(surf3, (10, 55))

    grid_w = n_cols * CELL_SIZE
    grid_h = n_rows * CELL_SIZE
    lava_w = width
    lava_h = height - HUD_HEIGHT

    lava_frame = lava_bg.get_frame()
    screen.blit(lava_frame, (0, HUD_HEIGHT))

    grid_x = (lava_w - grid_w) // 2
    grid_y = HUD_HEIGHT + (lava_h - grid_h) // 2

    for r in range(n_rows):
        for c in range(n_cols):
            x = grid_x + c * CELL_SIZE
            y = grid_y + r * CELL_SIZE
            val = env.grid[r, c]
            if val == LAVA:
                continue
            elif val == BARRIER:
                img = img_barrier
            elif BOX_MIN <= val <= BOX_MAX:
                img = img_box
            else:
                img = img_space
            screen.blit(img, (x, y))

    pygame.draw.rect(
        screen,
        (255, 90, 10),
        (grid_x, grid_y, grid_w, grid_h),
        4,
        border_radius=6,
    )

    for r in range(n_rows + 1):
        y = grid_y + r * CELL_SIZE
        pygame.draw.line(screen, (60, 60, 90), (grid_x, y), (grid_x + grid_w, y))
    for c in range(n_cols + 1):
        x = grid_x + c * CELL_SIZE
        pygame.draw.line(
            screen,
            (60, 60, 90),
            (x, grid_y),
            (x, grid_y + grid_h),
        )

    if selected_cell is not None:
        sr, sc = selected_cell
        if 0 <= sr < n_rows and 0 <= sc < n_cols:
            x = grid_x + sc * CELL_SIZE
            y = grid_y + sr * CELL_SIZE
            pygame.draw.rect(
                screen, (255, 255, 0), (x, y, CELL_SIZE, CELL_SIZE), 3
            )

    if show_overlay and overlay_text is not None:
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))

        text1 = font.render(overlay_text, True, (255, 255, 255))
        text2 = small_font.render(
            "Press Enter / Space / click to return to menu", True, (255, 230, 180)
        )
        rect1 = text1.get_rect(center=(width // 2, height // 2 - 10))
        rect2 = text2.get_rect(center=(width // 2, height // 2 + 20))
        screen.blit(text1, rect1)
        screen.blit(text2, rect2)


def animate_move_effect(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    env: ShoverWorldEnv,
    img_space: pygame.Surface,
    img_box: pygame.Surface,
    img_barrier: pygame.Surface,
    lava_bg: AnimatedGif,
    move_effect: AnimatedGif,
    start_cell: Tuple[int, int],
    end_cell: Tuple[int, int],
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    selected_cell: Optional[Tuple[int, int]],
    total_reward: float,
):
    n_rows, n_cols = env.grid.shape
    width, height = screen.get_size()
    grid_w = n_cols * CELL_SIZE
    grid_h = n_rows * CELL_SIZE
    lava_w = width
    lava_h = height - HUD_HEIGHT
    grid_x = (lava_w - grid_w) // 2
    grid_y = HUD_HEIGHT + (lava_h - grid_h) // 2

    duration_ms = 280
    elapsed = 0

    start_x = grid_x + start_cell[1] * CELL_SIZE + CELL_SIZE / 2
    start_y = grid_y + start_cell[0] * CELL_SIZE + CELL_SIZE / 2
    end_x = grid_x + end_cell[1] * CELL_SIZE + CELL_SIZE / 2
    end_y = grid_y + end_cell[0] * CELL_SIZE + CELL_SIZE / 2

    running = True
    while running and elapsed < duration_ms:
        dt = clock.tick(FPS * 2)
        elapsed += dt

        lava_bg.update(dt)
        move_effect.update(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        draw_scene(
            screen,
            env,
            img_space,
            img_box,
            img_barrier,
            lava_bg,
            selected_cell,
            font,
            small_font,
            total_reward,
            dt_ms=dt,
            show_overlay=False,
            overlay_text=None,
        )

        t = min(1.0, elapsed / duration_ms)
        x = start_x * (1 - t) + end_x * t
        y = start_y * (1 - t) + end_y * t

        frame = move_effect.get_frame()
        rect = frame.get_rect(center=(int(x), int(y)))
        screen.blit(frame, rect)

        pygame.display.flip()


def game_loop(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    map_path: Optional[str],
    main_font: pygame.font.Font,
    small_font: pygame.font.Font,
) -> Optional[str]:
    n_rows = 8
    n_cols = 8

    env = ShoverWorldEnv(
        render_mode=None,
        n_rows=n_rows,
        n_cols=n_cols,
        map_path=map_path,
        initial_force=40.0,
        unit_force=10.0,
        edge_lava=True,
    )

    env.reset()
    n_rows, n_cols = env.grid.shape

    hud_font = pygame.font.SysFont("consolas", 22, bold=True)
    hud_small_font = pygame.font.SysFont("consolas", 14)

    assets_dir = os.path.join(os.path.dirname(__file__), "assets")

    def load_img(name: str, fallback_color: Tuple[int, int, int]):
        path = os.path.join(assets_dir, name)
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(img, (CELL_SIZE, CELL_SIZE))
        surf = pygame.Surface((CELL_SIZE, CELL_SIZE))
        surf.fill(fallback_color)
        return surf

    img_space = load_img("space.png", (240, 235, 220))
    img_box = load_img("box.png", (188, 120, 60))
    img_barrier = load_img("barrier.png", (70, 70, 80))

    width, height = screen.get_size()
    lava_w = width
    lava_h = height - HUD_HEIGHT

    lava_bg_path = os.path.join(assets_dir, "lava_bg.gif")
    move_eff_path = os.path.join(assets_dir, "move_effect.gif")
    lava_bg = AnimatedGif(lava_bg_path, size=(lava_w, lava_h))
    move_effect = AnimatedGif(move_eff_path, size=(CELL_SIZE, CELL_SIZE))

    scream_path = os.path.join(assets_dir, "scream.wav")
    if os.path.exists(scream_path):
        scream_snd = pygame.mixer.Sound(scream_path)
    else:
        scream_snd = None
        print("Warning: scream.wav not found in assets!")

    dissolve_path = os.path.join(assets_dir, "dissolve.wav")
    if os.path.exists(dissolve_path):
        dissolve_snd = pygame.mixer.Sound(dissolve_path)
    else:
        dissolve_snd = None

    def find_first_box() -> Optional[Tuple[int, int]]:
        positions = np.argwhere((env.grid >= BOX_MIN) & (env.grid <= BOX_MAX))
        if len(positions) == 0:
            return None
        r, c = map(int, positions[0])
        return (r, c)

    selected_cell: Optional[Tuple[int, int]] = find_first_box()
    total_reward = 0.0
    episode_result: Optional[str] = None

    running_game = True
    while running_game:
        dt = clock.tick(FPS)

        action_to_take: Optional[int] = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running_game = False
                    episode_result = None
                    break

                if event.key == pygame.K_r:
                    env.reset()
                    n_rows, n_cols = env.grid.shape
                    lava_bg = AnimatedGif(lava_bg_path, size=(lava_w, lava_h))
                    selected_cell = find_first_box()
                    total_reward = 0.0
                    continue

                if event.key in (pygame.K_UP, pygame.K_w):
                    action_to_take = 1
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    action_to_take = 2
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    action_to_take = 3
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    action_to_take = 4
                elif event.key == pygame.K_b:
                    action_to_take = 5
                elif event.key == pygame.K_h:
                    action_to_take = 6

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                grid_w = n_cols * CELL_SIZE
                grid_h = n_rows * CELL_SIZE
                grid_x = (lava_w - grid_w) // 2
                grid_y = HUD_HEIGHT + (lava_h - grid_h) // 2

                if grid_y <= my < grid_y + n_rows * CELL_SIZE:
                    if grid_x <= mx < grid_x + n_cols * CELL_SIZE:
                        c = (mx - grid_x) // CELL_SIZE
                        r = (my - grid_y) // CELL_SIZE
                        if 0 <= r < n_rows and 0 <= c < n_cols:
                            if BOX_MIN <= env.grid[r, c] <= BOX_MAX:
                                selected_cell = (int(r), int(c))

        if not running_game:
            break

        if action_to_take is not None:
            if 1 <= action_to_take <= 4:
                if (
                    selected_cell is None
                    or not (BOX_MIN <= env.grid[selected_cell[0], selected_cell[1]] <= BOX_MAX)
                ):
                    action_to_take = None

        if action_to_take is not None:
            if selected_cell is not None:
                sr, sc = selected_cell
            else:
                sr, sc = env.agent_row, env.agent_col

            if selected_cell is not None and 1 <= action_to_take <= 4:
                if action_to_take == 1: 
                    env.agent_row = sr + 1
                    env.agent_col = sc
                elif action_to_take == 3: 
                    env.agent_row = sr - 1
                    env.agent_col = sc
                elif action_to_take == 2: 
                    env.agent_row = sr
                    env.agent_col = sc - 1
                elif action_to_take == 4: 
                    env.agent_row = sr
                    env.agent_col = sc + 1

            pos = np.array([sr, sc], dtype=np.int64)
            z = action_to_take - 1
            obs, reward, done, info = env.step((pos, z))
            total_reward += reward

            if info.get("lava_destroyed_this_step", 0) > 0:
                if scream_snd:
                    scream_snd.play()

            dissolved = info.get("dissolved_squares") or []
            if dissolved and len(dissolved) > 0:
                if dissolve_snd:
                    dissolve_snd.play()
                print(f"Dissolution / special square change: {dissolved}")

            if (
                selected_cell is not None
                and 1 <= action_to_take <= 4
                and info.get("last_action_valid", False)
                and info.get("chain_length", 0) > 0
            ):
                dr, dc = DIRECTION_VECS[action_to_take]
                new_sr = sr + dr
                new_sc = sc + dc
                if 0 <= new_sr < n_rows and 0 <= new_sc < n_cols:
                    animate_move_effect(
                        screen,
                        clock,
                        env,
                        img_space,
                        img_box,
                        img_barrier,
                        lava_bg,
                        move_effect,
                        start_cell=(sr, sc),
                        end_cell=(new_sr, new_sc),
                        font=hud_font,
                        small_font=hud_small_font,
                        selected_cell=selected_cell,
                        total_reward=total_reward,
                    )
                    if BOX_MIN <= env.grid[new_sr, new_sc] <= BOX_MAX:
                        selected_cell = (new_sr, new_sc)
                    else:
                        selected_cell = None
                else:
                    selected_cell = None

            if done:
                num_boxes = info.get("number_of_boxes", env._count_boxes())
                if num_boxes == 0:
                    episode_result = "win"
                    text = "YOU WON! All boxes cleared."
                elif env.stamina <= 0:
                    episode_result = "loss"
                    text = "YOU LOST! Stamina ran out."
                elif env.timestep >= env.max_timestep:
                    episode_result = "loss"
                    text = "YOU LOST! Time limit reached."
                else:
                    episode_result = "loss"
                    text = "Episode finished."

                waiting = True
                while waiting:
                    dt2 = clock.tick(FPS)
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()
                        elif event.type == pygame.KEYDOWN:
                            if event.key in (
                                pygame.K_RETURN,
                                pygame.K_SPACE,
                                pygame.K_q,
                                pygame.K_ESCAPE,
                            ):
                                waiting = False
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            waiting = False

                    draw_scene(
                        screen,
                        env,
                        img_space,
                        img_box,
                        img_barrier,
                        lava_bg,
                        selected_cell,
                        hud_font,
                        hud_small_font,
                        total_reward,
                        dt_ms=dt2,
                        show_overlay=True,
                        overlay_text=text,
                    )
                    pygame.display.flip()

                running_game = False

        if not running_game:
            break

        draw_scene(
            screen,
            env,
            img_space,
            img_box,
            img_barrier,
            lava_bg,
            selected_cell,
            hud_font,
            hud_small_font,
            total_reward,
            dt_ms=dt,
            show_overlay=False,
        )
        pygame.display.flip()

    env.close()
    return episode_result


class MenuButton:
    def __init__(self, rect: pygame.Rect, text: str, map_path: Optional[str]):
        self.rect = rect
        self.text = text
        self.map_path = map_path

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        base_color = (70, 80, 150)
        hover_color = (110, 130, 210)
        color = hover_color if hovered else base_color

        shadow = self.rect.copy()
        shadow.move_ip(0, 4)
        pygame.draw.rect(screen, (0, 0, 0, 160), shadow, border_radius=14)

        pygame.draw.rect(screen, color, self.rect, border_radius=14)
        pygame.draw.rect(screen, (220, 230, 255), self.rect, 2, border_radius=14)

        text_surf = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)


def menu_loop(screen: pygame.Surface):
    clock = pygame.time.Clock()
    width, height = screen.get_size()

    title_font = pygame.font.SysFont("comicsansms", 42, bold=True)
    button_font = pygame.font.SysFont("comicsansms", 26)
    info_font = pygame.font.SysFont("couriernew", 18)

    btn_w = 180
    btn_h = 39
    center_x = width // 2

    buttons: List[MenuButton] = []

    labels_paths = [
        ("Random Map", None),
        ("Map 1", os.path.join("maps", "C:\\Users\\Asus\\Desktop\\shover_world\\maps\\map1.txt")),
        ("Map 2", os.path.join("maps", "C:\\Users\\Asus\\Desktop\\shover_world\\maps\\map2.txt")),
        ("Quit", "QUIT"),
    ]
    start_y = height // 2 - 20

    for i, (label, path) in enumerate(labels_paths):
        rect = pygame.Rect(0, 0, btn_w, btn_h)
        rect.centerx = center_x
        rect.y = start_y + i * (btn_h + 12)
        buttons.append(MenuButton(rect, label, path))

    last_result: Optional[str] = None

    running = True
    while running:
        dt = clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    return
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in buttons:
                    if btn.rect.collidepoint(event.pos):
                        if btn.map_path == "QUIT":
                            return
                        result = game_loop(
                            screen,
                            clock,
                            btn.map_path,
                            main_font=button_font,
                            small_font=info_font,
                        )
                        if result is None:
                            last_result = "Exited game."
                        else:
                            last_result = f"Last game result: {result.upper()}"
                        break

        for y in range(height):
            t = y / max(1, height)
            r = int(20 + 80 * t)
            g = int(15 + 30 * (1 - t))
            b = int(60 + 90 * t)
            pygame.draw.line(screen, (r, g, b), (0, y), (width, y))

        for x in range(0, width, 40):
            for y in range(0, height, 40):
                if (x + y // 2) % 3 == 0:
                    screen.fill((255, 255, 255), (x, y, 1, 1))

        title = "Shover World"
        title_shadow = title_font.render(title, True, (0, 0, 0))
        title_main = title_font.render(title, True, (255, 255, 255))
        shadow_rect = title_shadow.get_rect(center=(width // 2 + 3, height // 4 + 3))
        main_rect = title_main.get_rect(center=(width // 2, height // 4))
        screen.blit(title_shadow, shadow_rect)
        screen.blit(title_main, main_rect)

        for btn in buttons:
            btn.draw(screen, button_font, mouse_pos)

        if last_result is not None:
            res_surf = info_font.render(last_result, True, (255, 250, 200))
            res_rect = res_surf.get_rect(center=(width // 2, height - 30))
            screen.blit(res_surf, res_rect)

        pygame.display.flip()


def main():
    pygame.init()

    window_cols = 10 
    window_rows = 10
    width = CELL_SIZE * window_cols
    height = CELL_SIZE * window_rows + HUD_HEIGHT
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Shover World")

    if len(sys.argv) > 1:
        map_path = sys.argv[1]
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("arial", 24)
        small = pygame.font.SysFont("arial", 16)
        game_loop(screen, clock, map_path, font, small)
    else:
        menu_loop(screen)

    pygame.quit()


if __name__ == "__main__":
    main()
