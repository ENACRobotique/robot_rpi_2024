#!/usr/bin/env python
import pygame
from pygame.joystick import Joystick
import time
import ecal.core.core as ecal_core
from ecal.core.publisher import ProtoPublisher
import generated.robot_state_pb2 as robot_state_pb2
import generated.messages_pb2 as message_pb2



MAX_SPEED = 300
V_THETA = 1.5

FRAME_W = 1
FRAME_R = 0

ATTACK3_CONF = {
    "X": 1, #axe
    "X_sens" : -1, #facteur
    "X_offset": 0.,
    "X_dead_zone": 0.1,
    "Y": 0, #axe
    "Y_sens" : -1,
    "Y_offset" : 0.,
    "Y_dead_zone": 0.1,
    "angle_gauche": 3, #bouton
    "angle_droit":4, #bouton
    "vitesse_supra_luminique": 0 #bouton
}

BATTLETRON = {
    "X": 1, #axe
    "X_sens" : -1, #facteur
    "X_offset": 0.15,
    "X_dead_zone": 0.1,
    "Y": 0, #axe
    "Y_sens" : -1,
    "Y_offset" : -0.6,
    "Y_dead_zone": 0.1,
    "THETA": 3, #axe
    "THETA_sens" : -1,
    "THETA_offset" : 0.1, #à régler
    "THETA_dead_zone": 0.1, # à régler
    "frame_robot":1, #bouton CARRÉ
    "frame_table":3, #bouton ROND
    "theta_supra_luminique":12, #bouton
    "vitesse_supra_luminique": 11 #bouton
}
class JoystickEcal ():
    def __init__(self):
        self.joystick: Joystick = None
        self.buttons = []
        self.axis = []
        self.conf = None
        self.frame = FRAME_R

        ecal_core.initialize([], "Joystick")
        time.sleep(1) # on laisse ecal se reveiller

        self.speed_publisher = ProtoPublisher("speed_cons", robot_state_pb2.Speed)
        self.message = robot_state_pb2.Speed()
        self.Mode_pub = ProtoPublisher("system_modes",message_pb2.System)
        # self.change_frame() # on passe en frame Robot
        
    def __repr__(self):
        return f"{len(self.axis)} Axis: {self.axis} \t{len(self.buttons)} Buttons : {self.buttons}"

    def open(self):
        while (self.joystick == None):
            for event in pygame.event.get():
                if event.type == pygame.JOYDEVICEADDED:
                    self.joystick = pygame.joystick.Joystick(event.device_index)
                    self.axis = [self.axis_get_value(n) for n in range(self.joystick.get_numaxes())]
                    self.buttons = [self.button_get_value(n) for n in range(self.joystick.get_numbuttons())]
                    time.sleep(0.5)
                    print(f"Manette {self.joystick.get_name()} connectée")
    def set_conf(self, conf):
        self.conf = conf


    def button_get_value(self,n):
        return self.joystick.get_button(n)
    
    def axis_get_value(self,n):
            return round(self.joystick.get_axis(n),2)

    def update_value(self):
        for n in range(self.joystick.get_numbuttons()):
            self.buttons[n] = self.button_get_value(n)

        for n in range(self.joystick.get_numaxes()):
            self.axis[n] = self.axis_get_value(n)

    def publish_command(self):
        vx = (MAX_SPEED * self.axis[self.conf["X"]] * self.conf["X_sens"] - self.conf["X_offset"]) * (1 + self.buttons[self.conf["vitesse_supra_luminique"]])
        self.message.vx = vx if abs(self.axis[self.conf["X"]])> self.conf["X_dead_zone"] else 0
        vy = (MAX_SPEED * self.axis[self.conf["Y"]] * self.conf["Y_sens"] - self.conf["Y_offset"]) * (1 + self.buttons[self.conf["vitesse_supra_luminique"]])
        self.message.vy = vy if abs(self.axis[self.conf["Y"]]) > self.conf["Y_dead_zone"] else 0
        
        if self.conf == BATTLETRON:
            vtheta = (V_THETA * self.axis[self.conf["THETA"]] * self.conf["THETA_sens"] - self.conf["THETA_offset"]) * (1 + self.buttons[self.conf["theta_supra_luminique"]])
            self.message.vtheta = vtheta if abs(self.axis[self.conf["THETA"]]) > self.conf["THETA_dead_zone"] else 0
        if self.conf == ATTACK3_CONF:
            self.message.vtheta = V_THETA * (self.buttons[self.conf["angle_gauche"]] - self.buttons[self.conf["angle_droit"]]) * (1 + self.buttons[self.conf["vitesse_supra_luminique"]])
        
        print(self.message)
        self.speed_publisher.send(self.message)
        if self.buttons[self.conf["frame_robot"]]:
            # print("LA",self.buttons[self.conf["frame_robot"]])
            self.set_frame(FRAME_R)
        if self.buttons[self.conf["frame_table"]]:
            # print("LA",self.buttons[self.conf["frame_robot"]])
            self.set_frame(FRAME_W)

    def set_mode(self, asserv, guidance):
        print(asserv,guidance)
        mode = message_pb2.System()
        mode.asserv = asserv
        mode.guidance = guidance
        mode.odometry = message_pb2.System.OdometryFlags.ODOMETRY_ENABLED
        self.Mode_pub.send(mode)
    
    def set_frame(self,frame):
        
        if frame == FRAME_R:
            self.frame = FRAME_R
            print("mode ",message_pb2.System.GuidanceFlags.GUIDANCE_ROBOT_FRAME | message_pb2.System.GuidanceFlags.GUIDANCE_BASIC)
            self.set_mode(message_pb2.System.AsservFlags.ASSERV_POS,message_pb2.System.GuidanceFlags.GUIDANCE_ROBOT_FRAME | message_pb2.System.GuidanceFlags.GUIDANCE_BASIC)
        
        elif frame == FRAME_W:
            self.frame = FRAME_W
            self.set_mode(message_pb2.System.AsservFlags.ASSERV_POS,message_pb2.System.GuidanceFlags.GUIDANCE_BASIC)
        print("Frame 1W|0R = ", self.frame)
        


pygame.init()
pygame.joystick.init()

joysticks_ecal = JoystickEcal()        
joysticks_ecal.open()
joysticks_ecal.set_conf(BATTLETRON)

while True :
    for event in pygame.event.get():
        joysticks_ecal.update_value()
        print(joysticks_ecal)
    joysticks_ecal.publish_command()  
    time.sleep(0.1)
    

