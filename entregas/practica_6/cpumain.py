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

    """
    ALERTA
    """
    ## Con RAM32/FS(4,8,16) se dispara un bug:
    ## Exception: Invalid Address,  11 is higher than process limit: 10 
    ## la Address cambia pero siempre es uno mas del limite
    ## PERO!!!! con frameSize 2 no falla
    ## setup our hardware and set memory size to 8 "cells"
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
    kernel = Kernel(HARDWARE,scheduler, frameSize = 2)
    # sleep(1)

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    prg1 = Program([
        ASM.STORA(2),
        ASM.LABEL('START'),
        ASM.CPU(8),
        ASM.IO(),
        ASM.CPU(8),
        ASM.IO(),
        ASM.DECA(1),
        ASM.JNZ('START'),
        ASM.CPU(2),
        ASM.EXIT(1)])  # A = 0 

    prg2 = Program([
        ASM.STORA(0), #0
        ASM.STORB(5), #1
        ASM.LABEL('START'), #2
        ASM.INCA(1), #2
        ASM.CMPAB(), #3
        ASM.JNZ('START'),
        ASM.EXIT(1)])  # A = 0 

    prg3 = Program([
        ASM.CPU(4),
        ASM.STORA(42),
        ASM.STORB(17),
        ASM.IO(),
        ASM.CPU(1),
        ASM.EXIT(1)]) 

    prg4 = Program([ASM.CPU(7)])

    kernel.fileSystem.write("/bin/prg1", prg1)
    kernel.fileSystem.write("/bin/prg2", prg2)
    kernel.fileSystem.write("/bin/prg3", prg3)
    kernel.fileSystem.write("/bin/prg4", prg4)
    # execute all programs "concurrently"
    kernel.run("/bin/prg1",1)
    kernel.run("/bin/prg2",3)
    kernel.run("/bin/prg3",2)
    kernel.run("/bin/prg1",1)
    kernel.run("/bin/prg2",4)
    kernel.run("/bin/prg3",0)
    kernel.run("/bin/prg1",1)
    kernel.run("/bin/prg2",1)
    kernel.run("/bin/prg3",0)
    kernel.run("/bin/prg1",1)
    kernel.run("/bin/prg2",2)
    kernel.run("/bin/prg3",0)
    kernel.run("/bin/prg1",1) 

    shell.com(kernel)
