#!/usr/bin/env python

from hardware import *
import log
from enum import Enum



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



class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        if len(self.kernel.readyQueue ) != 0:
            pcbFinish = self.kernel.readyQueue.pop(0)
            pcbFinish.state = State.sterminated
            self.kernel.pcbTable.runningPCB = None
            if len(self.kernel.readyQueue) > 1 :
                newRunningPCB = self.kernel.readyQueue[0]
                newRunningPCB.state = State.srunning
                self.kernel.pcbTable.running = newRunningPCB
                self.kernel.dispacher.load(self.kernel.readyQueue[0]) ## (original -1) ahora toma el valor pc del pcb
            else:
                HARDWARE.switchOff()

class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters
        pcb = self.kernel.readyQueue.pop(0)  #pcb ={'pc': HARDWARE.cpu.pc } # porque hacemos esto ??? para guardar el "estado actual del proceso"
        self.kernel.dispacher.save(pcb)                              #   HARDWARE.cpu.pc = -1
        if len(self.kernel.readyQueue) >= 1:
            pcb.state = State.swaiting
            pcbRunning =self.kernel.readyQueue[0]
            pcbRunning.state = State.srunning
            self.kernel.pcbTable.runningPCB = pcbRunning
            self.kernel.dispacher.load(pcbRunning)
        
        log.logger.info(self.kernel.ioDeviceController)
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        #HARDWARE.cpu.pc =  pcb['pc'] #original
        pcb.state = State.sready
        self.kernel.readyQueue.append(pcb)
        #prueba ->
        #pcbinProgres = self.kernel.pcbTable.runningPCB
        #self.kernel.dispacher.save(pcbinProgres)
        #pcbinProgres.state = State.sready
        #self.kernel.readyQueue.insert(0, pcb)
        #self.kernel.dispacher.load(pcb)
        #self.kernel.pcbTable.runningPCB = pcb
        if len(self.kernel.readyQueue) == 1 :
            self.kernel.dispacher.load(pcb)

        
        log.logger.info(self.kernel.ioDeviceController)


#emul dispacher
class Dispacher():

    def load(self, pcb):
        HARDWARE.cpu.pc = pcb.pc
        HARDWARE.mmu.baseDir = pcb.baseDir
    def save(self, pcb):
        pcb.pc = HARDWARE.cpu.pc
        HARDWARE.cpu.pc = -1

#enum states of a process(mio)
class State(Enum):
    snew = 0
    sready = 1
    srunning = 2
    swaiting = 3
    sterminated = 4

#emul pcb table
class PcbTable():
    def __init__(self):
        self._pid = 0
        self._QueuePcb = []
        self._running = None
    def get(self, pid):
        return self._QueuePcb.index(pid)
    def add(self, pcb):
        self._QueuePcb.insert(pcb.pid, pcb)
    def remove(self, pid):
        self._QueuePcb.pop(pid)
    @property
    def runningPCB(self):
        return self._running
    @runningPCB.setter
    def runningPCB(self, pcb):
        self._running = pcb
    def getNewPit(self):
        return self._pid
        self._pid +=1    



# emulates a  pcb(creado por mi :S)
class ProcessControlBlock():
    def __init__(self, nameProgram, pid, baseDir):
        self._pid = pid
        self._baseDir = baseDir
        self._pc  = 0
        self._state =State.snew
        if nameProgram != None:
            self._path = nameProgram
    @property
    def pid(self):
        return self._pid
    @property
    def path(self):
        return self._path
    @property
    def baseDir(self):
        return self._baseDir
    @property
    def pc(self):
        return self._pc 
    @pc.setter
    def pc(self, pc):
        self._pc = pc
    @property
    def state(self):
        return self._state
    @state.setter
    def state(self, state):
        self._state = state

# emulates the loader program( prueba)
class Loader():
    def __init__(self):
        self._memoryPos = 0

    @property
    def memoryPos(self):
        return self._memoryPos

    
    def memoryPosSetter(self, value):
        self._memoryPos = value

    def load(self, program):
        progSize = len(program.instructions)
        basedir = self.memoryPos
        for index in range(self.memoryPos , (progSize + self.memoryPos)):
            inst = program.instructions[index - self.memoryPos]
            HARDWARE.memory.put(index, inst)

        self.memoryPosSetter(index + 1)
        return basedir

  

# emulates the core of an Operative System
class Kernel():

    def __init__(self):
        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)

        self._pcbTable = PcbTable()
        self._dispacher = Dispacher()

        self._readyQueue = []
        self._loader = Loader()


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
    def pcbTable(self):
        return self._pcbTable
    @property
    def dispacher(self):
        return self._dispacher
    
    
    
    @property
    def ioDeviceController(self):
        return self._ioDeviceController
    
    def load_program(self, program):
        # loads the program in main memory
        basedir = self.loader.load(program)
        pcb = ProcessControlBlock(program.name, self.pcbTable.getNewPit(), basedir)
        pcb.state = State.sready
        self.readyQueue.append(pcb)
        self.pcbTable.add(pcb)
 
    ## emulates a "system call" for programs execution
    def run(self, program):
        self.load_program(program)
        log.logger.info("\n Executing program: {name}".format(name=program.name))
        log.logger.info(HARDWARE)

        # set CPU program counter at program's first intruction
        HARDWARE.cpu.pc = 0
        self.pcbTable.runningPCB = self.readyQueue[0]


    def __repr__(self):
        return "Kernel "
