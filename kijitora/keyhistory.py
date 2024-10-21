import os
from collections import deque
from game.engine.keys import Keys
from kijitora.config import DATA_DIR
from kijitora.kstate import key_history_slots
from datetime import datetime
from itertools import zip_longest

KEY_HISTORY_DIR = os.path.join(DATA_DIR, "replays")

def save_key_history(label, key_history, slot, now_tic):
    timestamp = datetime.now().strftime("%m%d_%H%M")
    idx = 0
    while True:
        filename = f"keyhistory_{timestamp}_{idx}.txt"
        filepath = os.path.join(KEY_HISTORY_DIR, filename)
        if not os.path.exists(filepath): break
        idx += 1

    total_tic = sum([tics for _, tics in key_history.history])
    with open(filepath, "w") as f:
        f.write(f"{label}/{now_tic - total_tic - 1}\n")
        for keys, tics in key_history.history:
            keys_str = "".join(sorted(str(key.serialized) for key in keys))
            f.write(f"{keys_str}:{tics}\n")

    key_history_slots[slot] = filename
    print(f"saved {total_tic} ticks into slot {slot}({filename=})")

def get_autoload_replay_name(level):
    return f"autoload_{level}.txt"

def exists_replay(name):
    filepath = os.path.join(KEY_HISTORY_DIR, name)
    return os.path.exists(filepath)

def load_key_history_from_name(name):
    filepath = os.path.join(KEY_HISTORY_DIR, name)

    loaded_key_history = deque()
    total_ticks = 0
    with open(filepath, "r") as f:
        lines = f.readlines()
        level_name, start_tick = (lines[0].rstrip().split("/") + [None])[:2]
        for line in lines[1:]:
            keys, tics = line.rstrip().split(":")[:2]
            keys = set(Keys.from_serialized(i) for i in keys)
            tics = int(tics)
            loaded_key_history.append((keys, tics))
            total_ticks += tics
    print(f"loaded {total_ticks} ticks from {name}: {level_name}")
    return KeyHistory(loaded_key_history, total_ticks), level_name


class KeyHistory:
    def __init__(self, history, length=-1):
        self.history = history
        self.length = length
        if self.length == -1:
            self.length = sum(time for _, time in history)

    def append(self, keys):
        if len(self.history) > 0 and self.history[-1][0] == keys:
            self.history[-1] = (self.history[-1][0], self.history[-1][1] + 1)
        else:
            self.history.append((keys, 1))
        self.length += 1

    def pop(self):
        keys, time = self.history[0]
        if time > 1:
            self.history[0] = (keys, time - 1)
        else:
            self.history.popleft()
        self.length -= 1
        return keys

    def clear(self):
        self.history.clear()
        self.length = 0

    def iterator(self):
        for keys, time in self.history:
            for _ in range(time):
                yield keys

    def compressed(self):
        compressed_key_history = KeyHistory(deque())
        for keys in self.iterator():
            compressed_key_history.append(keys)
        return compressed_key_history

    def merged(self, other):
        new_length = max(self.length, other.length)
        merged = deque()
        tic = 0
        for first_key, second_key in zip_longest(self.iterator(), other.iterator()):
            if first_key is None:
                merged.append((second_key, 1))
            elif second_key is None:
                merged.append((first_key, 1))
            else:
                merged.append((first_key | second_key, 1))
        return KeyHistory(merged, new_length).compressed()

    def subs(self, begin, end):
        if not(0 <= begin < end <= self.length):
            raise Exception("out of range")
        return KeyHistory([(keys, 1) for keys in self.iterator()][begin:end], end-begin).compressed()


