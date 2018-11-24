#!/usr/bin/env python

from tabulate import tabulate
from time import sleep
from threading import Thread, Lock
import log

##  Estas son la instrucciones soportadas por nuestro CPU
INSTRUCTION_HEADER = 'HEADER'
INSTRUCTION_LABEL = 'LABEL'
INSTRUCTION_JNZ = 'JNZ'
INSTRUCTION_JZ = 'JZ'
INSTRUCTION_JMP = 'JMP'
INSTRUCTION_CALL = 'CALL'
INSTRUCTION_RET = 'RET'
INSTRUCTION_STORA = 'STORA'
INSTRUCTION_STORB = 'STORB'
INSTRUCTION_DECA = 'DECA'
INSTRUCTION_INCA = 'INCA'
INSTRUCTION_INCB = 'INCB'
INSTRUCTION_DECB = 'DECB'
INSTRUCTION_ADDAB = 'ADDAB'
INSTRUCTION_CMPAB = 'CMPAB'
INSTRUCTION_PUSHA = 'PUSHA'
INSTRUCTION_POPA = 'POPA'
INSTRUCTION_PUSHB = 'PUSHB'
INSTRUCTION_POPB = 'POPB'
INSTRUCTION_EXIT = 'EXIT'
INSTRUCTION_IO = 'IO'
INSTRUCTION_CPU = 'CPU'

## Helper for emulated machine code
class ASM():

    # keep label, address map
    symbols = dict()
    # keep current addr assembled
    addrCounter = 0


    @classmethod
    def reset(self):
        self.addrCounter = 0

    # replace symbol with address
    @classmethod
    def secondPass(self, passOneCode):
        passTwoCode = []
        for i in passOneCode:
            passTwoCode.append(self.__addrInTable(i))

        self.reset()
        return passTwoCode

    # return maped value in symbol table map
    # if it is a string and is on table
    # else original value
    @classmethod
    def __addrInTable(self, value):
        if isinstance(value, str) and value in self.symbols:
            value = self.symbols[value]
        return value

    @classmethod
    def __afterCount(self, instructions):
        self.addrCounter += len(instructions)
        return instructions

    @classmethod
    def HEADER(self, space):
        return self.__afterCount(
                [INSTRUCTION_JMP, str(space)] + ['0']* (space-2))

    @classmethod
    def LABEL(self, labelName):
        self.symbols[labelName] = self.addrCounter
        return [] # must i return? TODO

    @classmethod
    def JNZ(self, address):
        return self.__afterCount([INSTRUCTION_JNZ, str(address)])

    @classmethod
    def JZ(self, address):
        return self.__afterCount([INSTRUCTION_JZ, str(address)])

    @classmethod
    def JMP(self, address):
        return self.__afterCount([INSTRUCTION_JMP, str(address)])

    @classmethod
    def CALL(self, address):
        return self.__afterCount([INSTRUCTION_CALL, str(address)])

    @classmethod
    def RET(self):
        return self.__afterCount([INSTRUCTION_RET])

    @classmethod
    def STORA(self, value):
        return self.__afterCount([INSTRUCTION_STORA, str(value)])

    @classmethod
    def STORB(self, value):
        return self.__afterCount([INSTRUCTION_STORB, str(value)])

    @classmethod
    def DECA(self, times):
        return self.__afterCount([INSTRUCTION_DECA] * times)

    @classmethod
    def INCA(self, times):
        return self.__afterCount([INSTRUCTION_INCA] * times)

    @classmethod
    def INCB(self, times):
        return self.__afterCount([INSTRUCTION_INCB] * times)

    @classmethod
    def DECB(self, times):
        return self.__afterCount([INSTRUCTION_DECB] * times)

    @classmethod
    def ADDAB(self):
        return self.__afterCount([INSTRUCTION_ADDAB])

    @classmethod
    def CMPAB(self):
        return self.__afterCount([INSTRUCTION_CMPAB])

    @classmethod
    def PUSHA(self):
        return self.__afterCount([INSTRUCTION_PUSHA])

    @classmethod
    def POPA(self):
        return self.__afterCount([INSTRUCTION_POPA])

    @classmethod
    def PUSHB(self):
        return self.__afterCount([INSTRUCTION_PUSHB])

    @classmethod
    def POPB(self):
        return self.__afterCount([INSTRUCTION_POPB])

    @classmethod
    def EXIT(self, times):
        return self.__afterCount([INSTRUCTION_EXIT] * times)

    @classmethod
    def IO(self):
        return self.__afterCount([INSTRUCTION_IO])

    @classmethod
    def CPU(self, times):
        return self.__afterCount([INSTRUCTION_CPU] * times)

    @classmethod
    def isEXIT(self, instruction):
        return INSTRUCTION_EXIT == instruction

    @classmethod
    def isIO(self, instruction):
        return INSTRUCTION_IO == instruction



