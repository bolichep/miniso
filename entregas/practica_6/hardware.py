#!/usr/bin/env python

from tabulate import tabulate
from time import sleep
from threading import Thread, Lock
import log

##  Estas son la instrucciones soportadas por nuestro CPU
INSTRUCTION_IO = 'IO'
INSTRUCTION_CPU = 'CPU'
INSTRUCTION_AI1 = 'AI1'
INSTRUCTION_AD1 = 'AD1'
INSTRUCTION_BI1 = 'BI1'
INSTRUCTION_BD1 = 'BD1'
INSTRUCTION_CAB = 'CAB'
INSTRUCTION_JZ = 'JZ'
INSTRUCTION_JMP = 'JMP'
INSTRUCTION_CALL = 'CALL'
INSTRUCTION_RET = 'RET'
INSTRUCTION_POPA = 'POPA'
INSTRUCTION_PUSHA = 'PUSHA'
INSTRUCTION_POPB = 'POPB'
INSTRUCTION_PUSHB = 'PUSHB'
INSTRUCTION_EXIT = 'EXIT'
INSTRUCTION_PAGEFAULT = 'PAGE_FAULT'


## Helper for emulated machine code
class ASM():

    @classmethod
    def HEADER(self, space):
        return [INSTRUCTION_JMP, str(space)] + ['0']* (space-2) 

    @classmethod
    def AD1(self, times):
        return [INSTRUCTION_AD1] * times

    @classmethod
    def AI1(self, times):
        return [INSTRUCTION_AI1] * times

    @classmethod
    def BI1(self, times):
        return [INSTRUCTION_BI1] * times

    @classmethod
    def BD1(self, times):
        return [INSTRUCTION_BD1] * times

    @classmethod
    def CAB(self, times):
        return [INSTRUCTION_CAB] * times

    @classmethod
    def JMP(self, direccion):
        return [INSTRUCTION_JMP, str(direccion)]

    @classmethod
    def CALL(self, direccion):
        return [INSTRUCTION_CALL, str(direccion)]

    @classmethod
    def RET(self):
        return [INSTRUCTION_RET]

    @classmethod
    def PUSHA(self):
        return [INSTRUCTION_PUSHA]

    @classmethod
    def POPA(self):
        return [INSTRUCTION_POPA]

    @classmethod
    def JZ(self, direccion):
        return [INSTRUCTION_JZ, str(direccion)]

    @classmethod
    def EXIT(self, times):
        return [INSTRUCTION_EXIT] * times

    @classmethod
    def IO(self):
        return INSTRUCTION_IO

    @classmethod
    def CPU(self, times):
        return [INSTRUCTION_CPU] * times

    @classmethod
    def isEXIT(self, instruction):
        return INSTRUCTION_EXIT == instruction

    @classmethod
    def isIO(self, instruction):
        return INSTRUCTION_IO == instruction

    @classmethod
    def isPAGEFAULT(self, instruction):
        return INSTRUCTION_PAGEFAULT == instruction



##  Estas son la interrupciones soportadas por nuestro Kernel
KILL_INTERRUPTION_TYPE = "#KILL"
IO_IN_INTERRUPTION_TYPE = "#IO_IN"
IO_OUT_INTERRUPTION_TYPE = "#IO_OUT"
NEW_INTERRUPTION_TYPE = "#NEW"
TIMEOUT_INTERRUPTION_TYPE = "#TIMEOUT"
PAGE_FAULT_INTERRUPTION_TYPE = "#PAGE_FAULT"

## emulates an Interrupt request
class IRQ:

    def __init__(self, type, parameters = None):
        self._type = type
        self._parameters = parameters

    @property
    def parameters(self):
        return self._parameters

    @property
    def type(self):
        return self._type



## emulates the Interrupt Vector Table
class InterruptVector():

    def __init__(self):
        self._handlers = dict()
        self.lock = Lock()

    def register(self, interruptionType, interruptionHandler):
        self._handlers[interruptionType] = interruptionHandler

    def handle(self, irq):
        log.logger.info("Handling {type} irq with parameters = {parameters}".format(type=irq.type, parameters=irq.parameters ))
        self.lock.acquire()
        self._handlers[irq.type].execute(irq)
        self.lock.release()





