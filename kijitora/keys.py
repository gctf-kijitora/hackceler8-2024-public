from game.engine.keys import Keys
def get_keycode(key_name): 
    if Keys._Keys__ui_key_cls is None:
        print("[+] Keys is not initialized! Call this method after the game is started")
    key_val = getattr(Keys._Keys__ui_key_cls, key_name)
    if key_val is None:
        print(f"[!] {key_name} is not found in key table")
    return key_val
