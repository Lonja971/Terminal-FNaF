import time
from core.window.base import Window
from utils.terminal import clear
from ui.elements import input_field
from utils.terminal import ensure_json_file

class NewBeginingWindow(Window):
    def __init__(self):
        self.default_interlocutor = "chief"

    def print_dialog_phrase(self, text, who, is_new_line=False):
        if is_new_line:
            print()
        print(f"[{who}] {text}")

    def render_window(self, wm):
        clear()
        save = ensure_json_file("config/save.json", "config/save.template.json")

        while True:
            self.print_dialog_phrase(wm.translator.t("what_is_your_name"), wm.translator.t("manager"))
            name = input_field()
            if not name.strip():
                self.print_dialog_phrase(wm.translator.t("I_didn't_hear"), wm.translator.t("manager"), "", True)
            else:
                break

        self.print_dialog_phrase(wm.translator.t("my_name_is", name=name), wm.translator.t("me"))

        save["player"]["name"] = name
        self.overwrite_json("config/save.json", save)

        time.sleep(1.5)
        self.print_dialog_phrase(wm.translator.t("welcome_to_the_pizzeria", name=name), wm.translator.t("manager"), True)
        time.sleep(3)
        clear()
        time.sleep(3)
        return wm.pop()