##  Estas son la interrupciones soportadas por nuestro Kernel
KILL_INTERRUPTION_TYPE       = "#KILL"
IO_IN_INTERRUPTION_TYPE      = "#IO_IN"
IO_OUT_INTERRUPTION_TYPE     = "#IO_OUT"
NEW_INTERRUPTION_TYPE        = "#NEW"
TIMEOUT_INTERRUPTION_TYPE    = "#TIMEOUT"
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

    def updateTLB(self, pageNumber, page):
        self._tlb.update({pageNumber: page})

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
            page = self._tlb[pageId]
        except:
            raise Exception("\n*\n* ERROR \n*\n Error en el MMU\nNo se cargo la pagina  {pageId}".format(pageId = str(pageId)))

        if not page.isValid:
            pageFaultIRQ = IRQ(PAGE_FAULT_INTERRUPTION_TYPE, pageId)
            HARDWARE.cpu._interruptVector.handle(pageFaultIRQ)
            page = self._tlb[pageId]
            print(" -----------  DESPUES DE # PAGE_FAULT")
            print(page)
            print(" -----------  DESPUES DE # PAGE_FAULT")



        frameId = page.frame
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
        self._or = None
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
        if self.isOOI(self._ir):
            self._or = self._mmu.fetch(self._pc)
            self._pc += 1
        #print("fetch: pc={}  ir={}".format( self._pc, self._ir))

    def _decode(self):
        if self._ir == 'IO':
            #print("IO Instruction")
            pass

        if self._ir == 'EXIT':
            print("\x9B7m", end="")
            print("A Reg : ", self._ac, "/ B Reg : ", self._bc,"/ z flag: ", self._zf)
            print("\x9B0m", end="")
            pass

        if self._ir == 'CALL':
            self._sp += 1
            self._mmu.write(self._sp, self._pc )
            self._pc = int(self._or)
            print("CALL instruction")

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

        if self._ir == 'STORA':
            self._ac = int(self._or)
            print("STORA Instruction")

        if self._ir == 'STORB':
            self._bc = int(self._or)
            print("STORB Instruction")

        if self._ir == 'DECA':
            self._ac -= 1
            self._zf = (self._ac == 0)
            print("DECA Instruction")

        if self._ir == 'INCA':
            self._ac += 1
            self._zf = (self._ac == 0)
            print("INCA Instruction")

        if self._ir == 'DECB':
            self._bc -= 1
            self._zf = (self._bc == 0)
            print("DECB Instruction")

        if self._ir == 'INCB':
            self._bc += 1
            self._zf = (self._bc == 0)
            print("INCB Instruction")

        if self._ir == 'ADDAB':
            self._ac += self._bc
            self._zf = self._ac == 0
            print("ADDAB Instruction")

        if self._ir == 'CMPAB':
            self._zf = self._ac == self._bc
            print("CMPAB Instruction")

        if self._ir == 'JMP': #Jump absoluto
            self._pc = int(self._or)
            print("JMP {} Instruction".format(self._pc))

        if self._ir == 'JNZ': # absoluto
            print("JNZ {} Instruction zf={}".format(
                       self._or, self._zf))
            if not self._zf:
                self._pc = int(self._or)

        if self._ir == 'JZ': # absoluto
            print("JZ {} Instruction zf={}".format(
                       self._or, self._zf))
            if self._zf:
                self._pc = int(self._or)

        pass

    def __repr__(self):
        return "cpu - IR={instr}, PC={pc} A={ac} B={bc} SP={sp} zflag={z}".format(instr=self._ir, pc=self._pc, ac=self._ac, bc=self._bc, sp=self._sp, z=self._zf)

    # is Zero Operand Instruction
    def isZOI(self, ir):
        return not self.isOOI(ir)

    # is One Operand Instruction
    def isOOI(self, ir):
        return ( ir in ['JNZ', 'JZ', 'JMP', 'CALL', 'STORA', 'STORB'])

    def _execute(self):
        if ASM.isEXIT(self._ir):
            killIRQ = IRQ(KILL_INTERRUPTION_TYPE)
            self._interruptVector.handle(killIRQ)
        elif ASM.isIO(self._ir):
            ioInIRQ = IRQ(IO_IN_INTERRUPTION_TYPE, self._ir)
            self._interruptVector.handle(ioInIRQ)
        else:
            log.logger.info("cpu - Exec: {instr:<6} {op:<3}, PC={pc:>3} A={ac:>3} B={bc:>3} SP={sp:>3} zflag={z}".format(
                instr = self._ir,
                op = self._or if self.isOOI(self._ir) else ' ',
                pc = self._pc,
                ac = self._ac,
                bc = self._bc,
                sp = self._sp,
                z  = self._zf
                ))


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

