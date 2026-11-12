
<<<<<<< HEAD

import time
import heapq
import collections
from sokoban import sokoban_goal_state


def compute_distances_and_dead_squares(width, height, storage, obstacles):

    dirs = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    storage_list = list(storage)
    dist_map = {}
    reachable_all = set()

    for s in storage_list:
        queue = collections.deque([(s, 0)])
        visited = {s: 0}
        dist_map[(s, s)] = 0
        reachable_all.add(s)

        while queue:
            b_curr, d = queue.popleft()
            for dx, dy in dirs:
                b_prev = (b_curr[0] - dx, b_curr[1] - dy)
                r_pos = (b_curr[0] + dx, b_curr[1] + dy)

                if (0 <= b_prev[0] < width and 0 <= b_prev[1] < height and b_prev not in obstacles and
                    0 <= r_pos[0] < width and 0 <= r_pos[1] < height and r_pos not in obstacles):
                    if b_prev not in visited:
                        visited[b_prev] = d + 1
                        queue.append((b_prev, d + 1))
                        reachable_all.add(b_prev)
                        dist_map[(b_prev, s)] = d + 1

    dead_squares = set()
    for x in range(width):
        for y in range(height):
            if (x, y) not in obstacles and (x, y) not in storage and (x, y) not in reachable_all:
                dead_squares.add((x, y))

    return dist_map, dead_squares


def get_box_matching_cost(boxes, storage_list, dist_map):

    n_b = len(boxes)
    n_s = len(storage_list)
    box_list = list(boxes)

    dp = {0: 0}
    for i in range(n_b):
        box = box_list[i]
        next_dp = {}
        for mask, cost in dp.items():
            for j in range(n_s):
                if not (mask & (1 << j)):
                    d = dist_map.get((box, storage_list[j]), float('inf'))
                    if d == float('inf'):
                        continue
                    new_mask = mask | (1 << j)
                    new_cost = cost + d
                    if new_mask not in next_dp or new_cost < next_dp[new_mask]:
                        next_dp[new_mask] = new_cost
        dp = next_dp
        if not dp:
            return float('inf')

    return min(dp.values()) if dp else float('inf')


def is_2x2_deadlock(boxes, storage, width, height, obstacles):

    for bx, by in boxes:
        if (bx, by) in storage:
            continue
        for dx, dy in [(-1, -1), (-1, 0), (0, -1), (0, 0)]:
            x, y = bx + dx, by + dy
            cells = [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]
            blocked = True
            has_non_storage_box = False
            for cx, cy in cells:
                if cx < 0 or cx >= width or cy < 0 or cy >= height or (cx, cy) in obstacles:
                    continue
                elif (cx, cy) in boxes:
                    if (cx, cy) not in storage:
                        has_non_storage_box = True
                else:
                    blocked = False
                    break
            if blocked and has_non_storage_box:
                return True
    return False


def solve(initial_state, timebound=120):

    start_time = time.time()

    if sokoban_goal_state(initial_state):
        return initial_state

    if timebound <= 0:
        return False

    width = initial_state.width
    height = initial_state.height
    obstacles = initial_state.obstacles
    storage = initial_state.storage
    storage_list = list(storage)

    dist_map, dead_squares = compute_distances_and_dead_squares(width, height, storage, obstacles)

    def heuristic(state):
        for b in state.boxes:
            if b in dead_squares:
                return float('inf')

        if is_2x2_deadlock(state.boxes, storage, width, height, obstacles):
            return float('inf')

        box_cost = get_box_matching_cost(state.boxes, storage_list, dist_map)
        if box_cost == float('inf'):
            return float('inf')

        unplaced = [b for b in state.boxes if b not in storage]
        if not unplaced:
            return 0

        min_r_dist = min(abs(r[0] - b[0]) + abs(r[1] - b[1]) for r in state.robots for b in unplaced) - 1
        r_cost = max(0, min_r_dist)

        return box_cost + r_cost

    h0 = heuristic(initial_state)
    if h0 == float('inf'):
        return False

    counter = 0
    open_set = [(h0, h0, counter, initial_state)]
    visited = {initial_state.hashable_state(): initial_state.gval}

    deadline = start_time + timebound - 0.3

    while open_set:
        if time.time() > deadline:
            return False

        f, h, _, current = heapq.heappop(open_set)

        if sokoban_goal_state(current):
            return current

        if current.gval > visited.get(current.hashable_state(), float('inf')):
            continue

        for succ in current.successors():
            key = succ.hashable_state()
            new_g = succ.gval

            if key in visited and visited[key] <= new_g:
                continue

            h_succ = heuristic(succ)
            if h_succ == float('inf'):
                continue

            visited[key] = new_g
            counter += 1
            f_succ = new_g + h_succ
            heapq.heappush(open_set, (f_succ, h_succ, counter, succ))

    return False
