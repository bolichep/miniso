from hardware import *
import log
import so

class shell():

    def com(kernel):
        log.logger.setLevel(60) # apago el log
        _consolaCorriendo = True
        while (_consolaCorriendo):
            print("& ", end="")
            comandos = input().split()
            if comandos[0] == 'nolog':
                log.logger.setLevel(60)
            if comandos[0] == 'log':
                log.logger.setLevel(0)
            if comandos[0] == 'start':
                HARDWARE.switchOn()
            if comandos[0] == 'halt':
                HARDWARE.switchOff()
            if comandos[0] == 'quit':
                HARDWARE.switchOff()
                _consolaCorriendo = False
            if comandos[0] == 'memory':
                print(HARDWARE)
            if comandos[0] == 'pcb':
                if comandos[1] == 'path':
                    print('pcb: {}'.format(kernel.pcbTable.runningPCB.path))