## emulates the Internal Clock
class Clock():

    def __init__(self):
        self._subscribers = []
        self._running = False
        self._timeUnit = 1

    @property
    def tickUnitInSec(self):
        return self._timeUnit

    @tickUnitInSec.setter
    def tickUnitInSec(self, value):
        self._timeUnit = value

    def addSubscriber(self, subscriber):
        self._subscribers.append(subscriber)

    def stop(self):
        self._running = False

    def start(self):
        log.logger.info("---- :::: START CLOCK  ::: -----")
        self._running = True
        t = Thread(target=self.__start)
        t.start()

    def __start(self):
        tickNbr = 0
        while (self._running):
            self.tick(tickNbr)
            tickNbr += 1

    def tick(self, tickNbr):
        log.logger.info("        --------------- tick: {tickNbr} ---------------".format(tickNbr = tickNbr))
        ## notify all subscriber that a new clock cycle has started
        for subscriber in self._subscribers:
            subscriber.tick(tickNbr)
        ## wait 1 second and keep looping
        sleep(self._timeUnit)

    def do_ticks(self, times):
        log.logger.info("---- :::: CLOCK do_ticks: {times} ::: -----".format(times=times))
        for tickNbr in range(0, times):
            self.tick(tickNbr)



## emulates the main memory (RAM)
class Memory():

    def __init__(self, size):
        self._size = size
        self._cells = [''] * size

    def put(self, addr, value):
        self._cells[addr] = value

    def get(self, addr):
        return self._cells[addr]

    def __repr__(self):
        return tabulate(enumerate(self._cells), tablefmt='psql')

    def getLeng(self) :
        return  self._size
        ## return "Memoria = {mem}".format(mem=self._cells)

## emulates the Memory Management Unit (MMU)
class MMU():

    def __init__(self, memory):
        self._memory = memory
        self._frameSize = 0
        self._limit = 999
        self._tlb = dict()

    @property
    def limit(self):
        return self._limit

    @limit.setter
    def limit(self, limit):
        self._limit = limit

    @property
    def frameSize(self):
        return self._frameSize

    @frameSize.setter
    def frameSize(self, frameSize):
        self._frameSize = frameSize

    def resetTLB(self):
        self._tlb = dict()

    def setPageFrame(self, pageId, frameId):
        self._tlb[pageId] = frameId

    def logicalToPhysicalAddress(self, logicalAddress):
        if (logicalAddress > self._limit):
            raise Exception("Invalid Address,  {logicalAddress} is higher than process limit: {limit}".format(limit = self._limit, logicalAddress = logicalAddress))

        # calculamos la pagina y el offset correspondiente a la direccion logica recibida
        pageId = logicalAddress // self._frameSize
        offset = logicalAddress % self._frameSize

        # buscamos la direccion Base del frame donde esta almacenada la pagina
        try:
            frameId = self._tlb[pageId]
        except:
            raise Exception("\n*\n* ERROR \n*\n Error en el MMU\nNo se cargo la pagina  {pageId}".format(pageId = str(pageId)))

        ##calculamos la direccion fisica resultante
        frameBaseDir  = self._frameSize * frameId
        physicalAddress = frameBaseDir + offset

        return physicalAddress

    def write(self, logicalAddress, value):
        self._memory.put(self.logicalToPhysicalAddress(logicalAddress), value)

    def fetch(self,  logicalAddress):
        # obtenemos la instrucción alocada en esa direccion
        return self._memory.get(self.logicalToPhysicalAddress(logicalAddress))


