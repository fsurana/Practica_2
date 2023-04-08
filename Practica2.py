"""
Puente de Ambite
"""
import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value

SOUTH = 1
NORTH = 0

NCARS = 20
NPED = 10
TIME_CARS_NORTH = 0.5  # a new car enters each 0.5s
TIME_CARS_SOUTH = 0.5  # a new car enters each 0.5s
TIME_PED = 5 # a new pedestrian enters each 5s
TIME_IN_BRIDGE_CARS = (1, 0.5) # normal 1s, 0.5s
TIME_IN_BRIDGE_PEDESTRIAN = (30, 10) # normal 1s, 0.5s

class Monitor():
    def __init__(self):
        self.mutex = Lock()
        self.cars_north_waiting = Value('i', 0)
        self.cars_south_waiting = Value('i', 0)
        self.cars_north_inside = Value('i', 0)
        self.cars_south_inside = Value('i', 0)
        self.cars_south_waiting = Value('i', 0)
        self.ped_waiting = Value('i', 0)
        self.ped_inside = Value('i', 0)
        self.turn = Value('i', 0)
        #turn 0 = north cars, turn 1 = south cars, turn 2 = pedestrian
        self.sem_north_cars = Condition(self.mutex)
        self.sem_south_cars = Condition(self.mutex)
        self.sem_pedestrian = Condition(self.mutex)
        
    
    def cars_north(self):
        return self.cars_south_inside.value == 0 and self.ped_inside.value == 0 and\
            ((self.cars_south_waiting.value == 0 and self.ped_waiting.value == 0) or\
             self.turn.value == 0)

    def cars_south(self):
        return self.cars_north_inside.value == 0 and self.ped_inside.value == 0 and\
            ((self.cars_north_waiting.value == 0 and self.ped_waiting.value == 0) or\
             self.turn.value == 1)
    
    def pedestrian(self):
        return self.cars_south_inside.value == 0 and self.cars_north_inside.value == 0 and\
            ((self.cars_south_waiting.value == 0 and self.cars_north_waiting.value == 0) or\
             self.turn.value == 2)


    def wants_enter_car(self, direction: int) -> None:
        
        if direction == 0:
            self.mutex.acquire()
            self.cars_north_waiting.value += 1
            self.sem_north_cars.wait_for(self.cars_north)
            self.cars_north_waiting.value -= 1
            self.cars_north_inside.value += 1
            self.mutex.release()
        
        else:
            self.mutex.acquire()
            self.cars_south_waiting.value += 1
            self.sem_south_cars.wait_for(self.cars_south)
            self.cars_south_waiting.value -= 1
            self.cars_south_inside.value += 1
            self.mutex.release()

    def leaves_car(self, direction: int) -> None:
        
        if direction == 0:
            self.mutex.acquire()
            self.cars_north_inside.value -= 1
            
            if self.cars_south_waiting != 0:
                self.turn.value = 1
                if self.cars_north_inside.value == 0:
                    self.sem_south_cars.notify_all()
            
            elif self.ped_waiting.value != 0:
                self.turn.value = 2
                if self.cars_north_inside.value == 0:
                    self.sem_pedestrian.notify_all()
            self.mutex.release()
                
        else:
            self.mutex.acquire()
            self.cars_south_inside.value -= 1
            
            if self.ped_waiting.value != 0:
                self.turn.value = 2
                if self.cars_south_inside.value == 0:
                    self.sem_pedestrian.notify_all()
            
            elif self.cars_north_waiting.value != 0:
                self.turn.value = 0
                if self.cars_south_inside.value == 0:
                    self.sem_north_cars.notify_all()
            
            self.mutex.release()
        
    def wants_enter_pedestrian(self) -> None:
        self.mutex.acquire()
        self.ped_waiting.value += 1
        self.sem_pedestrian.wait_for(self.pedestrian)
        self.ped_waiting.value -= 1
        self.ped_inside.value += 1
        self.mutex.release()

    def leaves_pedestrian(self) -> None:
        self.mutex.acquire()
        self.ped_inside.value -= 1
        
        if self.cars_north_waiting.value != 0:
            self.turn.value = 0
            if self.ped_inside.value == 0:
                self.sem_north_cars.notify_all()
        
        elif self.cars_south_waiting.value != 0:
            self.turn.value = 1
            if self.ped_inside.value == 0:
                self.sem_south_cars.notify_all()
            
        self.mutex.release()

    def __repr__(self) -> str:
        return f"Monitor: CN({self.cars_north_inside.value}), CNE({self.cars_north_waiting.value}), CS({self.cars_south_inside.value}), CSE({self.cars_south_waiting.value}), P({self.ped_inside.value}), PE({self.ped_waiting.value})"

def delay_car_north() -> None:
    time.sleep(0.6)
    pass

def delay_car_south() -> None:
    time.sleep(0.6)
    pass

def delay_pedestrian() -> None:
    time.sleep(1)
    pass

def car(cid: int, direction: int, monitor: Monitor)  -> None:
    print(f"car {cid} heading {direction} wants to enter. {monitor}")
    monitor.wants_enter_car(direction)
    print(f"car {cid} heading {direction} enters the bridge. {monitor}")
    if direction==NORTH :
        delay_car_north()
    else:
        delay_car_south()
    print(f"car {cid} heading {direction} leaving the bridge. {monitor}")
    monitor.leaves_car(direction)
    print(f"car {cid} heading {direction} out of the bridge. {monitor}")

def pedestrian(pid: int, monitor: Monitor) -> None:
    print(f"pedestrian {pid} wants to enter. {monitor}")
    monitor.wants_enter_pedestrian()
    print(f"pedestrian {pid} enters the bridge. {monitor}")
    delay_pedestrian()
    print(f"pedestrian {pid} leaving the bridge. {monitor}")
    monitor.leaves_pedestrian()
    print(f"pedestrian {pid} out of the bridge. {monitor}")



def gen_pedestrian(monitor: Monitor) -> None:
    pid = 0
    plst = []
    for _ in range(NPED):
        pid += 1
        p = Process(target=pedestrian, args=(pid, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_PED))

    for p in plst:
        p.join()

def gen_cars(direction: int, time_cars, monitor: Monitor) -> None:
    cid = 0
    plst = []
    for _ in range(NCARS):
        cid += 1
        p = Process(target=car, args=(cid, direction, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/time_cars))

    for p in plst:
        p.join()

def main():
    monitor = Monitor()
    gcars_north = Process(target=gen_cars, args=(NORTH, TIME_CARS_NORTH, monitor))
    gcars_south = Process(target=gen_cars, args=(SOUTH, TIME_CARS_SOUTH, monitor))
    gped = Process(target=gen_pedestrian, args=(monitor,))
    gcars_north.start()
    gcars_south.start()
    gped.start()
    gcars_north.join()
    gcars_south.join()
    gped.join()


if __name__ == '__main__':
    main()
