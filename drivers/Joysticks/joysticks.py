import pygame
from pygame.joystick import Joystick
import time
import ecal.core.core as ecal_core
from ecal.core.publisher import ProtoPublisher

ATTACK3_CONF = {
    "X": 1, #axe
    "X_sens" : -1, #facteur
    "Y": 0, #axe
    "Y_sens" : 1,
    "angle_gauche": 3, #bouton
    "angle_droit":4, #bouton
}

class JoystickEcal ():
    def __init__(self):
        self.joystick: Joystick | None = None
        self.buttons = []
        self.axis = []
        self.conf = ATTACK3_CONF

        ecal_core.initialize([], "Joystick")
        self.publisher = ProtoPublisher("Joystick_topic")
        
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

    def button_get_value(self,n):
        if self.joystick is not None:
            return self.joystick.get_button(n)
    
    def axis_get_value(self,n):
        if self.joystick is not None:
            return round(self.joystick.get_axis(n),2)

    def update_value(self):
        if self.joystick is not None:
            for n in range(self.joystick.get_numbuttons()):
                self.buttons[n] = self.button_get_value(n)

            for n in range(self.joystick.get_numaxes()):
                self.axis[n] = self.axis_get_value(n)
            


pygame.init()
pygame.joystick.init()

joysticks_ecal = JoystickEcal()        
joysticks_ecal.open()



while True :
    for event in pygame.event.get():
        joysticks_ecal.update_value()
        print(joysticks_ecal)
        
    time.sleep(0.1)
    

