import game.components.textbox
import kijitora.kstate as kstate
from game.engine.keys import Keys


class HackedTextbox(game.components.textbox.Textbox):
    def init_text(self, text: str, choices, free_text):
        super().init_text(text, choices, free_text)

        # ソケットがあるときは表示テキストをすべて送信する
        if kstate.interactive_sock is None:
            return

        try:
            kstate.interactive_received = False
            kstate.interactive_sock.sendline(text)

            if free_text:
                kstate.interactive_sock.sendline("FREETEXT")
            else:
                kstate.interactive_sock.sendline("CHOICES")
                for choice in choices:
                    kstate.interactive_sock.sendline(choice)
        except EOFError:
            print("[+] Connection closed (sendline)")
            kstate.interactive_sock = None

    def tick(self, newly_pressed_keys):
        super().tick(newly_pressed_keys)

        if kstate.interactive_sock is None:
            return
        
        if not self.choices_active() and kstate.interactive_selected:
            kstate.interactive_selected = False

        # ソケットがあるときは自動スキップする
        if self.done_scrolling:
            # ソケットが生きているかを確認する
            try:
                kstate.interactive_sock.recv(0, timeout=0.01)
            except EOFError:
                print("[+] Connection closed")
                kstate.interactive_sock = None
                return

            if self.choices_active() and not kstate.interactive_selected: # 選択肢
                # 先にキーを消費するまで待つ
                if kstate.interactive_key_next is None:
                    try:
                        choice = kstate.interactive_sock.recvline(keepends=False)
                    except EOFError:
                        print("[+] Connection closed (during choice)")
                        kstate.interactive_sock = None
                        return
                    print("Interactive choice:", choice.decode())
                    if choice.lower() == b"up":
                        kstate.interactive_key_next = Keys.W
                    elif choice.lower() == b"down":
                        kstate.interactive_key_next = Keys.S
                    elif choice.lower() in [b"ok", b"enter", b"select", b"choose"]:
                        kstate.interactive_key_next = Keys.E
                        kstate.interactive_selected = True
                    else:
                        print("[-] Unknown choice")
                        kstate.interactive_sock.close()
                        kstate.interactive_sock = None
                        return

            elif self.free_text_active(): # 自由記述
                pass

            elif self.get_close_key() not in newly_pressed_keys: # 連打扱いにならなければ送る
                if kstate.interactive_key_next is None:
                    kstate.interactive_key_next = Keys.E

        elif self.from_server and self.text_objs is None:
            pass

        elif Keys.E not in newly_pressed_keys: # 連打扱いにならなければ送る
            if kstate.interactive_key_next is None:
                kstate.interactive_key_next = Keys.E

