from fsm import State
from robot import Robot,Actionneur,ValeurActionneur,XY_ACCURACY,THETA_PINCES_BABORD,THETA_PINCES_TRIBORD, Strat, ACT_TIME
from common import Pos
import time
from enum import Enum
from math import pi, radians, degrees,sqrt
from collections import namedtuple
Plante = namedtuple('plante',['waypoint','azimut'])
Depose = namedtuple('zone_depose',['waypoint','azimut'])
Jardi = namedtuple('jardiniere',['waypoint','azimut'])
Moissonneuse = namedtuple('actionneur',['pince','openPince','closePince','orientation','ax','axUp','axDown', 'theta_inc'])
# coté babord , pince 1 et 2 et ax babord - Coté tribord , pince 3 et 4 et ax tribord , theta pinces repère robot
Moissonneuses = [Moissonneuse(Actionneur.Pince1,ValeurActionneur.OpenPince1,ValeurActionneur.ClosePince1,-THETA_PINCES_BABORD,Actionneur.AxBabord,ValeurActionneur.UpAxBabord,ValeurActionneur.DownAxBabord, radians(-15)),
                 Moissonneuse(Actionneur.Pince2,ValeurActionneur.OpenPince2,ValeurActionneur.ClosePince2,-THETA_PINCES_BABORD,Actionneur.AxBabord,ValeurActionneur.UpAxBabord,ValeurActionneur.DownAxBabord, radians(15)),
                 Moissonneuse(Actionneur.Pince3,ValeurActionneur.OpenPince3,ValeurActionneur.ClosePince3,-THETA_PINCES_TRIBORD,Actionneur.AxTribord,ValeurActionneur.UpAxTribord,ValeurActionneur.DownAxTribord, radians(15)),
                 Moissonneuse(Actionneur.Pince4,ValeurActionneur.OpenPince4,ValeurActionneur.ClosePince4,-THETA_PINCES_TRIBORD,Actionneur.AxTribord,ValeurActionneur.UpAxTribord,ValeurActionneur.DownAxTribord, radians(-15)),
                 ]
LIDAR_TIME= 3 # sec
def timeout(init_time,timeout):
    """Return True if timeout """
    return time.time() - init_time  >= timeout


class NavState(State):
    """ Args : next_state, destination (waypoints only), optional : orientation, enemy_alternative_route, timeout"""

    class MoveStatus(Enum):
        MOVING = 1
        STOPPED = 2
        
    def __init__(self, robot: Robot, globals: dict, args: dict) -> None:
        super().__init__(robot, globals, args)
    
    def enter(self, prev_state: State | None):

        if not 'orientation' in self.args:
            self.args['orientation'] = self.robot.pos.theta
            print(f"pos: {self.robot.pos}")
        print(f"Navigating to {self.args['destination']} with heading {degrees(self.args['orientation'])}° .")
        self.dtheta= self.robot.pathFinder(self.args['destination'],self.args['orientation'])
        self.move_status = self.MoveStatus.STOPPED
        self.t_stop = time.time()
        if "timeout" not in self.args:
            self.args["timeout"] = 5 # default timeout
    
    def loop(self):
        while True:
            x = self.robot.nav_pos[0].x
            y = self.robot.nav_pos[0].y
            
            if self.robot.obstacle_in_way(Pos(x=x,y=y,theta=0)) :
                if self.move_status == self.MoveStatus.STOPPED:# wait timeout before doing other planned action
                    #print(f"obstacle in the way to '{self.robot.nav.chemin[0]}'")
                    #self.robot.setTargetPos(self.robot.pos)
                    if time.time() - self.t_stop > self.args["timeout"] and "alternative" in self.args:
                        print("\nalternative way\n")
                        yield self.args["alternative"]
                    
                elif self.move_status == self.MoveStatus.MOVING: # Stop the robot and start timeout timer
                    #print(f"STOPPING started timer")
                    self.t_stop = time.time()
                    self.robot.setTargetPos(self.robot.pos)
                    self.move_status = self.MoveStatus.STOPPED
            else:
                if self.move_status == self.MoveStatus.STOPPED:
                    self.robot.setTargetPos(self.robot.nav_pos[0])
                    self.move_status = self.MoveStatus.MOVING

                elif self.move_status == self.MoveStatus.MOVING: 
                    if self.robot.hasReachedTarget():
                        del self.robot.nav_pos[0]
                        if self.robot.isNavDestReached():
                            yield self.args['next_state']
                        self.robot.setTargetPos(self.robot.nav_pos[0])
            yield None

    
