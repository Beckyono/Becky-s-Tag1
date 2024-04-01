import pygame
import time
import random as r
import math 
from Player import Player
from NPC import NPC
from FlashLightUtils import Boundary,Vector,Circle
from MapStates import gen_map, find_spawn_point;
from CreateMaps import choose_random_map, choose_map, get_last_map
from GameTimer import GameTimer
from ClientSocket import ClientSocket


SLEEPTIME = 0.1
class GameState:
    def __init__(self,name):
        pygame.mixer.init()
        self.bg_music_path = 'app/client/src/assets/music/gamemusic.mp3'
        self.ding_sound_path = 'app/client/src/assets/music/ding.mp3'
        self.flashlight_sound_path = 'app/client/src/assets/music/flashlight.mp3'
        self.bg_music = pygame.mixer.Sound(self.bg_music_path)
        self.bg_music.set_volume(0.3 * self.state_machine.master_volume)
        self.game_timer = None
        self.ding_sound = pygame.mixer.Sound(self.ding_sound_path)
        self.flashlight_sound = pygame.mixer.Sound(self.flashlight_sound_path)
        self.name = name
        self.state_machine = None
        self.player = None
        self.map = None
        self.map_img = None
        self.box_resolution = 50
        self.mouseX = 0
        self.mouseY = 0
        self.mouseB = -1
        self.reset_once = False
        self.clock = pygame.time.Clock()
        self.debug_mode = False
        self.walls = []
        self.objects = []
        self.round_started = False
        return
    
    def reset_map(self):
        if(not self.reset_once):
            pygame.mixer.Channel(1).play(self.ding_sound,fade_ms=100)

            self.state_machine.client_socket.send_data("map-req")
            time.sleep(SLEEPTIME)    
            self.map = choose_map("maps.json",self.state_machine.client_socket.map_name)

            valid_x, valid_y = find_spawn_point(self.map, self.box_resolution)
            self.player = Player(valid_x, valid_y,5)

            self.objects = []
            self.walls = []
            self.gen_boundaries()
            self.draw_map()
            self.reset_once = True
        return


    def enter(self):
        self.state_machine.client_socket = ClientSocket(self.state_machine.ip_address)
        if(self.state_machine.client_socket.inited):
            self.state_machine.client_socket.start_thread()
        else:
            self.state_machine.transition("message","Failed To Connect to Server")

        pygame.mixer.music.stop()
        self.state_machine.player_score = 0

        self.game_timer = GameTimer((100,200),color=(255,255,255))
        pygame.mixer.Channel(0).play(self.bg_music,loops=-1)
        
        self.state_machine.client_socket.send_data("map-req")
        time.sleep(SLEEPTIME)    

        self.map = choose_map("maps.json",self.state_machine.client_socket.map_name)

        valid_x, valid_y = find_spawn_point(self.map, self.box_resolution)
        self.player = Player(valid_x, valid_y,5)
        
        valid_x, valid_y = find_spawn_point(self.map, self.box_resolution)
        self.gen_boundaries()
        self.draw_map()
        return
    
    def leave(self):
        # make sure this socket dies
        if(self.state_machine.client_socket.admin and not self.round_started):
            self.state_machine.client_socket.send_data("get-admin")
            time.sleep(SLEEPTIME)    

        self.state_machine.client_socket.send_data("kill-socket")
        time.sleep(SLEEPTIME)  

        pygame.mixer.Channel(0).stop()
        pygame.mixer.Channel(1).stop()
        self.walls = []
        self.objects = []
        return
    
    def get_val_from_map(self,x,y):
        x = int(x)
        y = int(y)
        if((0 <= x and x <= len(self.map[0])-1) and (0 <= y and y <= len(self.map)-1)):
            return self.map[y][x]
        return None
    
    def gen_lines(self, x_offset, y_offset, x_check, y_check):
        res = self.box_resolution

        def create_vector(x, y, is_horizontal):
            if is_horizontal:
                return Vector(x * res, y * res + y_offset), Vector(x * res + res, y * res + y_offset)
            else:
                return Vector(x * res + x_offset, y * res), Vector(x * res + x_offset, y * res + res)

        def add_wall(start_vector, end_vector):
            self.walls.append(Boundary(start_vector, end_vector))

        for y in range(len(self.map)):
            start_vector = None

            for x in range(len(self.map[0])):
                val = self.get_val_from_map(x, y)

                if val != 0 and start_vector is None:
                    if self.get_val_from_map(x + x_check, y + y_check) == 0:
                        start_vector, end_vector = create_vector(x, y, is_horizontal=(y_check != 0))
                elif val != 0 and start_vector is not None:
                    if self.get_val_from_map(x + x_check, y + y_check) == 0:
                        end_vector = create_vector(x, y, is_horizontal=(y_check != 0))[1]
                    else:
                        add_wall(start_vector, end_vector)
                        start_vector = None
                elif val == 0 and start_vector is not None:
                    add_wall(start_vector, end_vector)
                    start_vector = None

            if start_vector is not None:
                add_wall(start_vector, end_vector)

    def gen_boundaries(self):
        self.gen_lines(self.box_resolution, 0, 1, 0)
        self.gen_lines(0, 0, -1, 0)
        self.gen_lines(0, self.box_resolution, 0, 1)
        self.gen_lines(0, 0, 0, -1)
        return
           
    def draw_map(self):
        res  = self.box_resolution
        self.map_img = pygame.Surface((self.state_machine.window_width, self.state_machine.window_height))
        for i in range(0,len(self.map)):
            for j in range(0,len(self.map[0])):
                 col = (0,0,0)
                 if(self.map[i][j] == 1):
                     col = (255,255,255)
                 self.map_img.fill(col,(j*res,i*res,res,res)) 
        return

    def render(self,window=None):
        res  = self.box_resolution
        background_color = (0, 0, 0)
        window.fill(background_color)
        text_msg = "Waiting To Start Match."
        text_col = (255,255,255)

        if(self.state_machine.client_socket.admin):
            text_msg = "Hit P to Start Match..."
        if(self.debug_mode):
            text_col = (0,0,0)
            window.blit(self.map_img, (0,0))

        if(not self.round_started):
                font = pygame.font.SysFont('Georgia',30)
                text = font.render(text_msg, True, text_col) 
                text_rect = text.get_rect()
                text_rect.center = (160, 30) 
                window.blit(text, text_rect)

        self.game_timer.render(window,self.debug_mode,self.state_machine.window_width)
                       
        self.player.render(window,self.walls,self.objects)
        if(self.debug_mode):
            for wall in self.walls:
                wall.render(window)
            for obj in self.objects:
                obj.render(window)
        return

    def update(self):
        
        #dont ask...
        self.round_started = self.state_machine.client_socket.round_started

        #Prevent from Joining on lobby full
        if(self.state_machine.client_socket.lobby_full):
            self.state_machine.transition("message","Lobby Full or Round Started")

        self.objects = []
        self.game_timer.time = 10

        self.game_timer.update(self.state_machine.client_socket.round_timer) 

        if(self.game_timer.time > 0):
            self.reset_once = False
            keys = pygame.key.get_pressed()
            self.mouseX,self.mouseY = pygame.mouse.get_pos()
            self.mouseB = pygame.mouse.get_pressed()

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.debug_mode = not self.debug_mode
                    if event.key == pygame.K_ESCAPE:
                        if(self.round_started):
                            self.state_machine.transition("message","You Lose")
                        else:
                            self.state_machine.transition("message","Leaving Lobby")
                    if event.key == pygame.K_p:
                        if(self.state_machine.client_socket.admin and not self.round_started):
                            self.round_started = True
                            for i in range(2):
                                self.state_machine.client_socket.send_data("start-round")
                                time.sleep(SLEEPTIME)

                if event.type == pygame.QUIT:
                    self.state_machine.window_should_close = True
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pygame.mixer.Channel(1).play(self.flashlight_sound,fade_ms=100)

            pdata = self.state_machine.client_socket.player_data
            if(pdata):
                for key,data in pdata.items():
                    if(key != self.state_machine.client_socket.id):
                        self.objects.append(NPC(data[0],data[1],5))
                
            self.player.update(keys,(self.mouseX,self.mouseY,self.mouseB),self.map,self.box_resolution,self.objects) 
            self.state_machine.client_socket.send_data("player-tick",[self.player.x,self.player.y])
        
        elif(self.game_timer.time <= self.state_machine.server_time_end):
            self.reset_map()

        self.clock.tick(60)  
        return