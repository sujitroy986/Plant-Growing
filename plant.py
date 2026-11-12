import math
import random
import pygame

pygame.init()
W, H = 900, 700
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Procedural Neon Flower")
clock = pygame.time.Clock()

# Colors
BLACK = (0, 0, 0)
TURQ = (60, 255, 220)
PINK = (255, 130, 230)
VIOLET = (175, 115, 255)
GREY = (110, 115, 135)
WHITE = (255, 255, 255)

GROUND_Y = H - 110
STEM_H = 360

scene = pygame.Surface((W, H))
veil = pygame.Surface((W, H))
veil.fill(BLACK)

random.seed(7)
JIT = [(random.uniform(-2.2, 2.2), random.uniform(-2.2, 2.2), random.random())
       for _ in range(1024)]
GROUND_DOTS = [(random.uniform(0, W),
                GROUND_Y + abs(random.gauss(0, 16)) + random.uniform(0, 5),
                random.random()) for _ in range(900)]


# ---------- helpers ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3.0 - 2.0 * x)


def stage(life, start, dur):
    """0 before `start`, eases to 1 over `dur`."""
    return ease((life - start) / dur)


def lerp(a, b, f):
    return a + (b - a) * f


def mix(c1, c2, f):
    f = clamp(f)
    return tuple(int(lerp(a, b, f)) for a, b in zip(c1, c2))


def line(surf, color, pts, closed=False):
    if len(pts) > 1:
        pygame.draw.aalines(surf, color, closed, pts)


def stipple(surf, color, pts, t, salt=0):
    """Grainy, twinkling dots along a path (gives the speckled neon look)."""
    for i, (x, y) in enumerate(pts):
        jx, jy, ph = JIT[(i * 7 + salt) % len(JIT)]
        tw = 0.55 + 0.45 * math.sin(t * 3.0 + ph * 6.28)
        c = (int(color[0] * tw), int(color[1] * tw), int(color[2] * tw))
        surf.fill(c, (int(x + jx), int(y + jy), 2, 2))


# ---------- geometry ----------
def stem_points(grow, t, wilt, n=90):
    h = grow * STEM_H
    pts = []
    for i in range(n + 1):
        f = i / n
        sway = 8 * math.sin(f * 3.0 + t * 1.5) * f * min(1.0, grow * 3)
        bend = wilt * 95 * f ** 2.2          # stem bows to the right
        y = f * h * (1 - 0.18 * wilt * f * f)  # and loses a little height
        pts.append((W / 2 + sway + bend, GROUND_Y - y))
    return pts


def tube(pts):
    """Left/right outlines of a tapered hollow stem."""
    L, R = [], []
    n = len(pts) - 1
    for i, (x, y) in enumerate(pts):
        x0, y0 = pts[max(i - 1, 0)]
        x1, y1 = pts[min(i + 1, n)]
        dx, dy = x1 - x0, y1 - y0
        d = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / d, dx / d
        half = lerp(6.0, 3.5, i / n)
        L.append((x + nx * half, y + ny * half))
        R.append((x - nx * half, y - ny * half))
    return L, R


def leaf_outline(base, side, length, width, droop, steps=14):
    """Pointed lens-shaped leaf. side = +1 right, -1 left."""
    x, y = base
    top, bot, axis = [], [], []
    for i in range(steps + 1):
        f = i / steps
        a = math.radians(-22 - 20 * f) + droop * (0.4 + 1.0 * f)
        dx, dy = side * math.cos(a), math.sin(a)
        w = width * math.sin(math.pi * f) ** 0.9
        nx, ny = -dy, dx
        axis.append((x, y))
        top.append((x + nx * w, y + ny * w))
        bot.append((x - nx * w, y - ny * w))
        x += dx * length / steps
        y += dy * length / steps
    return top + bot[::-1], axis


def petal_outline(center, phi0, length, width, wilt, sgn, steps=12):
    """Pointed petal. phi0 = angle from straight up (radians, + is right)."""
    x, y = center
    left, right = [], []
    for i in range(steps + 1):
        f = i / steps
        phi = phi0 + sgn * (0.12 * f + wilt * (0.3 + 1.3 * f))  # wilt droops outward
        w = width * math.sin(math.pi * f) ** 0.8
        nx, ny = math.cos(phi), math.sin(phi)
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
        x += math.sin(phi) * length / steps
        y -= math.cos(phi) * length / steps
    return left + right[::-1]


