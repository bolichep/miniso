from hardware import *
import log
from so import *
import sys
import readline


class shell():
    help_c = """
    nolog          : suprime la salida de log.logger
    log            : habilita la salida de log.logger
    start          : enciende el hardware
    halt           : detiene el hardware
    stop           : detiene el hardware
    quit           : sale del shell
    state          : muestra el estado del CPU y la MMU
    iodevice       : muestra el estado del iodevice y su cola (waiting)
    readyqueue     : muestra los PCB en el readyQueue
    memory         : muestra el contenido de la memoria
    pcbtable       : muestra el contenido de la tabla de PCB
    ticktime n     : establece el tiempo en segundos de cada tick
    tick [n]       : envia n (o 1 por omision) tick de clock a los dispositivos subscriptos
    ls             : lista los programas salvados
    save name code : salva el codigo en 'code' bajo el nombre 'name'
                     ej: save uno CPU,IO,CPU,EXIT
    load name      : carga el codigo bajo el nombre 'name' para ser usado en run
    run            : corre el codigo previamente cargado con load
    """


    def _tick(count):
        nbrTick = 0
        while count != nbrTick:
            nbrTick += 1
            HARDWARE.clock.tick(nbrTick)

    def com(kernel):
        ct = Thread(target = shell._com, kwargs = dict(kernel = kernel))
        ct.start()

    def _com(kernel):
        _consolaCorriendo = True
        _code = []
        _name = []
        while (_consolaCorriendo):
            try:
                comandos = []
                while not comandos:
                    comandos = input("& ").split()

                while comandos:
                    if comandos[0] == 'eval':
                        try:
                            print(eval(comandos[1]))
                        except NameError as ne:
                            print('NameError: {}'.format(ne))
                        except TypeError as te:
                            print('TypeError: {}'.format(te))


                    if comandos[0] == 'ls':
                        for f  in kernel.fileSystem.root:
                            print("{:<8} {}".format(f, kernel.fileSystem.root.get(f)))

                    if comandos[0] == 'save':
                        kernel.fileSystem.write(comandos[1], 
                                Program([comandos[2].split(",")]) )
                        #shell.fs.update({comandos[1]: comandos[2]})

                    if comandos[0] == 'load':
                        _code = shell.fs.get(comandos[1])
                        _name = comandos[1]
                        print(_code)

                    if comandos[0] == 'run':
                        #kernel.fileSystem.write(_name, Program([_code.split(",")]) )
                        kernel.run(comandos[1], 3 if len(comandos) < 2 else int(comandos[2]))

                    if comandos[0] == 'ticktime':
                        HARDWARE.timeUnit = float(comandos[1])

                    if comandos[0] == 'loaderreset':
                        kernel.loader.memoryPos = 0

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

                    if comandos[0] == 'reset':
                        print(HARDWARE.setup(35))

                    if comandos[0] == 'state':
                        print(HARDWARE.cpu, HARDWARE.mmu)

                    if comandos[0] == 'iodevice':
                        print(kernel.ioDeviceController)

                    if comandos[0] == 'readyqueue':
                        print(kernel.scheduler)

                    if comandos[0] == 'memory':
                        print(HARDWARE.memory)

                    if comandos[0] == 'pcbtable':
                        if kernel.pcbTable.runningPCB != None:
                            print("runningPCB: ", kernel.pcbTable.runningPCB,
                                    end="")
                        print(kernel.pcbTable)

                    if comandos[0] == 'tick':
                        comandos.pop(0)
                        times = int(comandos[0])
                        thread_shell_tick = Thread(target = shell._tick, kwargs = dict(count=times))
                        thread_shell_tick.start()

                    if kernel.fileSystem.read(comandos[0]) != None:
                        kernel.run(comandos[0], 
                                3 if len(comandos) < 2 
                                else int(comandos[1]))

                    # done current command, see if we got next
                    while comandos and comandos[0] is not ';':
                        comandos.pop(0)
                    # if first is ; remove it
                    if comandos and comandos[0] is ';':
                        comandos.pop(0)


            except KeyboardInterrupt:
                print("\nTo exit, type: quit<Enter>\nor help to see commands")
                pass
            except (IndexError, AttributeError):
                print("IndexError or AttributeError at {}".format(sys.exc_info()[-1].tb_lineno))
                pass
