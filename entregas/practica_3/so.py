#!/usr/bin/env python
#log.logger.info("DEBUG EXIT"); quit()

from hardware import *
import log

from enum import Enum, unique

@unique
class state(Enum):
    NEW = 1
    READY = 2
    WAITING = 3
    RUNNING = 4
    TERMINATED = 5



## emulates a compiled program
class Program():

    def __init__(self, name, instructions):
        self._name = name
        self._instructions = self.expand(instructions)

    @property
    def name(self):
        return self._name

    @property
    def instructions(self):
        return self._instructions

    def addInstr(self, instruction):
        self._instructions.append(instruction)

    def expand(self, instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                ## is a list of instructions
                expanded.extend(i)
            else:
                ## a single instr (a String)
                expanded.append(i)

        ## now test if last instruction is EXIT
        ## if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    def __repr__(self):
        return "Program({name}, {instructions})".format(name=self._name, instructions=self._instructions)


## emulates an Input/Output device controller (driver)
class IoDeviceController():

    def __init__(self, device):
        self._device = device
        self._waiting_queue = []
        self._currentPCB = None

    def runOperation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def getFinishedPCB(self):
        finishedPCB = self._currentPCB
        self._currentPCB = None
        self.__load_from_waiting_queue_if_apply()
        return finishedPCB

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            ## pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            #print(pair)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._currentPCB = pcb
            self._device.execute(instruction)


    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}".format(deviceID=self._device.deviceId, currentPCB=self._currentPCB, waiting_queue=self._waiting_queue)


## emulates the  Interruptions Handlers
class AbstractInterruptionHandler():
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))


class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        baseText = self.kernel.loader.doIt(irq.parameters)
        log.logger.info("load code to memory: {program} in {baseText}".format(
            program=irq.parameters, baseText = baseText) )
        pcb = ProcessControlBlock(programPath = irq.parameters,
                baseDir = baseText)
        log.logger.info("New process {pcb}".format(pcb = pcb.pid))
        log.logger.info("insert process in table")

class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        if len(self.kernel.readyQueue ) != 0:
            self.kernel.readyQueue.pop(0)
        elif len(self.kernel.readyQueue) == 0:
            HARDWARE.switchOff()
        else:
            HARDWARE.mmu.baseDir(self, self.kernel.readyQueue[0].basedir)
            HARDWARE.cpu.cp = -1

class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters
        pcb = {'pc': HARDWARE.cpu.pc} # porque hacemos esto ???

        ##TODO### Aca deberimos hacer el switch context ???????
        HARDWARE.cpu.pc = -1   ## dejamos el CPU IDLE

        self.kernel.ioDeviceController.runOperation(pcb, operation)
        log.logger.info(self.kernel.ioDeviceController)


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        HARDWARE.cpu.pc = pcb['pc']
        log.logger.info(self.kernel.ioDeviceController)


class Dispatcher():
    
    def __init__(self):
        pass

    def Load(self, pcb):
        HARDWARE.cpu.pc = pcb.get('pc')
        HARDWARE.mmu.baseDir = pcb.get('baseDir')

    def Save(self, pcb):
        pcb.update({'pc': HARDWARE.cpu.pc})



#pid counter
class PID():
    number = 0

    @classmethod
    def new(self):
        self.number += 1
        return self.number

class PCBTable():
    # _currentPID is grater than 0
    # _table 

    def __init__(self):
        #
        self._currentPID = 1 # este seria el proceso uno
        self._table = {1: ProcessControlBlock('init', None)}

    def get(self, pid):
        # denota un PCB con el pid dado
        # prec: el pcb con el pid dado existe en _table
        return self._table.get(pid)

    def Add(self, pcb):
        #agregar pcb a la _tabla (diccionario)
        #prec: el pcb no esta en la tabla
        self._table.update({pcb.get('pid'): pcb})
        pass

    def Remove(self, pid):
        #remueve el pcb con pid de _table (diccionario)
        # prec: no esta en ningun queue
        pass

    @property
    def runningPCB(self):
        return self._currentPID

    @runningPCB.setter
    def runningPCB(self, value):
        self._currentPID = value


class ProcessControlBlock():

    def __init__(self, programPath, baseDir):
        self._pid = PID.new()
        self._baseDir = baseDir
        self._pc  = -1
        self._state = state.NEW
        self._path = programPath

    @property
    def pc(self):
        return self._pc

    @pc.setter
    def pc(self, value):
        self._pc = value


    @property
    def pid(self):
        return self._pid
 
    @property
    def path(self):
        return self._path

    @property
    def baseDir(self):
        return self._baseDir
    
# emulates the loader program( prueba)
class Loader():
    def __init__(self, initialFreeCell):
        self._firstFreeCell = initialFreeCell

    @property
    def firstFreeCell(self):
        return self._firstFreeCell
    
    @firstFreeCell.setter
    def firstFreeCell(self, value):
        self._firstFreeCell = value

    def doIt(self, program):

        # para: program is a instance of Program
        progSize = len(program.instructions)
        baseDir = self.firstFreeCell
        log.logger.info("Loader.doIt.....")
        for index in range(self.firstFreeCell , (progSize + self.firstFreeCell)):
            inst = program.instructions[index - self.firstFreeCell]
            HARDWARE.memory.put(index, inst)

        self.firstFreeCell = index + 1
        return baseDir

  

# emulates the core of an Operative System
class Kernel():

    def __init__(self):
        ## setup interruption handlers
        newHandler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)

        self._readyQueue = []
        self._loader = Loader(initialFreeCell = 0)


    @property 
    def readyQueue(self):
       return self._readyQueue
   
    @property
    def pid(self):
        return self._pid

    @property
    def loader(self):
        return self._loader
    
    
    @property
    def ioDeviceController(self):
        return self._ioDeviceController
    
    ## emulates a "system call" for programs execution
    def run(self, program):
        log.logger.info("#send #New interrupt")
        newINT = IRQ(NEW_INTERRUPTION_TYPE,program)
        HARDWARE.interruptVector.handle(newINT)
        #self.load_program(program)
        log.logger.info("\n Executing program: {name}".format(name=program.name))
        log.logger.info(HARDWARE)

        # set CPU program counter at program's first intruction
        HARDWARE.cpu.pc = 0


    def __repr__(self):
        return "Kernel "
