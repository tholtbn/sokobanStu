

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