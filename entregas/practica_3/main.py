from hardware import *
from so import *
import log


##
##  MAIN 
##
if __name__ == '__main__':
    log.setupLogger()
    log.logger.info('Starting emulator')

    ## setup our hardware and set memory size to n "cells"
    HARDWARE.setup(13)

    ## Switch on computer
    HARDWARE.switchOn()

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo
    kernel = Kernel()

    ##  create a program
    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ###################
    prg1 = Program("prg1.exe", [ASM.CPU(1), ASM.IO(), ASM.CPU(1), ASM.IO(), ASM.CPU(1)])
    prg2 = Program("prg2.exe", [ASM.CPU(1), ASM.IO(), ASM.CPU(1)])
    prg3 = Program("prg3.exe", [ASM.CPU(2)])

    # execute all programs "concurrently"
    kernel.run(prg1)
    kernel.run(prg2)
    kernel.run(prg3)

