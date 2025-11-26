import curses, time, re
from config.animatronics import ANIMATRONICS
from ui.sprites.logo import GAME_OVER_PICTURE_DARK, SIX_AM_PICTURE_DARK
from ui.sprites.office import PAUSE
from ui.sprites.office import OFFICE_CENTER
from ui.sprites.left_door import DOOR_LEFT, DOOR_LEFT_BONNIE, DoorLeftSprites
from ui.sprites.right_door import DOOR_RIGHT, DOOR_RIGHT_CHICA, DoorRightSprites
from ui.sprites.cameras import CAMERAS, CamerasMapSprite
from core.translator import Translator
from core.window.base import Window
from utils.terminal import debug_log, shorten

class GameRenderer(Window):
    def __init__(self, stdscr, player_name, state, current_night):
        self.player_name = player_name
        self.stdscr = stdscr
        self.state = state
        self.hours = ["12", "01", "02", "03", "04", "05", "06"]
        self.foxy_camera_info = {
            "location": 12,
            "camera_num": 5,
        }

        self._init_colors()
        self.left_padding = 2
        self.current_night = current_night
        self.action_comment = None

        self.translator = Translator()
        self.cameras_map_sprite = CamerasMapSprite(self.translator)
        self.door_left_sprites = DoorLeftSprites(self.translator)
        self.door_right_sprites = DoorRightSprites(self.translator)

        self.screamer_frame_delay = 0.05
        self.screamer_post_delay = 0.5

    def _init_colors(self):
        curses.start_color()
        if curses.has_colors() and curses.COLORS >= 256:
            curses.use_default_colors()
        GRAY = 244
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, -1)
        curses.init_pair(4, 130, -1)
        curses.init_pair(10, 250, curses.COLOR_BLACK)
        curses.init_pair(11, GRAY, -1)

    def render_all(self, current_view, door_animatronics, is_flickering):
        self.stdscr.clear()
        self.render_top()
        self.render_content(current_view,door_animatronics, is_flickering)
        self.render_bottom()
        self.stdscr.refresh()

    def render_top(self):
        with self.state.lock:
            hours = self.hours[self.state.time["hour_index"]]
            int_minutes = int(self.state.time["min"])

            minutes = "0" + str(int_minutes) if len(str(int_minutes)) <= 1 else int_minutes
            power = int(self.state.power)
            power_usage = self.state.power_usage

        line = f"|{' '*self.left_padding}{self.translator.t('night')}: {self.current_night} | {hours}:{minutes}   {self.translator.t('energy')}: {power}% :{'[]' * power_usage['items']}"
        line = line.ljust(99) + "|"

        self.stdscr.attron(curses.color_pair(1))
        self.stdscr.addstr(0, 0, "=" * 100)
        self.stdscr.addstr(1, 0, " " * 100)
        self.stdscr.addstr(1, 0, line)
        self.stdscr.addstr(2, 0, "=" * 100)
        self.stdscr.attroff(curses.color_pair(1))
        self.stdscr.refresh()

    def render_bottom(self):
        action_comment = self.action_comment or ""
        action_comment = action_comment[:28].ljust(28)
        player_name = shorten(self.player_name, 12)

        name_status = f"<{player_name}> [{self.translator.t('ALIVE')}]".ljust(25)
        base_line = f"|{self.left_padding * ' '}{name_status} {action_comment}"

        # Початок рендеру
        self.stdscr.attron(curses.color_pair(2))
        self.stdscr.addstr(33, 0, "=" * 100)
        self.stdscr.addstr(34, 0, " " * 100)
        self.stdscr.addstr(34, 0, base_line)
        self.stdscr.attroff(curses.color_pair(2))

        x_offset = len(base_line)

        for name in ["Foxy", "Freddy"]:
            comment = self.state.event_comments.get(name, {"text": "", "color": None})
            text = comment.get("text", "")[:35].ljust(35)
            color = comment.get("color")

            if color is not None:
                self.stdscr.attron(curses.color_pair(color))
            self.stdscr.addstr(34, x_offset, text)
            if color is not None:
                self.stdscr.attroff(curses.color_pair(color))

            x_offset += 20

        self.stdscr.attron(curses.color_pair(2))
        self.stdscr.addstr(34, 99, "|")
        self.stdscr.addstr(35, 0, "=" * 100)
        self.stdscr.attroff(curses.color_pair(2))

        self.stdscr.refresh()

    def render_content(self, current_view, door_animatronics, is_flickering=False):
        color_pair = 11 if is_flickering else 10
        self.stdscr.attron(curses.color_pair(color_pair))
        self.set_action_comment(None)

        for i in range(3, 30):
            self.stdscr.move(i, 0)
            self.stdscr.clrtoeol()

        lines = []
        if self.state.is_pause == True:
            lines = PAUSE
        elif self.state.current_camera["is_open"]:
            lines = self.get_camera_view()
        elif current_view == "center":
            lines = self.get_office()
        elif current_view == "left":
            lines = self.get_left_door(door_animatronics)
        elif current_view == "right":
            lines = self.get_right_door(door_animatronics)

        for idx, line in enumerate(lines):
            self.stdscr.addstr(3 + idx, 0, line[:101])

        self.stdscr.attroff(curses.color_pair(color_pair))
        self.stdscr.refresh()
    
    def render_camers_map(self):
        start_y = 3
        start_x = 102
        current_camera = self.state.current_camera["number"]
        current_camera_position = self.state.cameras[current_camera]["position"]
        sprite_lines = self.cameras_map_sprite.get_cameras_map_sprite(current_camera, current_camera_position)

        camera_pattern = re.compile(r"\[\d+\]")
        cam_tag_pattern = re.compile(r"\[CAM_\d+\]")

        for i, line in enumerate(sprite_lines):
            y = start_y + i
            x = start_x
            idx = 0

            # --- Додаємо | на позиції 45 ---
            if len(line) < 45:
                line = line.ljust(44) + "|"

            # --- Обробляємо патерни ---
            for match in camera_pattern.finditer(line):
                start, end = match.span()
                self.stdscr.addstr(y, x + idx, line[idx:start])
                camera_str = match.group()
                camera_num = int(camera_str.strip("[]"))
                color = curses.color_pair(2) if camera_num == current_camera else curses.color_pair(1)
                self.stdscr.addstr(y, x + start, camera_str, color)
                idx = end

            # Обробляємо [CAM n] (нижній рядок)
            for match in cam_tag_pattern.finditer(line):
                start, end = match.span()
                self.stdscr.addstr(y, x + idx, line[idx:start])
                self.stdscr.addstr(y, x + start, match.group(), curses.color_pair(2))
                idx = end

            # Друкуємо залишок рядка
            self.stdscr.addstr(y, x + idx, line[idx:])

        self.stdscr.refresh()

    def render_screamer(self, killer_name):
        self.stdscr.clear()
        self.stdscr.attron(curses.color_pair(10))

        frames = ANIMATRONICS[killer_name]["screamer_sprites"]

        for frame in frames:
            for i in range(3, 30):
                self.stdscr.move(i, 0)
                self.stdscr.clrtoeol()

            for idx, line in enumerate(frame):
                if 3 + idx >= 30:
                    break
                self.stdscr.addstr(3 + idx, 0, line[:100])

            self.stdscr.refresh()
            time.sleep(self.screamer_frame_delay)

        self.stdscr.attroff(curses.color_pair(10))

        time.sleep(self.screamer_post_delay)

    def render_game_over(self):
        anim_info = {
            "Freddy": "freddy_info",
            "Chica": "chica_info",
            "Bonnie": "bonnie_info",
            "Foxy": "foxy_info"
        }
        self.stdscr.clear()
        reason = self.state.game_status.get("reason")
        end_picture = GAME_OVER_PICTURE_DARK

        if reason == "morning":
            end_picture = SIX_AM_PICTURE_DARK

        picture_lines = end_picture.split("\n")
        start_line = max(0, (30 - len(picture_lines)) // 2)

        for i, line in enumerate(picture_lines):
            if i + start_line < 30:
                self.stdscr.addstr(start_line + i, 2, line[:100])

        if reason == "morning":
            self.stdscr.addstr(32, 2, self.translator.t("survived_until_the_morning"))
        elif reason == "killed":
            killed_by = self.state.game_status.get("killed_by", "unknown")
            info_lines = self.translator.t(anim_info[killed_by], anim_name=killed_by).split("\n")
            start_y = 33
            start_x = 2

            self.stdscr.addstr(31, 2, self.translator.t("caught", killed_by=killed_by))
            if any(line.strip() for line in info_lines):
                for i, line in enumerate(info_lines):
                    self.stdscr.addstr(start_y + i, start_x, line, curses.A_BOLD)
        else:
            self.stdscr.addstr(31, 2, self.translator.t("the_reason_is_unknown"))

        self.stdscr.addstr(36, 2, self.translator.t("press_q_to_exit"), curses.A_BOLD)
        self.stdscr.refresh()

    def get_office(self):
        return OFFICE_CENTER

    def get_left_door(self, door_animatronics):
        door_picture = DOOR_LEFT
        action_comment = None

        if self.state.light["left"]:
            if door_animatronics["left"]:
                if self.state.doors["left"]:
                    action_comment = self.translator.t("bonnie_in_the_door")
                door_picture = DOOR_LEFT_BONNIE
            else:
                action_comment = self.translator.t("no_one")
                door_picture = self.door_left_sprites.get_door_left_light_sprite()
            
        if self.state.doors["left"]:
            door_picture = self.door_left_sprites.get_door_left_closed_sprite()

        self.set_action_comment(action_comment)
        return door_picture

    def get_right_door(self, door_animatronics):
        door_picture = DOOR_RIGHT
        action_comment = None

        if self.state.light["right"]:
            if door_animatronics['right']:
                if self.state.doors["right"]:
                    action_comment = self.translator.t("chica_in_the_door")
                door_picture = DOOR_RIGHT_CHICA
            else:
                action_comment = self.translator.t("no_one")
                door_picture = self.door_right_sprites.get_door_right_light_sprite()
            
        if self.state.doors["right"]:
            door_picture = self.door_right_sprites.get_door_right_closed_sprite()
        
        self.set_action_comment(action_comment)
        return door_picture
    
    def get_camera_view(self):
        current_camera = self.state.current_camera
        camera_number = current_camera["number"]

        self.render_camers_map()

        current_camera_data = self.state.cameras.get(camera_number)
        if not current_camera_data:
            return CAMERAS["not_found"]
        
        position = current_camera_data["position"]

        position_key = f"position_{position}"
        translated_position = self.translator.t(position_key)
        if translated_position[0] == "[":
            self.set_action_comment(f"[CAM_{camera_number}]")
        else:
            translated_position = shorten(translated_position, 15)
            self.set_action_comment(f"[CAM_{camera_number}] {translated_position}")

        camera_config = CAMERAS.get(position)
        if not camera_config:
            return CAMERAS["not_found"]
        
        if current_camera_data["position"] == self.foxy_camera_info["location"]:
            sprite_key = current_camera_data["view"][0] if current_camera_data["view"] else {"state": 0}
            return camera_config.get(sprite_key["state"], CAMERAS["not_found"])
        
        if current_camera_data["view"]:
            sorted_names = sorted([entity["name"] for entity in current_camera_data["view"]])
            sprite_key = "_".join(sorted_names)
            return camera_config.get(sprite_key, CAMERAS["not_found"])
        
        return camera_config.get("default", CAMERAS["not_found"])

    def set_action_comment(self, comment_text=None):
        self.action_comment = comment_text