# (count, spread in degrees, center length, side length, half-width)
LAYERS = [(9, 78, 70, 102, 13), (7, 58, 60, 90, 12), (5, 36, 50, 74, 10)]
LEAVES = [(0.22, +1, 90, 11), (0.38, -1, 78, 10), (0.54, +1, 64, 8.5), (0.70, -1, 52, 7)]


# ---------- drawing ----------
def draw_ground(t):
    for i, (x, y, b) in enumerate(GROUND_DOTS):
        tw = 0.6 + 0.4 * math.sin(t * 2 + b * 20)
        k = (0.25 + 0.75 * b) * tw
        scene.fill((int(70 * k), int(130 * k), int(130 * k)), (int(x), int(y), 2, 2))
    pygame.draw.ellipse(scene, (6, 28, 28), (W / 2 - 90, GROUND_Y - 6, 180, 16))


def draw_leaves(pts, grow, wilt, t, col):
    n = len(pts) - 1
    for i, (p, side, length, width) in enumerate(LEAVES):
        g = stage(grow if grow < 1 else 1.0, 0, 1)
        if grow < p:
            continue
        lg = stage(grow, p + 0.05, 0.25)
        if lg <= 0.01:
            continue
        bx, by = pts[min(n, int(p / grow * n))]
        outline, axis = leaf_outline((bx, by), side, length * lg, width * lg, wilt * 1.2)
        line(scene, col, outline, True)
        line(scene, mix(col, BLACK, 0.45), axis)
        stipple(scene, col, outline, t, salt=i * 40)


def draw_head(center, life, wilt, t):
    cx, cy = center
    bloom = stage(life, 0.38, 0.30)
    # glowing core
    core_r = int(6 + 22 * bloom * (1 - 0.7 * wilt))
    for r in range(core_r, 0, -3):
        k = 1 - r / max(1, core_r)
        c = mix(mix((120, 40, 110), PINK, k), WHITE, k * k)
        c = mix(c, GREY, wilt * 0.6)
        pygame.draw.circle(scene, c, (cx, cy), r)

    tilt = wilt * 0.5
    for li, (count, spread, lc, ls, width) in enumerate(LAYERS):
        open_ = stage(life, 0.40 + li * 0.04, 0.22)
        if open_ <= 0.01:
            continue
        base_col = mix(VIOLET, PINK, 0.2 + li * 0.4)
        col = mix(base_col, GREY, wilt)
        for i in range(count):
            u = (i / (count - 1)) * 2 - 1                       # -1 .. 1
            theta = math.radians(spread) * u * open_ + tilt
            length = lerp(lc, ls, abs(u) ** 1.3) * (0.15 + 0.85 * open_) * (1 - 0.3 * wilt)
            sgn = 1 if u >= 0 else -1
            pts = petal_outline((cx, cy), theta, length, width * (0.4 + 0.6 * open_), wilt, sgn)
            line(scene, col, pts, True)
            stipple(scene, col, pts, t, salt=li * 97 + i * 13)


def render(life, t):
    scene.fill(BLACK)
    draw_ground(t)

    wilt = stage(life, 0.72, 0.26)
    grow = stage(life, 0.02, 0.33)

    if grow < 0.05:  # seed
        pygame.draw.circle(scene, TURQ, (W // 2, GROUND_Y), 3)
    else:
        pts = stem_points(grow, t, wilt)
        col = mix(TURQ, (80, 125, 125), wilt * 0.7)
        L, R = tube(pts)
        for edge, s in ((L, 0), (R, 300)):
            line(scene, col, edge)
            stipple(scene, col, edge, t, salt=s)
        draw_leaves(pts, grow, wilt, t, col)
        cx, cy = pts[-1]
        draw_head((int(cx), int(cy)), life, wilt, t)

    # soft bloom: blur at two scales and add back
    screen.blit(scene, (0, 0))
    small = pygame.transform.smoothscale(scene, (W // 4, H // 4))
    g1 = pygame.transform.smoothscale(small, (W, H))
    tiny = pygame.transform.smoothscale(small, (W // 12, H // 12))
    g2 = pygame.transform.smoothscale(tiny, (W, H))
    for g in (g1, g1, g2, g2):
        screen.blit(g, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    fade = stage(life, 0.93, 0.07)
    if fade > 0:
        veil.set_alpha(int(255 * fade))
        screen.blit(veil, (0, 0))


def main():
    life, t = 0.0, 0.0
    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        t += dt
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                running = False
        life += dt / 30.0
        if life > 1.0:
            life = 0.0
        render(life, t)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()