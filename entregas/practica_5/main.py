from hardware import *
from so import *
import log
from shell import *
from time import sleep
import sys


##
##  MAIN 
##
if __name__ == '__main__':
    log.setupLogger()
    log.logger.info('Starting emulator')

    ## setup our hardware and set memory size to 32 "cells"
    HARDWARE.setup(32)

    SCHEDULER_FCFS = 'FCFS'
    SCHEDULER_RR = 'RR'
    SCHEDULER_NP = 'NP'
    SCHEDULER_P = 'P'

    #scheduler choose
    sche = SCHEDULER_FCFS #<<<<<<< choose here or at cli

    if len(sys.argv) > 1:
        sche = sys.argv[1]

    if sche == SCHEDULER_RR:
        timer = HARDWARE.timer
        timer.quantum = 2
        scheduler = SchedulerRRB()
    if sche == SCHEDULER_FCFS:
        scheduler = SchedulerFCFS()
    if sche == SCHEDULER_NP:
        scheduler = SchedulerNonPreemtive()
    if sche == SCHEDULER_P:
        scheduler = SchedulerPreemtive()

    print("Runnnig", scheduler.name)


    ## Switch on computer
    HARDWARE.switchOn()

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo
    kernel = Kernel(scheduler, frameSize = 4)
    # sleep(1)

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    prg1 = Program([ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])   
    prg2 = Program([ASM.CPU(7)])
    prg3 = Program([ASM.CPU(4), ASM.IO(), ASM.CPU(1)]) 

    kernel.fileSystem.write("prg1.exe", prg1)
    kernel.fileSystem.write("prg2.exe", prg2)
    kernel.fileSystem.write("prg3.exe", prg3)
    # execute all programs "concurrently"
    kernel.run("prg1.exe",1)
    kernel.run("prg2.exe",0)
    kernel.run("prg3.exe",0)
    #kernel.run("prg3.exe",2)
    sleep(32)
    kernel.run("prg1.exe",1)
    kernel.run("prg2.exe",0)
    kernel.run("prg3.exe",0)

    shell.com(kernel)
