from hardware import *
from so import *
import log
from shell import *


##
##  MAIN 
##
if __name__ == '__main__':
    log.setupLogger()
    log.logger.info('Starting emulator')

    ## setup our hardware and set memory size to 25 "cells"
    HARDWARE.setup(35)



    #scheduler choose
    sche = "P"
    if sche == "RRB":
        timer = HARDWARE.timer
        timer.quantum = 2
        scheduler = SchedulerRRB()
    if sche == "FCFS":
        scheduler = SchedulerFCFS()
    if sche == "NP":
        scheduler = SchedulerNonPreemtive()
    if sche == "P":
        scheduler = SchedulerPreemtive()


    ## Switch on computer
    HARDWARE.switchOn()

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo
    kernel = Kernel(scheduler)

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    prg1 = Program("prg1.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])
    prg2 = Program("prg2.exe", [ASM.CPU(7)])
    prg3 = Program("prg3.exe", [ASM.CPU(4), ASM.IO(), ASM.CPU(1)])

    # execute all programs "concurrently"
    kernel.run(prg1,1)
    kernel.run(prg2,3)
    kernel.run(prg3,0)
    kernel.run(prg3,2)

    shell.com(kernel)