=======
import heapq
import time
from collections import deque

from sokoban import sokoban_goal_state, UP, RIGHT, DOWN, LEFT

# ---------------------------------------------------------------------------
# Hang so cau hinh
# ---------------------------------------------------------------------------
_DIRS = (UP, RIGHT, DOWN, LEFT)          # cung thu tu voi SokobanState.successors
_DX = (0, 1, 0, -1)
_DY = (-1, 0, 1, 0)
_INF = 10 ** 6                           # "vo cung" cho khoang cach / heuristic

TIME_FRACTION = 0.88                     # ti le timebound duoc phep dung
TIME_RESERVE = 0.4                       # giay du tru cho phat lai + tra ket qua
WEIGHTS = (4.0, 2.0, 1.4, 1.15, 1.0)     # lich trong so cua weighted A*
NODE_CAP = 700_000                     # gioi han so nut luu tru moi vong (bo nho)


# ---------------------------------------------------------------------------
# Tien xu ly ban do
# ---------------------------------------------------------------------------
class _Board:
    """Du lieu bat bien suy ra tu ban do (khong phu thuoc vi tri thung/robot)."""

    def __init__(self, state):
        W, H = state.width, state.height
        N = W * H
        self.W, self.H, self.N = W, H, N

        wall = bytearray(N)
        for (x, y) in state.obstacles:
            if 0 <= x < W and 0 <= y < H:
                wall[y * W + x] = 1
        self.wall = wall

        nb4 = []
        for c in range(N):
            x, y = c % W, c // W
            row = []
            for k in range(4):
                nx, ny = x + _DX[k], y + _DY[k]
                if 0 <= nx < W and 0 <= ny < H and not wall[ny * W + nx]:
                    row.append(ny * W + nx)
                else:
                    row.append(-1)
            nb4.append(tuple(row))
        self.nb4 = nb4
        self.nbl = [tuple(n for n in row if n >= 0) for row in nb4]

        self.storage = sorted(y * W + x for (x, y) in state.storage)
        self.ns = len(self.storage)
        self.smask = 0
        for s in self.storage:
            self.smask |= 1 << s

        self._push_distance_tables()
        self._push_options()
        self._walk_rows = {}
        self._acache = {}          # mask hop -> chi phi ghep cap

    # -- khoang cach day nguoc -------------------------------------------------
    def _push_distance_tables(self):
        """pd[j][c] = so lan day it nhat de dua mot thung tu o c toi dich j.

        BFS nguoc: thung dang o c (vua duoc day theo huong k) thi truoc do no
        o p = c - k va robot dung o p - k; ca hai phai la o trong ban do.
        """
        N, nb4 = self.N, self.nb4
        pd = []
        for s in self.storage:
            dist = [_INF] * N
            dist[s] = 0
            q = deque([s])
            while q:
                c = q.popleft()
                for k in range(4):
                    back = (k + 2) % 4
                    p = nb4[c][back]
                    if p < 0 or dist[p] < _INF:
                        continue
                    if nb4[p][back] < 0:          # khong co cho cho robot dung
                        continue
                    dist[p] = dist[c] + 1
                    q.append(p)
            pd.append(dist)
        self.pd = pd

        self.dead = [False] * N
        self.minv = [_INF] * N
        self.arg = [0] * N
        self.pdrow = [None] * N
        for c in range(N):
            row = tuple(pd[j][c] for j in range(self.ns))
            self.pdrow[c] = row
            if self.wall[c]:
                continue
            if self.ns:
                m = min(row)
                self.minv[c] = m
                self.arg[c] = row.index(m)
            if self.minv[c] >= _INF:
                self.dead[c] = True

    # -- cac lan day "co the" tai moi o thung ---------------------------------
    def _push_options(self):
        """push_opts[b] = [(huong k, o robot dung pp, o dich cua thung t)]
        chi gom nhung lan day khong dua thung vao tuong / o chet."""
        nb4 = self.nb4
        self.push_opts = []
        for b in range(self.N):
            opts = []
            if not self.wall[b]:
                for k in range(4):
                    t = nb4[b][k]
                    pp = nb4[b][(k + 2) % 4]
                    if t >= 0 and pp >= 0 and not self.dead[t]:
                        opts.append((k, pp, t))
            self.push_opts.append(tuple(opts))

    def bfs(self, start, occ):
        """Khoang cach di bo tu `start`; o co occ[c] != 0 la vat can."""
        nbl = self.nbl
        dist = [-1] * self.N
        dist[start] = 0
        frontier = [start]
        while frontier:
            nxt = []
            for c in frontier:
                d1 = dist[c] + 1
                for n in nbl[c]:
                    if dist[n] < 0 and not occ[n]:
                        dist[n] = d1
                        nxt.append(n)
            frontier = nxt
        return dist

    # -- can duoi so buoc di bo toi lan day dau tien -------------------------
    def walk_row(self, rc):
        """row[b] = so buoc di bo ngan nhat (bo qua thung) tu o rc toi mot o
        co the dung de day thung o b."""
        row = self._walk_rows.get(rc)
        if row is not None:
            return row
        N, nbl = self.N, self.nbl
        dist = [-1] * N
        dist[rc] = 0
        frontier = [rc]
        while frontier:
            nxt = []
            for c in frontier:
                d = dist[c] + 1
                for n in nbl[c]:
                    if dist[n] < 0:
                        dist[n] = d
                        nxt.append(n)
            frontier = nxt
        row = [_INF] * N
        for b in range(N):
            best = _INF
            for (_k, pp, _t) in self.push_opts[b]:
                d = dist[pp]
                if 0 <= d < best:
                    best = d
            row[b] = best
        self._walk_rows[rc] = row
        return row

    # -- ghep cap thung - dich (Hungary) --------------------------------------
    def assignment_cost(self, boxcells):
        rows = [self.pdrow[c] for c in boxcells]
        n, m = len(rows), self.ns
        if n > m:
            return _INF
        BIG = 10 ** 9
        u = [0] * (n + 1)
        v = [0] * (m + 1)
        p = [0] * (m + 1)
        way = [0] * (m + 1)
        for i in range(1, n + 1):
            p[0] = i
            j0 = 0
            minv = [BIG] * (m + 1)
            used = [False] * (m + 1)
            while True:
                used[j0] = True
                i0 = p[j0]
                row = rows[i0 - 1]
                delta, j1 = BIG, 0
                for j in range(1, m + 1):
                    if not used[j]:
                        cur = row[j - 1] - u[i0] - v[j]
                        if cur < minv[j]:
                            minv[j] = cur
                            way[j] = j0
                        if minv[j] < delta:
                            delta = minv[j]
                            j1 = j
                for j in range(m + 1):
                    if used[j]:
                        u[p[j]] += delta
                        v[j] -= delta
                    else:
                        minv[j] -= delta
                j0 = j1
                if p[j0] == 0:
                    break
            while True:
                j1 = way[j0]
                p[j0] = p[j1]
                j0 = j1
                if j0 == 0:
                    break
        cost = -v[0]
        return cost if cost < _INF else _INF

    # -- heuristic -----------------------------------------------------------
    def h(self, robots, boxcells, mask):
        """Can duoi cua tong so buoc con lai (chap nhan duoc)."""
        minv, arg = self.minv, self.arg
        total = 0
        used = 0
        conflict = False
        for c in boxcells:
            m = minv[c]
            if m >= _INF:
                return _INF
            total += m
            bit = 1 << arg[c]
            if used & bit:
                conflict = True
            used |= bit
        if conflict:
            total = self._acache.get(mask)
            if total is None:
                total = self.assignment_cost(boxcells)
                if len(self._acache) < 2_000_000:
                    self._acache[mask] = total
            if total >= _INF:
                return _INF
        if total == 0:
            return 0
        best = _INF
        rows = self._walk_rows
        for rc in robots:
            row = rows.get(rc)
            if row is None:
                row = self.walk_row(rc)
            for c in boxcells:
                v = row[c]
                if v < best:
                    best = v
        if best >= _INF:
            return _INF
        return total + best

    # -- freeze deadlock -------------------------------------------------------
    def freeze_deadlock(self, mask, c):
        """True neu thung moi dat o c cung cac thung ke no bi 'dong bang'
        (khong the di chuyen vinh vien) va co it nhat mot thung khong o dich."""
        nb = self.nb4[c]
        dead = self.dead
        l, r, u, d = nb[3], nb[1], nb[0], nb[2]

        def axis_possible(a, b):
            return (a < 0 or b < 0 or (dead[a] and dead[b])
                    or (mask >> a) & 1 or (mask >> b) & 1)

        if not (axis_possible(l, r) and axis_possible(u, d)):
            return False
        # thanh phan lien thong (4 huong) cac thung chua c
        comp = [c]
        seen = {c}
        i = 0
        nb4 = self.nb4
        while i < len(comp):
            x = comp[i]
            i += 1
            for y in nb4[x]:
                if y >= 0 and y not in seen and (mask >> y) & 1:
                    seen.add(y)
                    comp.append(y)
        frozen = set(comp)
        changed = True
        while changed:
            changed = False
            for x in list(frozen):
                nbx = nb4[x]
                ok = True
                for a, b in ((nbx[3], nbx[1]), (nbx[0], nbx[2])):
                    if not (a < 0 or b < 0 or (dead[a] and dead[b])
                            or a in frozen or b in frozen):
                        ok = False
                        break
                if not ok:
                    frozen.discard(x)
                    changed = True
        smask = self.smask
        for x in frozen:
            if not (smask >> x) & 1:
                return True
        return False


