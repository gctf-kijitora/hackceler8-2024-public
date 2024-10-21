# Hackceler8 2024 Game

## Steps to run the game:

1. Install prerequisites
```
cd handout
python3 -m venv my_venv
source my_venv/bin/activate
pip3 install -r requirements.txt
```

2. Run server (optional but good for testing cheat detection/etc.)

```
cd handout
source my_venv/bin/activate
python3 server.py
```

Note that this server is slightly different from the one run by organizers during the live rounds as it doesn't have all the code for the boss fights.

3. Run client

```
cd handout
source my_venv/bin/activate
python3 client.py
```

If you want to run the client without a server, pass `--standalone` as an additional argument.

Here’s the English translation of the README:

## Kijitora Custom
### Default Keymap

| Key | Action | Details/Usage |
| --- | --- | --- |
| Z | Decrease TickRate | |
| X | Increase TickRate | |
| M | Stop Key Replay | |
| C | Stop Tick | |
| V | Advance Tick | |
| K | Invincibility | Standalone only |
| U | Reset Camera | |
| I | Camera Zoom In | |
| O | Camera Zoom Out | |
| Y | Auto Paint | Piet-related function |
| H | Tick Undo | Works every 10 ticks / does not work in Arcade mode |
| J | Tick Redo | |
| L | Reset Map | Explained later |
| , | Multi-gun Rapid Fire | |
| B | Auto-aim at Boss | |
| N | Automatic Double Jump | |
| F | Max Jump as per jump trajectory | |
| T | Key Lock | Locks the current key being pressed. Press again to unlock |
| 1-5 | Save/Load Game State | Can save in 5 different slots, Standalone only |
| 6-0 | Save/Load Key History | Can save in 5 different slots |
| Ctrl + Number | Clear Slot | |

### Other Features
| Action | Function | Details/Usage |
| --- | --- | --- |
| Right-click | Teleport | |
| Middle-click | Pathfinding and Move | Requires setup in Rust |
| Mouse Wheel Scroll | Camera Zoom In/Out | |
| Ctrl + V | Paste (in text input screen) | Accepts input from console |

### HUD
- Top left: Key input history
- Bottom left: Displays invincibility and auto-paint flags, fps, environmental information like underwater status, player coordinates, current tick/server tick/tickrate
- Lines from the player: Red lines for items, yellow for coins
- Red Circle: Enemy detection range (enemies with ranged attacks will shoot if the player is within this range and facing their direction, enemies with melee attacks will deal damage based on proximity within the range)
- Pink marks on walls: Indicates double-jump possible. Press N while moving toward the object to double-jump from the top edge of the object

### Important Things to Remember
Since the server sends packets at 180 ticks, you can undo/redo ticks within that range.  
If Arcade mode exists, you’ll need to copy and paste the code from #shared to start it (this is pushed at startup).  
To apply extra_items, you’ll need to add it to `config#extra_items` (this is pushed at startup).

### How to Execute Pathfinding
- Install `rustup` and `maturin`
- Run `cheats-rust/build.sh`
- Execute the displayed `pip install ...` command

### Runtime Arguments
  - `--stars [STARS]`: Changes the number of stars you start with
  - `--go-boss`: Automatically holds the A key at game startup and goes straight to the boss room (for syncing the tick when entering the boss room)

### How to Use
Generally, you should run in `--standalone` mode when playing locally (features like invincibility and backups only work in standalone mode).  
If you take damage, you can go back and retry using Tick Undo/Redo. If you want to move slowly, adjust the TickRate or pause ticks and proceed one tick at a time.  
Once you reach the desired location, save the key history and share it as needed.  
Be cautious: enemy firing cycles and facing directions won’t reset with the R key reset. You need to reset the map (which is on by default) to correctly replay key histories.

Auto paint calculates the target image using the `calc_painting_target_image` function. Modify this function if you want to use auto paint.  
The return value is a 2D array of integers, where -1 indicates a blank, and other values correspond to the colors in `PaintingSystem#all_colors`.  
With the Pencil equipped, enabling auto paint will show a red frame and automatically paint (assuming zero gravity).  
It’s okay if all pixels in the frame are highlighted white.

### Sections Likely to be Modified
- If you want to modify the key inputs the game receives, use `_pressed_key_hook`
- If you want to hook a specific key input and execute something, modify `macros#*_key_pressed`
  - You can reference `fire_all_guns` for generating and executing macros via code.
  - If you want to do something at the start of the next tick, add a function to `kstate.next_tick_tasks`
- If you want to render something, use `render_hud`
