from hardware import *
import log
from so import *

class shell():
    help_c = """
    nolog      : suprime la salidad de log.logger
    log        : habilita la salida de log.logger
    start      : enciende el hardware
    halt       : detiene el hardware
    stop       : detiene el hardware
    quit       : sale del shell
    state      : muestra el estado del CPU y la MMU
    iodevice   : muestra el estado del iodevice y su cola
    readyqueue : muestra los PCB en el readyQueue
    memory     : muestra el contenido de la memoria
    pcbtable   : muestra el contenido de la tabla de PCB
    tick [n]   : envia n (o 1 por omision) tick de clock a los dispositivos subscriptos
    """

    def com(kernel):
        #log.logger.setLevel(60) # apago el log
        #HARDWARE.switchOff()
        _consolaCorriendo = True
        while (_consolaCorriendo):
            try:
                comandos = []
                while not comandos:
                    print("& ", end="")
                    comandos = input().split()

                if comandos[0] == 'help':
                    print(shell.help_c)

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

                if comandos[0] == 'iodevice':
                    print(kernel.ioDeviceController)

                if comandos[0] == 'readyqueue':
                    print(kernel.readyQueue)

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
                        HARDWARE.clock.tick(1)
                        count -= 1

            except KeyboardInterrupt:
                print("\nTo exit, type: quit<Enter>\nor help to see commands")
                pass