# ---------------------------------------------------------------------------
# Tim kiem
# ---------------------------------------------------------------------------
class _Timeout(Exception):
    pass


def _bits(mask):
    out = []
    while mask:
        low = mask & -mask
        out.append(low.bit_length() - 1)
        mask ^= low
    return out


class _Solver:
    def __init__(self, board, state, deadline):
        self.b = board
        self.deadline = deadline
        W = board.W
        self.robots0 = tuple(y * W + x for (x, y) in state.robots)
        mask = 0
        for (x, y) in state.boxes:
            mask |= 1 << (y * W + x)
        self.mask0 = mask
        self.nbox = bin(mask).count("1")
        self.nrob = len(self.robots0)
        self.NK = board.N ** max(1, self.nrob)

    # -- khoa trang thai (robot da sap xep: robot nhu nhau) --------------------
    def _key(self, robots, mask):
        N = self.b.N
        rc = 0
        for r in sorted(robots):
            rc = rc * N + r
        return mask * self.NK + rc

    # ======================= tim kiem macro-push ==============================
    def macro(self, w, bound):
        """Weighted A* tren cac lan day.  Tra ve (trang_thai, chi_phi, ds_nut).

        trang_thai: 'found' | 'exhausted' | 'cap' ; ket thuc bang 'exhausted'
        o vong w = 1 nghia la chi phi `bound` da duoc chung minh toi uu.
        """
        B = self.b
        N, wall, nbl, nb4, push_opts = B.N, B.wall, B.nbl, B.nb4, B.push_opts
        smask = B.smask
        bfs = B.bfs
        heur = B.h
        freeze = B.freeze_deadlock
        deadline = self.deadline
        key_of = self._key

        robots0, mask0 = self.robots0, self.mask0
        h0 = heur(robots0, _bits(mask0), mask0)
        if h0 >= _INF or h0 >= bound:
            return "exhausted", None, None
        key0 = key_of(robots0, mask0)
        nodes = [(-1, robots0, mask0, 0, -1, key0)]
        best = {key0: 0}
        heap = [(w * h0, h0, 0, 0)]
        ctr = 1
        expansions = 0
        pop, push = heapq.heappop, heapq.heappush
        notstore = ~smask

        while heap:
            f, h, _c, idx = pop(heap)
            parent, robots, mask, g, _mv, key = nodes[idx]
            if best[key] < g:
                continue
            if g + h >= bound:
                if w == 1.0:
                    break
                continue
            if not (mask & notstore):
                return "found", g, (nodes, idx)
            expansions += 1
            if not (expansions & 127):
                if time.time() > self.deadline:
                    raise _Timeout()
                if len(nodes) > NODE_CAP:
                    return "cap", None, None

            bl = _bits(mask)
            occ = bytearray(wall)
            for b in bl:
                occ[b] = 1
            for r in robots:
                occ[r] = 1
            rob_at = {r: j for j, r in enumerate(robots)}
            blockers = set()          # robot dang chan mot lan day hop le
            nrob = len(robots)

            for ri, rp in enumerate(robots):
                dist = bfs(rp, occ)
                dfree = None          # BFS bo qua robot khac (tinh lazy)
                head, tail = robots[:ri], robots[ri + 1:]
                for bi, b in enumerate(bl):
                    for (k, pp, t) in push_opts[b]:
                        dd = dist[pp]
                        tocc = occ[t] and t != rp
                        if dd < 0 or tocc:
                            # lan day khong thuc hien duoc: co phai do robot khac?
                            if nrob > 1 and not ((mask >> t) & 1):
                                j = rob_at.get(t)
                                if j is not None and j != ri:
                                    blockers.add(j)
                                elif dd < 0 and not ((mask >> pp) & 1):
                                    j = rob_at.get(pp)
                                    if j is not None and j != ri:
                                        blockers.add(j)
                                    else:
                                        if dfree is None:
                                            occ2 = bytearray(wall)
                                            for x in bl:
                                                occ2[x] = 1
                                            dfree = bfs(rp, occ2)
                                        if dfree[pp] >= 0:
                                            blockers.update(
                                                j2 for j2 in range(nrob) if j2 != ri)
                            continue
                        ng = g + dd + 1
                        nmask = mask ^ (1 << b) ^ (1 << t)
                        nrobots = head + (b,) + tail
                        nkey = key_of(nrobots, nmask)
                        old = best.get(nkey)
                        if old is not None and old <= ng:
                            continue
                        if freeze(nmask, t):
                            continue
                        nbl_ = bl[:bi] + [t] + bl[bi + 1:]
                        hh = heur(nrobots, nbl_, nmask)
                        if hh >= _INF or ng + hh >= bound:
                            continue
                        best[nkey] = ng
                        nodes.append((idx, nrobots, nmask, ng,
                                      (ri * N + pp) * 4 + k, nkey))
                        push(heap, (ng + w * hh, hh, ctr, len(nodes) - 1))
                        ctr += 1

            # nuoc "ne": robot dang chan di mot buoc sang o trong (khong day)
            for j in blockers:
                rj = robots[j]
                for k in range(4):
                    n = nb4[rj][k]
                    if n < 0 or occ[n]:
                        continue
                    nrobots = robots[:j] + (n,) + robots[j + 1:]
                    ng = g + 1
                    nkey = key_of(nrobots, mask)
                    old = best.get(nkey)
                    if old is not None and old <= ng:
                        continue
                    hh = heur(nrobots, bl, mask)
                    if hh >= _INF or ng + hh >= bound:
                        continue
                    best[nkey] = ng
                    nodes.append((idx, nrobots, mask, ng, -(j * 4 + k) - 1, nkey))
                    push(heap, (ng + w * hh, hh, ctr, len(nodes) - 1))
                    ctr += 1
        return "exhausted", None, None

    # ======================= tim kiem tung buoc (du phong) ====================
    def primitive(self, w, bound):
        """A* tren tung buoc don (dam bao day du, cham hon macro)."""
        B = self.b
        N, W, nb4 = B.N, B.W, B.nb4
        wall = B.wall
        smask = B.smask
        heur = B.h
        freeze = B.freeze_deadlock
        dead = B.dead
        key_of = self._key
        robots0, mask0 = self.robots0, self.mask0
        h0 = heur(robots0, _bits(mask0), mask0)
        if h0 >= _INF or h0 >= bound:
            return "exhausted", None, None
        key0 = key_of(robots0, mask0)
        nodes = [(-1, robots0, mask0, 0, -1, key0)]
        best = {key0: 0}
        heap = [(w * h0, h0, 0, 0)]
        ctr = 1
        expansions = 0
        notstore = ~smask
        while heap:
            f, h, _c, idx = heapq.heappop(heap)
            parent, robots, mask, g, _mv, key = nodes[idx]
            if best[key] < g:
                continue
            if g + h >= bound:
                if w == 1.0:
                    break
                continue
            if not (mask & notstore):
                return "found", g, (nodes, idx)
            expansions += 1
            if not (expansions & 255):
                if time.time() > self.deadline:
                    raise _Timeout()
                if len(nodes) > NODE_CAP:
                    return "cap", None, None
            for ri, rp in enumerate(robots):
                for k in range(4):
                    nloc = nb4[rp][k]
                    if nloc < 0 or nloc in robots:
                        continue
                    nmask = mask
                    pushed = -1
                    if (mask >> nloc) & 1:
                        t = nb4[nloc][k]
                        if t < 0 or (mask >> t) & 1 or t in robots or dead[t]:
                            continue
                        nmask = mask ^ (1 << nloc) ^ (1 << t)
                        pushed = t
                    nrobots = robots[:ri] + (nloc,) + robots[ri + 1:]
                    ng = g + 1
                    nkey = key_of(nrobots, nmask)
                    old = best.get(nkey)
                    if old is not None and old <= ng:
                        continue
                    if pushed >= 0 and freeze(nmask, pushed):
                        continue
                    hh = heur(nrobots, _bits(nmask), nmask)
                    if hh >= _INF or ng + hh >= bound:
                        continue
                    best[nkey] = ng
                    nodes.append((idx, nrobots, nmask, ng, ri * 4 + k, nkey))
                    heapq.heappush(heap, (ng + w * hh, hh, ctr, len(nodes) - 1))
                    ctr += 1
        return "exhausted", None, None

    # ======================= dung lai duong di ================================
    def macro_actions(self, nodes, idx):
        """Chuyen chuoi nut macro thanh danh sach (robot, huong) tung buoc."""
        B = self.b
        N, nb4, wall = B.N, B.nb4, B.wall
        chain = []
        while idx > 0:
            chain.append(idx)
            idx = nodes[idx][0]
        chain.reverse()
        robots = list(self.robots0)
        boxes = set(_bits(self.mask0))
        actions = []
        for i in chain:
            mv = nodes[i][4]
            if mv < 0:                       # nuoc ne: 1 buoc, khong day
                ri, k = divmod(-mv - 1, 4)
                actions.append((ri, k))
                robots[ri] = nb4[robots[ri]][k]
                continue
            k = mv % 4
            rest = mv // 4
            ri, pp = divmod(rest, N)
            start = robots[ri]
            blocked = set(boxes)
            blocked.update(r for j, r in enumerate(robots) if j != ri)
            if start != pp:
                prev = {start: None}
                q = deque([start])
                while q and pp not in prev:
                    c = q.popleft()
                    for kk in range(4):
                        n = nb4[c][kk]
                        if n >= 0 and n not in prev and n not in blocked:
                            prev[n] = (c, kk)
                            q.append(n)
                path = []
                c = pp
                while prev[c] is not None:
                    c, kk = prev[c][0], prev[c][1]
                    path.append(kk)
                    # c da duoc cap nhat thanh o truoc
                path.reverse()
                for kk in path:
                    actions.append((ri, kk))
            actions.append((ri, k))
            b = nb4[pp][k]
            t = nb4[b][k]
            boxes.discard(b)
            boxes.add(t)
            robots[ri] = b
        return actions

    @staticmethod
    def primitive_actions(nodes, idx):
        B_actions = []
        while idx > 0:
            mv = nodes[idx][4]
            B_actions.append(divmod(mv, 4))
            idx = nodes[idx][0]
        B_actions.reverse()
        return B_actions


