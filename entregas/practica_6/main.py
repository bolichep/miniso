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
    HARDWARE.setup(2)
    HARDWARE.timeUnit = 0.2

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
    kernel = Kernel(HARDWARE,scheduler, frameSize = 2)
    # sleep(1)

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    prg1 = Program([ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])   
    prg2 = Program([ASM.INCA(57), ASM.CPU(4)])
    prg3 = Program([ASM.CPU(45), ASM.IO(), ASM.CPU(1)]) 

    # CALL RET Stack TEST
    stacktest = Program([
        ASM.HEADER(4),
        ASM.STORA(15),
        ASM.LABEL('DEC'),
        ASM.PUSHA(),
        ASM.POPA(),
        ASM.DECA(1),
        ASM.JNZ('DEC')
        ])
    kernel.fileSystem.write("/stacktest", stacktest)


    kernel.fileSystem.write("/prg1", prg1)
    kernel.fileSystem.write("/prg2", prg2)
    kernel.fileSystem.write("/prg3", prg3)
    # execute all programs "concurrently"
    #kernel.run("/prg1",1)
    #kernel.run("/prg2",0)
    #kernel.run("/prg3",0)
    #kernel.run("/prg3",2)
    sleep(2 * HARDWARE.timeUnit)
    #kernel.run("/prg1",1)
    #kernel.run("/prg2",0)
    #kernel.run("/prg3",0)
    kernel.run("/stacktest",1)

    HARDWARE.switchOff()
    shell.com(kernel)
