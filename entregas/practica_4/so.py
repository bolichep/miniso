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

    def contextSwitchFromRunningTo(self, toState):
        prevPCB = self.kernel.pcbTable.runningPCB
        prevPCB.state = toState
        self.kernel.dispacher.save(prevPCB)
        self.kernel.pcbTable.runningPCB = None
        if toState == State.sterminated:
            self.kernel.pcbTable.remove(prevPCB.pid)
        else:
            self.kernel.pcbTable.update(prevPCB)
        if self.kernel.scheduler.hasNext():
            nextPCB = self.kernel.scheduler.getNext()
            nextPCB.state = State.srunning
            self.kernel.pcbTable.runningPCB = nextPCB
            self.kernel.pcbTable.update(nextPCB)
            self.kernel.dispacher.load(nextPCB)
        return prevPCB

    def contextSwitchToReadyOrRunning(self, nextPCB):
        runningPCB = self.kernel.pcbTable.runningPCB
        if runningPCB == None:
            self.kernel.dispacher.load(nextPCB)
            nextPCB.state = State.srunning
            self.kernel.pcbTable.runningPCB = nextPCB
        else:
            nextPCB.state = State.sready
            self.kernel.scheduler.add(nextPCB)
            if self.kernel.scheduler.mustExpropiate(runningPCB, nextPCB):
                self.contextSwitchFromRunningTo(State.sready)
                nextPCB.state = State.srunning
                self.kernel.pcbTable.runningPCB = nextPCB
                self.kernel.pcbTable.update(nextPCB)
                self.kernel.dispacher.load(nextPCB)
        self.kernel.pcbTable.update(nextPCB)
                


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        self.contextSwitchFromRunningTo(State.sterminated)


class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        HARDWARE.timer.reset()
        operation = irq.parameters
        pcb = self.contextSwitchFromRunningTo(State.swaiting)
        log.logger.info(self.kernel.ioDeviceController)
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        

class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        (program, priority) = irq.parameters
        log.logger.info("New loading {} {}".format(program, priority))
        baseDir, limit = self.kernel.loader.load(program)
        pcb = ProcessControlBlock(program, baseDir, limit, priority)
        pcb.state = State.snew
        self.kernel.pcbTable.update(pcb) #add pcb
        # to ready or running
        self.contextSwitchToReadyOrRunning(pcb)


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        pcb.state = State.sready
        self.kernel.pcbTable.update(pcb) #update pcb
        # to ready or running
        self.contextSwitchToReadyOrRunning(pcb)
        log.logger.info(self.kernel.ioDeviceController)

class TimeoutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        HARDWARE.timer.reset()
        if self.kernel.scheduler.hasNext():
            pcb = self.kernel.scheduler.getNext()
            self.contextSwitchToReadyOrRunning(pcb)


#emul dispacher
class Dispacher():

    def load(self, pcb):
        HARDWARE.cpu.pc = pcb.pc
        HARDWARE.mmu.baseDir = pcb.baseDir
        HARDWARE.mmu.limit = pcb.limit

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
        self._tablePcb = dict()
        self._running = None

    def get(self, pid):
        return self._tablePcb.get(pid)

    def update(self, pcb):
        self._tablePcb.update({pcb.pid: pcb})

    def remove(self, pid):
        self._tablePcb.pop(pid)

    @property
    def runningPCB(self):
        return self._running

    @runningPCB.setter
    def runningPCB(self, pcb):
        self._running = pcb

    def __repr__(self):
        return "PCBTable:\n {}".format(self._tablePcb)


#pid counter
class pid():
    number = 0

    @classmethod
    def new(self):
        self.number += 1
        return self.number


# emulates a  pcb(creado por mi :S)
class ProcessControlBlock():

    def __init__(self, nameProgram, baseDir, limit, priority = 0):
        self._pid = pid.new()
        self._baseDir = baseDir
        self._limit = limit
        self._pc  = 0
        self._state =State.snew
        self._path = nameProgram
        self._priority = priority 

    @property
    def priority(self):
        return self._priority

    @priority.setter
    def priority(self, value):
        self._priority = value
            
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
    def limit(self):
        return self._limit

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

    def __repr__(self):
        return "PCB: pid:{:>3} prio:{:>2} baseDir:{:>3} pc:{:>3} limit:{:>3} state: {}\n".format(
                self._pid, self._priority, self._baseDir, self._pc, self._limit, self._state)

# emulates the loader program( prueba)
class Loader():
    def __init__(self):
        self._memoryPos = 0

    @property
    def memoryPos(self):
        return self._memoryPos

    @memoryPos.setter
    def memoryPos(self, value):
        self._memoryPos = value

    def load(self, program):
        progSize = len(program.instructions)
        baseDir = self.memoryPos
        for index in range(self.memoryPos , (progSize + self.memoryPos)):
            inst = program.instructions[index - self.memoryPos]
            HARDWARE.memory.put(index, inst)

        self.memoryPos = index + 1
        return baseDir, progSize - 1 # limit = progSize - 1


class AbstractScheduler():

    def __init__(self):
        self._readyQueue = self.emptyReadyQueue()

    def emptyReadyQueue(self):
        return []

    @property
    def readyQueue(self):
        return self._readyQueue

    def mustExpropiate(self, pcbInCPU, pcbToAdd):
        return False


class SchedulerNonPreemtive(AbstractScheduler):

    # uso el readyqueue al revés
    # a mojorar el orden... ya que sorted seria O(N log N)
    def add(self, pcb):
        self._readyQueue.append(pcb)
        # sorted seria  O(N log N), buscar mejor opcion
        self._readyQueue = sorted ( self._readyQueue, key = lambda x: 0 - x.priority)
        print(self._readyQueue)


    # lo uso al revés ya que pop(0) es O(n) y pop() es O(1)
    # prec: readyQueue no esta vacia
    def getNext(self):
        return self._readyQueue.pop()


    def hasNext(self):
        return  self._readyQueue


class SchedulerPreemtive(SchedulerNonPreemtive):

    def mustExpropiate(self, pcbInCPU, pcbToAdd):
        return pcbInCPU.priority > pcbToAdd.priority

  
class SchedulerFCFS(AbstractScheduler):

    def add(self, pcb):
        self._readyQueue.append(pcb)

    def getNext(self):
        return self._readyQueue.pop(0) #.pop(0) is O(n)

    def hasNext(self):
        return  self._readyQueue

class SchedulerRRB(AbstractScheduler):

    def add(self, nextPCB):
        self._readyQueue.append(nextPCB)

    def getNext(self):
        return self._readyQueue.pop(0)

    def hasNext(self):
        return self._readyQueue


  

# emulates the core of an Operative System
class Kernel():

    def __init__(self, scheduler):
        ## setup interruption handlers
        newHandler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        timeoutHandler = TimeoutInterruptionHandler(self)
        HARDWARE.interruptVector.register(TIMEOUT_INTERRUPTION_TYPE, timeoutHandler)

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)

        self._pcbTable = PcbTable()
        self._dispacher = Dispacher()

        self._scheduler = scheduler
        self._loader = Loader()


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
         
    ## emulates a "system call" for programs execution
    def run(self, program, priority):
        newINT = IRQ(NEW_INTERRUPTION_TYPE, (program, priority))
        #log.logger.info("Set New Int Handler")# ayuda visual
        HARDWARE.interruptVector.handle(newINT)
        log.logger.info("\n Executing program: {name}".format(name=program.name))
        log.logger.info(HARDWARE)

    @property
    def scheduler(self):
        return self._scheduler

    def __repr__(self):
        return "Kernel "
