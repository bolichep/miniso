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
    kernel = Kernel(HARDWARE,scheduler, frameSize = 8)
    # sleep(1)

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    """
    prg1 = Program([
        ASM.HEADER(10),
        ASM.CPU(1), #0
        ASM.CPU(1), #1
        ASM.CPU(1), #2
        ASM.AI1(1), #3
        ASM.PUSHA(), #4
        ASM.PUSHA(), #4
        ASM.AI1(1), #5
        ASM.JZ(4),  #16
        ASM.CPU(1), #8
        ASM.JMP(17),
        ASM.CPU(2)  #9 ,10
        ])
    """
    prg1 = Program([
        ASM.HEADER(4),
        ASM.AI1(4),
        ASM.BI1(1),
        ASM.AD1(1),
        ASM.JZ(2),
        ASM.JMP(8),
        ASM.EXIT(1)
        ])
    kernel.fileSystem.write("asmcode", prg1)
    kernel.run("asmcode",1)
    kernel.run("asmcode",1)

    shell.com(kernel)