## emulates the main Central Processor Unit
class Cpu():

    def __init__(self, mmu, interruptVector):
        self._mmu = mmu
        self._interruptVector = interruptVector
        self._pc = -1
        self._ir = None
        self._ac = 0
        self._bc = 0
        self._zf = True
        self._sp = -1

    def tick(self, tickNbr):
        if (self._pc > -1):
            self._fetch()
            self._decode()
            self._execute()
        else:
            log.logger.info("cpu - NOOP")


    def _fetch(self):
        self._ir = self._mmu.fetch(self._pc)
        self._pc += 1

    def _decode(self):
        if self._ir == 'IO':
            #print("IO Instruction")
            pass

        if self._ir == 'EXIT':
            #print("\x9B7m", end="")
            #print("A Reg : ", self._ac, "/ B Reg : ", self._bc,"/ z flag: ", self._zf)
            #print("\x9B0m", end="")
            pass

        if self._ir == 'PAGE_FAULT'
            pass

        if self._ir == 'CALL':
            self._fetch()
            self._sp += 1
            self._mmu.write(self._sp, self._pc)
            self._pc = int(self._ir)
            #print("CALL instruction")

        if self._ir == 'RET':
            self._pc = self._mmu.fetch(self._sp)
            self._sp -= 1
            #print("RET Instruction")

        if self._ir == 'PUSHA':
            self._sp += 1
            self._mmu.write(self._sp, self._ac)
            #print("PUSHA instruction")

        if self._ir == 'POPA':
            self._ac = self._mmu.fetch(self._sp)
            self._sp -= 1
            #print("POPA instruction")

        if self._ir == 'PUSHB':
            self._sp += 1
            self._mmu.write(self._sp, self._bc)
            #print("PUSHB instruction")

        if self._ir == 'POPB':
            self._bc = self._mmu.fetch(self._sp)
            self._sp -= 1
            #print("POPB instruction")

        if self._ir == 'CPU':
            #print("CPU Instruction")
            pass

        if self._ir == 'AD1':
            self._ac -= 1
            self._zf = (self._ac == 0) 
            #print("AD1 Instruction")

        if self._ir == 'AI1':
            self._ac += 1
            self._zf = (self._ac == 0) 
            #print("AI1 Instruction")

        if self._ir == 'BD1':
            self._bc -= 1
            self._zf = (self._bc == 0) 
            #print("BD1 Instruction")

        if self._ir == 'BI1':
            self._bc += 1
            self._zf = (self._bc == 0) 
            #print("BI1 Instruction")

        if self._ir == 'JMP':
            self._fetch()
            self._pc = int(self._ir)
            #print("JMP {} Instruction".format(self._ir))

        if self._ir == 'JZ':
            self._fetch()
            #print("JZ {} Instruction zf={}".format(self._ir, self._zf))
            if self._zf:
                self._pc += int(self._ir)

        pass

    def _execute(self):
        if ASM.isEXIT(self._ir):
            killIRQ = IRQ(KILL_INTERRUPTION_TYPE)
            self._interruptVector.handle(killIRQ)
        elif ASM.isIO(self._ir):
            ioInIRQ = IRQ(IO_IN_INTERRUPTION_TYPE, self._ir)
            self._interruptVector.handle(ioInIRQ)
        elif ASM.isPAGEFAULT(self._ir):
            pageFaultIRQ = IRQ(PAGE_FAULT_INTERRUPTION_TYPE, self.ir)
            self._interruptVector.handle(pageFaultIRQ)
        else:
            log.logger.info("cpu - Exec: {instr}, PC={pc} A={ac} B={bc} SP={sp} zflag={z}".format(instr=self._ir, pc=self._pc, ac=self._ac, bc=self._bc, sp=self._sp, z=self._zf))


    def isBusy(self):
        return self._pc != -1

    @property
    def context(self):
        # keep sync with so#297 and setter below
        return (self._pc, self._ac, self._bc, self._sp, self._zf)

    @context.setter
    def context(self, values):
        (self._pc, self._ac, self._bc, self._sp, self._zf) = values

    @property
    def pc(self):
        return self._pc

    @pc.setter
    def pc(self, addr):
        self._pc = addr


    def __repr__(self):
        return "CPU(PC={pc})".format(pc=self._pc)