class EndState(State):
    def enter(self, prev_state: State | None):
        for m in Moissonneuses:
            self.robot.setActionneur(m.pince, m.openPince)
        x_end,y_end = self.robot.nav.getCoords(self.globals['end_pos'])
        x_alt,y_alt = self.robot.nav.getCoords(self.globals['alt_end'])
        if sqrt((x_end-self.robot.pos.x)**2+(y_end-self.robot.pos.y)**2) < XY_ACCURACY:
            self.robot.updateScore(10)
        elif sqrt((x_alt-self.robot.pos.x)**2+(y_alt-self.robot.pos.y)**2) < XY_ACCURACY:
            self.robot.updateScore(10)
        print("The End !")

        while True :
            self.robot.shuffle_play()
            time.sleep(10)


class PanosState(State):
    def __init__(self, robot: Robot, globals, args={}) -> None:
        super().__init__(robot, globals, args)
    
    def enter(self, prev_state: State | None):
        # s'il reste des panneaux à tourner, y aller
        if len(self.args["panos"]) > 0:
            print(f"Go to {self.args['panos'][0]}")

    def loop(self):
        while True:
            if len(self.args["panos"]) == 0:
                if self.robot.strat == Strat.Basique:
                    yield FarmingState(self.robot, self.globals, self.args)

                elif self.robot.strat == Strat.Audacieuse:
                    self.args["destination"] = self.globals['end_pos']
                    self.args['next_state'] = EndState(self.robot, self.globals, self.args)
                    yield NavState(self.robot, self.globals, self.args)

            self.args["destination"] = self.args["panos"][0]
            self.args["orientation"] = radians(90)
            self.args['next_state'] = PanoTurnState(self.robot, self.globals, self.args)
            yield NavState(self.robot, self.globals, self.args)
        
class PanoTurnState(State):
    def __init__(self, robot: Robot, globals, args={}) -> None:
        super().__init__(robot, globals, args)
    
    def enter(self, prev_state: State | None):
        print(f"tourner panneau {self.args['panos'][0]}...")
        self.prev_state = prev_state
        #self.robot.heading(radians(90)) # bras // pano
        time.sleep(1)
        if (time.time() - self.robot.aruco_time >= 1) or (abs(self.robot.aruco_y) > 100):
            if (time.time() - self.robot.aruco_time >= 1):
                print("fffflllllllaaaaaaaaagggggggggg: time")
            if (abs(self.robot.aruco_y) > 100):
                print("fffflllllllaaaaaaaaagggggggggg: too far")
            self.args['flag_bad_aruco'] = True
            return
        elif 0 + self.args["pano_angle"] < abs(self.robot.aruco_theta) < 40 + self.args["pano_angle"]:
            print("fffflllllllaaaaaaaaagggggggggg: good already")
            self.args['flag_bad_aruco'] = True
            return
        else:
            self.args['flag_bad_aruco']  = False
        #print(f"aruco cmd used: x = {self.robot.aruco_x}\t y = {self.robot.aruco_y}")
        self.robot.move_rel(self.robot.aruco_x,self.robot.aruco_y) # on se rapproche du pano
    
    def loop(self):
        while True:
            # faire tourner le panneau
            if self.args['flag_bad_aruco']:
                yield PanosState(self.robot, self.globals, self.args)
            if self.robot.hasReachedTarget():
                if not self.robot.command_sent :
                    self.robot.command_sent = True
                    self.robot.panoDo(self.robot.commande_pano)
                    self.robot.updateScore(5)
                    yield PanosState(self.robot, self.globals, self.args)

    def leave(self, next_state: State):
        # le panneau est tourné, on peut l'oublier pour passer au suivant.
        self.robot.command_sent = False
        del self.args['panos'][0]
    
class FarmingState(State):
    def __init__(self, robot: Robot, globals, args={}) -> None:
        super().__init__(robot, globals, args)
    def enter(self, prev_state: State | None):
        if len(self.args["plantes"]) > 0:
            print(f"Farming now at {self.args['plantes'][0].waypoint}")

        self.lidar_time = time.time()
        while time.time() - self.lidar_time <= LIDAR_TIME:
            yield None
        self.robot.recallageLidar(100)

    def loop(self):
        while True:
            if len(self.args["plantes"]) == 0:
                self.args['next_state'] = EndState(self.robot, self.globals, {})
                self.args['destination'] = self.globals["end_pos"]
                yield NavState(self.robot, self.globals, self.args)

            self.args["destination"] = self.args["plantes"][0].waypoint
            self.args["orientation"] = self.args["plantes"][0].azimut 
            self.args['next_state'] = PlantesState(self.robot, self.globals, self.args)

            yield NavState(self.robot, self.globals, self.args)

