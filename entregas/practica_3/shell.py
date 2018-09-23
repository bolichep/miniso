from hardware import *
import log
from so import *

class shell():

    def com(kernel):
        #log.logger.setLevel(60) # apago el log
        #HARDWARE.switchOff()
        _consolaCorriendo = True
        while (_consolaCorriendo):
            print("& ", end="")
            try:
                comandos = input().split()
                if comandos[0] == 'nolog':
                    log.logger.setLevel(60)

                if comandos[0] == 'log' and len(comandos) == 2:
                    log.logger.setLevel(int(comandos[1]))
                else:
                    log.logger.setLevel(0)

                if comandos[0] == 'start':
                    HARDWARE.switchOn()

                if comandos[0] == 'halt' or comandos[0] == 'stop':
                    HARDWARE.switchOff()

                if comandos[0] == 'quit':
                    HARDWARE.switchOff()
                    _consolaCorriendo = False

                if comandos[0] == 'state':
                    print(HARDWARE.cpu, HARDWARE.mmu)

                if comandos[0] == 'memory':
                    print(HARDWARE.memory)

                if comandos[0] == 'pcbtable':
                    if kernel.pcbTable.runningPCB != None:
                        print("runningPCB: ", kernel.pcbTable.runningPCB,
                                end="")
                    print(kernel.pcbTable)

                if comandos[0] == 'tick':
                    comandos.pop(0)
                    count = 1
                    if comandos:
                        count = int(comandos[0])
                    while count:
                        HARDWARE.cpu.tick(1)
                        count -= 1

            except KeyboardInterrupt:
                print("\nTo exit, type: quit<Enter>")
                pass