def _replay(initial_state, actions):
    """Phat lai danh sach hanh dong bang successors() cua framework."""
    cur = initial_state
    for (ri, k) in actions:
        name = "%d %s" % (ri, _DIRS[k].name)
        nxt = None
        for s in cur.successors():
            if s.action == name:
                nxt = s
                break
        if nxt is None:
            return None
        cur = nxt
    return cur


# ---------------------------------------------------------------------------
# Giao dien chinh
# ---------------------------------------------------------------------------
def _time_limit(timebound):
    return max(timebound * 0.5, timebound - max(TIME_RESERVE, (1 - TIME_FRACTION) * timebound))


_LAST_INFO = {}          # thong tin lan chay gan nhat (phuc vu bao cao / debug)


def solve(initial_state, timebound=120):
    """Giao dien chinh. Moi ngoai le bat ngo -> False (khong crash)."""
    try:
        return _solve(initial_state, timebound)
    except Exception:
        return False


def _solve(initial_state, timebound):
    """Tra ve trang thai dich (co chuoi parent hop le) hoac False.

    Khong thay doi initial_state.  Dung tong cong khong qua ~TIME_FRACTION * timebound.
    """
    t0 = time.time()
    info = _LAST_INFO
    info.clear()
    info.update(cost=None, macro_optimal=False, exact_optimal=False, phase="init")
    if sokoban_goal_state(initial_state):
        info.update(cost=initial_state.gval, macro_optimal=True, exact_optimal=True)
        return initial_state
    if timebound <= 0:
        return False

    deadline = t0 + _time_limit(timebound)
    try:
        board = _Board(initial_state)
        solver = _Solver(board, initial_state, deadline)
    except Exception:
        return False
    if solver.nbox > board.ns or solver.nrob == 0:
        return False             # thung nhieu hon dich / khong co robot: vo nghiem

    best_final = None
    best_cost = _INF

    def accept(actions):
        nonlocal best_final, best_cost
        final = _replay(initial_state, actions)
        if final is not None and sokoban_goal_state(final) and final.gval < best_cost:
            best_final, best_cost = final, final.gval
            info["cost"] = best_cost

    # --- giai doan 1: macro-push, anytime weighted A* ---------------------------
    # Lich trong so dong: neu mot vong cham tran bo nho (khong cai thien duoc)
    # thi thu trong so trung gian giua w do va w truoc (de tim duoc cai thien
    # nho voi it nut hon) thay vi bo cuoc ngay.
    info["phase"] = "macro"
    try:
        queue = list(WEIGHTS)
        prev_w = None
        while queue:
            w = queue.pop(0)
            status, _cost, payload = solver.macro(w, best_cost)
            if status == "found":
                accept(solver.macro_actions(*payload))
                prev_w = w
            if w == 1.0 and status in ("found", "exhausted"):
                info["macro_optimal"] = True
            if status == "cap":
                if prev_w is not None and prev_w - w > 0.08:
                    queue.insert(0, round((prev_w + w) / 2.0, 3))
                    prev_w = w  # tranh lap vo han: lan sau khoang cach nho hon
                    continue
                break
            if status == "exhausted" and best_final is None:
                break            # khong gian macro het ma chua co nghiem
    except (_Timeout, MemoryError):
        pass

    # --- giai doan 2: A* tung buoc chinh xac ----------------------------------
    # * macro khong co nghiem  -> du phong day du.
    # * macro da co nghiem     -> dung chi phi do lam can tren; A* tung buoc co ca
    #   nuoc "di truoc chiem cho" ma macro khong bieu dien duoc.  Map nho: chung
    #   minh/cai thien nghiem; map lon: chay het gio, khong lam hong ket qua.
    info["phase"] = "exact"
    if time.time() < deadline:
        try:
            for w in ((3.0, 1.5, 1.0) if best_final is None else (1.0,)):
                status, _cost, payload = solver.primitive(w, best_cost)
                if status == "found":
                    accept(solver.primitive_actions(*payload))
                if w == 1.0 and status in ("found", "exhausted"):
                    info["exact_optimal"] = True
                if status == "cap" or (status == "exhausted" and best_final is None):
                    break
        except (_Timeout, MemoryError):
            pass

    info["phase"] = "done"
    info["elapsed"] = time.time() - t0
    return best_final if best_final is not None else False
>>>>>>> 777327d (Update project)