class PlantesState(State):
    def __init__(self, robot: Robot, globals, args={}) -> None:
        super().__init__(robot, globals, args)
    
    def enter(self, prev_state: State | None):
        print(f"Chercher plantes {self.args['plantes'][0].waypoint}...")
        self.prev_state = prev_state

    # Reminder : Plante  ['waypoint','azimut']
    # Reminder : Moissonneuse  ['pince','open','closed','orientation','ax','axUp','axDown']
    def loop(self):
        self.robot.move(100, -Moissonneuses[0].orientation)
        while not self.robot.hasReachedTarget():
                yield None
        for M in Moissonneuses:
            print("Using :", M.pince)
            self.robot.setActionneur(M.ax,M.axDown)
            self.robot.setActionneur(M.pince,M.openPince)
            # descend l'ax et ouvre la pince
            
            print("Je tourne")
            #azimut des plantes + mettre les pince en face
            self.robot.heading(M.orientation+self.args["orientation"])
            while not self.robot.hasReachedTarget():
                yield None
            print("Je suis en face")
            
            # DETECTION VL53
            time.sleep(1)
            angle = 0
            distance = 0
            self.plant = False
            for i in range(2):
                data = self.robot.vl53_data[M.pince]
                self.robot.vl53_data[M.pince] = None
                print(self.robot.vl53_data)
                if data is not None:
                    angle, distance = data
                    print(f"vl53{M.pince} detected plante at {angle}°")
                    self.plant = True
                    distance -= 10
                    break
                else:
                    # 2 rotation dans un sens s'il n'a pas vu de plantes
                    if i == 0:
                        self.robot.heading(self.robot.pos.theta - M.theta_inc)
                    elif i == 1:
                        self.robot.heading(self.robot.pos.theta + M.theta_inc)
                    while not self.robot.hasReachedTarget():
                        yield None
                    print("no plant detected")
                time.sleep(1)
            else:
                yield None
                continue
            
            # essaie de choper une plante si il en a vu une
            if self.plant :
                self.robot.heading(self.robot.pos.theta - radians(angle))
                print(f"heading {self.robot.pos.theta - radians(angle)}")
                while not self.robot.hasReachedTarget():
                    yield None
                print("ok")
                self.robot.move(distance,-M.orientation)
                while not self.robot.hasReachedTarget():
                    yield None
                self.robot.setActionneur(M.pince,M.closePince)
                print("Plante attrapée")
            else:
                print("Pas de plante pas de tournante")

            self.robot.move(-distance*(2/3), -M.orientation)
            while not self.robot.hasReachedTarget():
                yield None
            print("je reviens en place")
        for M in Moissonneuses:
            self.robot.setActionneur(M.ax,M.axUp)

        #une fois que le robot a ramassé les plantes, on peut passer dessus
        #self.robot.nav.graph.weights[(self.args["plantes"][0].waypoint, 'mid')] -= 10000
        #self.robot.nav.graph.weights[('mid', self.args["plantes"][0].waypoint)] -= 10000
        
        #petit recallage lidar des familes
        self.lidar_time = time.time()
        while time.time() - self.lidar_time <= LIDAR_TIME:
            yield None
        self.robot.recallageLidar(100)

        self.args["destination"] = self.args["jardi"][0].waypoint
        self.args["orientation"] = self.args["jardi"][0].azimut.value + Moissonneuses[0].orientation
        self.args['next_state'] = DeposeState(self.robot, self.globals, self.args)
        yield NavState(self.robot, self.globals, self.args)
       
    
    def leave(self, next_state: State):
        # les plantes sont rammasée, on peut l'oublier pour passer au suivant.
        del self.args['plantes'][0]



