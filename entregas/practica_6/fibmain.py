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
    HARDWARE.timeUnit = 0.01

    SCHEDULER_FCFS = 'FCFS'
    SCHEDULER_RR = 'RR'
    SCHEDULER_NP = 'NP'
    SCHEDULER_P = 'P'

    #scheduler choose
    sche = SCHEDULER_P #<<<<<<< choose here or at cli

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
    ## Switch OFF to test
    HARDWARE.switchOff()

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo
    kernel = Kernel(HARDWARE,scheduler, frameSize = 4)
    # sleep(1)

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    prg1 = Program([ASM.CPU(1), ASM.IO(), ASM.CPU(1)])
    prg2 = Program([ASM.INCA(1), ASM.IO()])
    prg3 = Program([ASM.CPU(4), ASM.IO(), ASM.CPU(1)])

    # CALL RET Stack TEST
    calltest = Program([
        ASM.HEADER(4),
        ASM.JMP(9),
        ASM.INCA(1),
        ASM.DECB(1),
        ASM.RET(),
        ASM.CALL(6),
        ASM.CALL(6),
        ASM.CALL(6)
        ])
    """
    fib 0 = 0
    fib 1 = 1
    fib n = fib (n-1) + fib (n-2)
    { 0,1,1,2,3,5,8,13,21,34,55,89,144,}
    """


    def fibo(x):
        return Program([
            ASM.HEADER(16),
            ASM.STORA(x),      # fib(10) 2200 tick +/-
            ASM.CALL('FIB'),
            ASM.EXIT(1),
            ASM.LABEL('FIB'),    # fib(n), A = n
            ASM.STORB('0'),
            ASM.CMPAB(),
            ASM.JZ('RETORNO'),   # B = fib(n)
            ASM.STORB('1'),
            ASM.CMPAB(),
            ASM.JZ('RETORNO'),   # B = fib(n)
            ASM.DECA(1),         # n-1
            ASM.PUSHA(),
            ASM.CALL('FIB'),     # fib(n-1)
            ASM.POPA(),
            ASM.PUSHB(),         # save B = fib(n-1)
            ASM.DECA(1),         # n-2
            ASM.CALL('FIB'),     # B = fib(n-2)
            ASM.POPA(),          # A = saved B = fib(n-1)
            ASM.ADDAB(),         # A = fib(n-1) + fib(n-2)
            ASM.PUSHA(),
            ASM.POPB(),          # B = fib(n-1) + fib(n-2)
            ASM.LABEL('RETORNO'),
            ASM.RET()
            ])

    fib = fibo(6)

    kernel.fileSystem.write("/bin/exit", Program([
        ASM.HEADER(4),
        ASM.STORB('49'),
        ASM.STORA('100'),
        ASM.JMP('O'),

        ASM.LABEL('A'),
        ASM.PUSHB(),
        ASM.PUSHA(),
        ASM.PUSHA(),
        ASM.POPA(),
        ASM.POPB(),
        ASM.POPA(),
        ASM.RET(),

        ASM.LABEL('O'),
        ASM.CALL('A'),
        ASM.DECB(2)

        ]))

    #kernel.fileSystem.write("/bin/calltest", calltest)
    kernel.fileSystem.write("/prg1", prg1)
    kernel.fileSystem.write("/prg2", prg2)
    kernel.fileSystem.write("/prg3", prg3)
    # execute all programs "concurrently"
    #kernel.run("/bin/calltest", 1)
    #kernel.run("/prg1",0)
    #kernel.run("/prg2",0)
    #kernel.run("/prg3",2)
    #sleep(32 * HARDWARE.timeUnit)
    #kernel.run("/prg1",1)
    #kernel.run("/prg2",0)
    #kernel.run("/prg3",0)

    #kernel.run("/bin/exit", 4)
    #kernel.run("/bin/calltest", 1)
    kernel.fileSystem.write("/fib1", fibo(6))
    kernel.fileSystem.write("/fib2", fibo(7))
    kernel.fileSystem.write("/fib3", fibo(4))
    kernel.run("/fib1", 3)
    kernel.run("/fib2", 3)
    kernel.run("/fib3", 3)

    shell.com(kernel)