## emulates an Input/output device of the Hardware
class AbstractIODevice():

    def __init__(self, deviceId, deviceTime):
        self._deviceId = deviceId
        self._deviceTime = deviceTime
        self._busy = False

    @property
    def deviceId(self):
        return self._deviceId

    @property
    def is_busy(self):
        return self._busy

    @property
    def is_idle(self):
        return not self._busy


    ## executes an I/O instruction
    def execute(self, operation):
        if (self._busy):
            raise Exception("Device {id} is busy, can't  execute operation: {op}".format(id = self.deviceId, op = operation))
        else:
            self._busy = True
            self._ticksCount = 0
            self._operation = operation

    def tick(self, tickNbr):
        if (self._busy):
            self._ticksCount += 1
            if (self._ticksCount > self._deviceTime):
                ## operation execution has finished
                self._busy = False
                ioOutIRQ = IRQ(IO_OUT_INTERRUPTION_TYPE, self._deviceId)
                HARDWARE.interruptVector.handle(ioOutIRQ)
            else:
                log.logger.info("device {deviceId} - Busy: {ticksCount} of {deviceTime}".format(deviceId = self.deviceId, ticksCount = self._ticksCount, deviceTime = self._deviceTime))


class PrinterIODevice(AbstractIODevice):
    def __init__(self):
        super(PrinterIODevice, self).__init__("Printer", 3)


class Timer:

    def __init__(self, cpu, interruptVector):
        self._cpu = cpu
        self._interruptVector = interruptVector
        self._tickCount = 0    # cantidad de de ciclos “ejecutados” por el proceso actual
        self._active = False    # por default esta desactivado
        self._quantum = 0   # por default esta desactivado

    def tick(self, tickNbr):
        # registro que el proceso en CPU corrio un ciclo mas
        self._tickCount += 1

        if self._active and (self._tickCount > self._quantum) and self._cpu.isBusy():
            # se “cumplio” el limite de ejecuciones
            timeoutIRQ = IRQ(TIMEOUT_INTERRUPTION_TYPE)
            self._interruptVector.handle(timeoutIRQ)
        else:
            self._cpu.tick(tickNbr)

    def reset(self):
           self._tickCount = 0

    @property
    def quantum(self):
        return self._quantum

    @quantum.setter
    def quantum(self, quantum):
        self._active = True
        self._quantum = quantum




## emulates the Hardware that were the Operative System run
class Hardware():

    ## Setup our hardware
    def setup(self, memorySize):
        ## add the components to the "motherboard"
        self._memory = Memory(memorySize)
        self._interruptVector = InterruptVector()
        self._clock = Clock()
        self._ioDevice = PrinterIODevice()
        self._mmu = MMU(self._memory)
        self._cpu = Cpu(self._mmu, self._interruptVector)
        self._timer = Timer(self._cpu, self._interruptVector)
        self._clock.addSubscriber(self._ioDevice)
        self._clock.addSubscriber(self._timer)

    def switchOn(self):
        log.logger.info(" ---- SWITCH ON ---- ")
        return self.clock.start()

    def switchOff(self):
        self.clock.stop()
        log.logger.info(" ---- SWITCH OFF ---- ")

    @property
    def cpu(self):
        return self._cpu

    @property
    def clock(self):
        return self._clock

    @property
    def interruptVector(self):
        return self._interruptVector

    @property
    def memory(self):
        return self._memory

    @property
    def mmu(self):
        return self._mmu

    @property
    def ioDevice(self):
        return self._ioDevice


    @property
    def timer(self):
        return self._timer

    @property
    def timeUnit(self):
        return self._clock.tickUnitInSec

    @timeUnit.setter
    def timeUnit(self, value):
        self._clock.tickUnitInSec = value

    def __repr__(self):
        return "HARDWARE state {cpu}\n{mem}".format(cpu=self._cpu, mem=self._memory)

### HARDWARE is a global variable
### can be access from any
HARDWARE = Hardware()