class DeposeState(State):
    """
    (depose_wp, azimut, theta_pince)
    """
    class Azimut(Enum):
        WEST = pi
        EAST = 0
        SOUTH = -pi/2
        NORTH = pi/2

    def __init__(self, robot: Robot, globals, args={}) -> None:
        super().__init__(robot, globals, args)

    def validate_plante(self,pince):
        data = self.robot.vl53_data[pince]
        if data is not None:
            angle, distance = data
            if distance < 50:
                self.robot.updateScore(4)
                return True
        return False
    
    def enter(self, prev_state: State | None):
        print(f" Déposer Butin {self.args['jardi'][0].waypoint}...")
        self.prev_state = prev_state
        #self.heeee = self.args['jardi'][0][1].value - self.args['jardi'][0][2]
        #self.robot.heading(self.args['jardi'][0].azimut.value - Moissonneuses[0].orientation)
        self.substate = 0
        self.start_time = 0
        self.open_time = 0
    
    def loop(self):
    #Reminder : Plante  ['waypoint','azimut']
    #Reminder : Moissonneuse  ['pince','open','closed','orientation','ax','axUp','axDown']

          
        self.robot.move(60, -Moissonneuses[0].orientation+pi/2) # decalle direction -x_table
        while not self.robot.hasReachedTarget():
            yield None   
        self.robot.move(95, -Moissonneuses[0].orientation)# avance vers le bord
        while not self.robot.hasReachedTarget():
            yield None
            
        print("prêt à lacher")
        if self.validate_plante(Moissonneuses[0].pince):
            self.robot.setActionneur(Moissonneuses[0].pince, Moissonneuses[0].openPince)# lache plante 1
            self.open_time = time.time()
            while time.time() - self.open_time <= ACT_TIME:
                yield None
            print("pinces 1 lachés")
        else:
            print("pinces 1 vide")

        if self.validate_plante(Moissonneuses[1].pince):
            self.robot.move(50, -Moissonneuses[0].orientation+pi/2) # decalle direction +x_table
            while not self.robot.hasReachedTarget():
                yield None

            self.robot.setActionneur(Moissonneuses[1].pince, Moissonneuses[1].openPince)# lache plante 2
            self.open_time = time.time()
            while time.time() - self.open_time <= ACT_TIME:
                yield None
            print("pinces 2 lachés")
        else:
            print("pinces 2 vide")

        self.robot.move(-100, -Moissonneuses[0].orientation)# recule
        while not self.robot.hasReachedTarget():
            yield None
        self.back = False
        
        # tourne l'autre face et reviens au waypoint
        print("je me tourne à ", degrees(self.args['jardi'][0].azimut.value + Moissonneuses[2].orientation))
        self.robot.goToWaypoint(self.args["destination"],self.args["jardi"][0].azimut.value + Moissonneuses[2].orientation)
        while not self.robot.hasReachedTarget():
            yield None

        # #petit recallage lidar des familles
        # self.lidar_time = time.time()
        # while self.lidar_time - time.time() < LIDAR_TIME:
        #     yield None

        # self.robot.recallageLidar(100)
        
        self.robot.heading(self.args['jardi'][0].azimut.value + Moissonneuses[2].orientation)
        while not self.robot.hasReachedTarget():
            yield None
            self.robot.move(60, -Moissonneuses[2].orientation-pi/2) # decalle direction +x_table
            while not self.robot.hasReachedTarget():
                yield None   
            self.robot.move(95, -Moissonneuses[2].orientation)# avance vers le bord
            while not self.robot.hasReachedTarget():
                yield None

        if self.validate_plante(Moissonneuses[3].pince):
            self.robot.setActionneur(Moissonneuses[3].pince, Moissonneuses[3].openPince)# lache plante 4
            self.open_time = time.time()
            while time.time() - self.open_time <= ACT_TIME:
                yield None
            print("pinces 4 lachés")
        else:
            print("pinces 4 vide")
            

        if self.validate_plante(Moissonneuses[2].pince):
            self.robot.move(50, -Moissonneuses[3].orientation-pi/2) # decalle direction -x_table
            while not self.robot.hasReachedTarget():
                yield None
            self.robot.setActionneur(Moissonneuses[2].pince, Moissonneuses[2].openPince)# lache plante 3
            self.open_time = time.time()
            while time.time() - self.open_time <= ACT_TIME:
                yield None
            print("pinces 3 lachés")
        else:
            print("pinces 3 vide")

        #recule
        self.robot.move(-100, -Moissonneuses[2].orientation)
        while not self.robot.hasReachedTarget():
            yield None
    
        print("j'ai fini")
        #self.robot.setActionneur(Actionneur.AxL,ValeurActionneur.UpAxL)
        if self.robot.strat == Strat.Basique:
            self.args["destination"] = self.globals["end_pos"]
            self.args['next_state'] = EndState(self.robot, self.globals, self.args)
        
        yield NavState(self.robot, self.globals, self.args)

# class PotState(State):
#     """TEMPORAIRE """
#     def __init__(self, robot: Robot, globals, args={}) -> None:
#         super().__init__(robot, globals, args)
    
#     def enter(self, prev_state: State | None):
#         print(f"Chercher pot {self.args['pots'][0][0]}...")
#         self.prev_state = prev_state
#         self.robot.heading(self.args['pots'][0][1])
    
#     def loop(self) -> State | None:
        
#         if timeout(self.globals["match_start_time"],self.globals["match_timeout"]):
#             return EndState(self.robot, self.globals, self.args)
        
#         # poser la plante dans le pot
#         if self.robot.hasReachedTarget():
#             self.robot.setActionneur(Actionneur.AxL,ValeurActionneur.UpAxL)
#             self.robot.move(50,self.args['pots'][0][1])
#             self.robot.setActionneur(Actionneur.Pince2,ValeurActionneur.OpenPince2)
#             if self.robot.hasReachedTarget():
#                 self.robot.setActionneur(Actionneur.Pince2,ValeurActionneur.ClosePince2)
#                 time.sleep(0.1)
#                 self.robot.setActionneur(Actionneur.AxL,ValeurActionneur.UpAxL)
#                 return PotState(self.robot, self.globals, self.args)

#     def leave(self, next_state: State):
#         # les pots sont rammassé, on peut l'oublier pour passer au suivant.
#         del self.args['pots'][0]
    
