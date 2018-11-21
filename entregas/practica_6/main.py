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
    HARDWARE.timeUnit = 0.5

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
    kernel = Kernel(HARDWARE,scheduler, frameSize = 4)
    # sleep(1)

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    prg1 = Program([ASM.CPU(4), ASM.IO(), ASM.CPU(4)])   
    prg2 = Program([ASM.AI1(4), ASM.CPU(4), ASM.IO(), ASM.CPU(3)])
    prg3 = Program([ASM.CPU(4), ASM.IO(), ASM.CPU(1)]) 

    # CALL RET Stack TEST
    calltest = Program([
        ASM.HEADER(4),
        ASM.JMP(9),
        ASM.AI1(1),
        ASM.BD1(1),
        ASM.RET(),
        ASM.CALL(6),
        ASM.CALL(6),
        ASM.CALL(6)
        ])
    kernel.fileSystem.write("/bin/calltest", calltest)


    kernel.fileSystem.write("/prg1", prg1)
    kernel.fileSystem.write("/prg2", prg2)
    kernel.fileSystem.write("/prg3", prg3)
    # execute all programs "concurrently"
    kernel.run("/prg1",1)
    kernel.run("/prg2",0)
    kernel.run("/prg3",0)
    kernel.run("/prg3",2)
    sleep(32 * HARDWARE.timeUnit)
    kernel.run("/prg1",1)
    kernel.run("/prg2",0)
    kernel.run("/prg3",0)

    shell.com(kernel)
