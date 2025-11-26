import random, time
from config.location import LOCATION
from core.translator import Translator

def debug_log(message):
    with open("debug_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {message}\n")

class Animatronic:
    def __init__(self, name, default_position_index, path_graph, attack_trigger, wait_delay_range, attack_delay, activation_time, add_event_comment, reduce_power):
        self.name = name
        self.camera_state = 0
        self.path_graph = path_graph
        self.activation_time = activation_time
        self.current_position_index = default_position_index
        self.default_position_index = default_position_index
        self.last_position_index = None

        self.time_in_position = 0
        self.time_in_position_tick = 0.5
        self.time_before_attack = 0
        self.time_before_attack_tick = 0.5
        self.time_in_trigger_point = 0
        self.is_attacking = False

        self.wait_delay_range = wait_delay_range
        self.current_wait_delay = random.uniform(*wait_delay_range)

        self.attack_trigger = attack_trigger
        self.add_event_comment = add_event_comment
        self.reduce_power = reduce_power

        if attack_trigger["type"] == "position":
            self.self_update_position = True
            self.self_reseat = True
            self.attack_delay = attack_delay
            self.attack_wait_time = random.choice(attack_delay["wait_time"])
            self.attack_need_time = random.choice(attack_delay["need_time"])

        elif attack_trigger["type"] == "laugh":
            self.self_update_position = True
            self.self_reseat = False
            self.attack_delays = attack_delay
            self.current_attack_delay = random.choice(attack_delay)
            self.laugh_number = 0

        elif attack_trigger["type"] == "run":
            self.with_camera_time_in_position_tick = 0.2
            self.attack_power_cost = attack_trigger["power_cost"]
            self.self_update_position = False
            self.self_reseat = False
            self.is_running = False
            self.active_pose = 0
            self.attack_delays = attack_delay
            self.current_attack_delay = random.choice(attack_delay)
            self.message_is_running = False

        self.translator = Translator()
    
    def set_new_wait_delay(self):
        self.current_wait_delay = random.uniform(*self.wait_delay_range)

    def set_new_attack_delay(self):
        if self.attack_trigger["type"] == "position":
            self.attack_wait_time = random.choice(self.attack_delay["wait_time"])
            self.attack_need_time = random.choice(self.attack_delay["need_time"])
        elif self.attack_trigger["type"] == "laugh":
            self.current_attack_delay = random.choice(self.attack_delays)

    def reset_position(self, also_attacking=False):
        if also_attacking:
            self.is_attacking = False
        
        if self.attack_trigger["type"] == "laugh":
            self.laugh_number = 0

        if self.attack_trigger["type"] == "run":
            self.message_is_running = False
            self.active_pose = 0

        self.current_position_index = self.default_position_index
        self.time_in_position = 0
        self.time_in_trigger_point = 0
        self.time_before_attack = 0
        self.set_new_wait_delay()
        self.set_new_attack_delay()
        self.camera_state = 0

    def advance(self, office_position_index, doors, doors_index, current_camera, camera_data):
        #---ТІ-ЩО-ДО-ДВЕРЕЙ-ЙДУТЬ---
        if self.attack_trigger["type"] == "position" and self.attack_trigger["position"] == self.current_position_index:
            door_name = doors_index[self.attack_trigger["position"]]
            if not doors[door_name]:
                debug_log(f"{self.name} треба для атаки: {self.time_before_attack} >= {self.attack_need_time}")
                if self.time_before_attack >= self.attack_need_time:
                    self.current_position_index = office_position_index
                    self.is_attacking = True
                else:
                    self.time_before_attack += self.time_before_attack_tick
                
            if self.time_in_trigger_point > self.attack_wait_time and doors[door_name]:
                self.reset_position()
            else:
                self.time_in_trigger_point += self.time_in_position_tick
                debug_log(f"{self.name} стоїть вже {self.time_in_trigger_point}. Всього він збирається стояти: {self.attack_wait_time}")

        #---ФРЕДДІ---
        elif self.attack_trigger["type"] == "laugh" and self.laugh_number == self.attack_trigger["number"]:
            debug_log(f"{self.name} збирається атакувати [{self.laugh_number}] {self.time_before_attack} >= {self.current_attack_delay}")
            if self.time_before_attack >= self.current_attack_delay:
                self.current_position_index = office_position_index
                self.is_attacking = True
                debug_log(f"{self.name} АТАКУЄ")
                self.add_event_comment(self.name, f"[{self.name}] {self.translator.t('angry_freddy_sounds')}", 4)
            self.time_before_attack += 0.5

        #---ФОКСІ---
        elif self.attack_trigger["type"] == "run":
            time_in_position_tick = self.time_before_attack_tick

            if current_camera["is_open"] and camera_data["position"] == self.default_position_index:
                time_in_position_tick = self.with_camera_time_in_position_tick

            if self.active_pose >= self.attack_trigger["attack_pose"]:
                debug_log(f"{self.name} готовий до атаки {self.time_before_attack} >= {self.current_attack_delay}")
                if not self.message_is_running:
                    self.message_is_running = True
                    #self.add_event_comment(self.name, f"[{self.name}] {self.translator.t("foxy_running")}", 3)

                if self.time_before_attack >= self.current_attack_delay:
                    debug_log(f"{self.name} АТАКУЄ")
                    self.is_attacking = True
                    self.add_event_comment(self.name, f"[{self.name}] {self.translator.t('angry_foxy_sounds')}", 3)
                    self.reduce_power(self.attack_power_cost)
                else:
                    self.time_before_attack += self.time_before_attack_tick
            elif self.time_in_position >= self.current_wait_delay:
                self.active_pose += 1
                self.time_in_position = 0
                self.camera_state = self.active_pose
                self.set_new_wait_delay()
                debug_log(f"{self.name} в новій позі: {self.active_pose}")
            else:
                self.time_in_position += time_in_position_tick

        #---ЗМІНА-ПОЗИЦІЇ---
        elif self.time_in_position >= self.current_wait_delay and self.self_update_position:
            next_positions = self.path_graph[self.current_position_index]
            if self.last_position_index in next_positions:
                next_positions.remove(self.last_position_index)

            if next_positions:
                old_position_index = self.current_position_index
                self.current_position_index = random.choice(next_positions)
                debug_log(f"{self.name} перейшов у позицію {LOCATION[self.current_position_index]['name']}")
                if self.attack_trigger["type"] == "laugh":
                    self.laugh_number += 1
                    debug_log(f"{self.name} Сміється [{self.laugh_number}] {LOCATION[self.current_position_index]['name']}")
                    self.add_event_comment(self.name, f"[{self.name}] {self.translator.t('ho_ho_ho')}", 4)

                self.time_in_position = 0
                self.last_position_index = old_position_index
                self.set_new_wait_delay()
                self.set_new_attack_delay()

        self.time_in_position += self.time_in_position_tick
