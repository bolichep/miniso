from hardware import *
import log
from so import *
import sys
import readline


class shell:
    help_c = """
    start          : enciende el hardware
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
    """

    def com(kernel):
        ct = Thread(target = shell._com, kwargs = dict(kernel = kernel))
        ct.start()
        ct.join()

    def _eval(args, kernel):
        try:
            print(eval(args[0]))
        except NameError as ne:
            print('NameError: {}'.format(ne))
        except TypeError as te:
            print('TypeError: {}'.format(te))

    def _ls(args, kernel):
        for f  in kernel.fileSystem.root:
            print("{:<8} {}".format(f, kernel.fileSystem.root.get(f)))

    def _run(args, kernel):
        kernel.run(args[0], 3 if len(args) < 2 else int(args[1]))

    def _ticktime(args, kernel):
        HARDWARE.timeUnit = float(args[0])

    def __tick(count):
        nbrTick = 0
        while count != nbrTick:
            nbrTick += 1
            HARDWARE.clock.tick(nbrTick)

    def _tick(args, kernel):
        times = int(args[0])
        thread_shell_tick = Thread(target = shell.__tick, kwargs = dict(count=times))
        thread_shell_tick.start()
        #thread_shell_tick.join()

    def _help(args, kernel):
        print(shell.help_c)

    def _start(args, kernel):
        HARDWARE.switchOn()

    def _stop(args, kernel):
        HARDWARE.switchOff()

    def _quit(args, kernel):
        HARDWARE.switchOff()
        #_consolaCorriendo = False
        return True

    def _reset(args, kernel):
        print(HARDWARE.setup(args[0]))

    def _state(args, kernel):
        print(HARDWARE.cpu, HARDWARE.mmu)

    def _iodevice(args, kernel):
        print(kernel.ioDeviceController)

    def _readyqueue(args, kernel):
        print(kernel.scheduler)

    def _memory(args, kernel):
        print(HARDWARE.memory)

    def _pcbtable(args, kernel):
        if kernel.pcbTable.runningPCB != None:
            print("runningPCB:\n    ", kernel.pcbTable.runningPCB,
                                end="")
        print(kernel.pcbTable)

    def _default(args, kernel):
        if kernel.fileSystem.read(args[0]) != None:
            kernel.run(args[0], 
                    3 if len(args) < 2 
                    else int(args[1]))

    def _nothing(args, kernel):
        pass
            
    commands = dict(
            eval       = _eval,
            ls         = _ls,
            run        = _run,
            ticktime   = _ticktime,
            help       = _help,
            start      = _start,
            stop       = _stop,
            reset      = _reset,
            state      = _state,
            iodevice   = _iodevice,
            readyqueue = _readyqueue,
            memory     = _memory,
            pcbtable   = _pcbtable,
            tick       = _tick,
            quit       = _quit)
    commands.update({'':_nothing})

    def _com(kernel):
        _consolaCorriendo = True
        _code = []
        _name = []
        while (_consolaCorriendo):
            try:
                script = []
                while not script:
                    script = input("& ").split(';')

                while script:
                    line = script[0].split()
                    script.pop(0)
                    #print("line =", line, shell.commands)
                    #print(len(line))
                    if line: # and line[0] in shell.commands:
                        if not line[0] in shell.commands:
                            line = ['run'] + line
                        cmd , args = line[0], line[1:] if len(line) > 1 else []
                        #print("exec:", cmd, args)
                        _consolaCorriendo = not shell.commands[cmd](args, kernel)


            except KeyboardInterrupt:
                print("\nTo exit, type: quit<Enter>\nor help to see commands")
                pass
            except (IndexError, AttributeError):
                print("IndexError or AttributeError at {}".format(sys.exc_info()[-1].tb_lineno))
                pass


