#!/usr/bin/env python

from hardware import *
import log
from enum import Enum


## emulates a compiled program
class Program():

    def __init__(self, instructions):
        self._instructions = self.expand(instructions)

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
        return "Program({instructions})".format(instructions=self._instructions)


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

    def contextSwitchFromRunningTo (self, toState):
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
        if self.kernel.pcbTable.runningPCB == None:
            self.kernel.dispacher.load(nextPCB)
            nextPCB.state = State.srunning
            self.kernel.pcbTable.runningPCB = nextPCB
        else:
            nextPCB.state = State.sready
            prevPCB = self.kernel.pcbTable.runningPCB
            if  self.kernel.scheduler.mustExpropiate(prevPCB, nextPCB):
                self.contextSwapPreemtive(nextPCB, prevPCB)
                nextPCB.state = State.srunning
            else : 
                self.kernel.scheduler.add(nextPCB)
        self.kernel.pcbTable.update(nextPCB)

    def contextSwapPreemtive(self, nextPCB, prevPCB):
        prevPCB.state = State.sready
        self.kernel.pcbTable.runningPCB = nextPCB
        self.kernel.dispacher.save(prevPCB)
        self.kernel.pcbTable.update(prevPCB)
        self.kernel.dispacher.load(nextPCB)
        self.kernel.scheduler.add(prevPCB)

    def contextSwapPreemtiveTimeOut(self, nextPCB):
        nextPCB.state = State.sready
        prevPCB = self._kernel.pcbTable.runningPCB
        self.contextSwapPreemtive(nextPCB, prevPCB)
        nextPCB.state = State.srunning
        self.kernel.pcbTable.update(nextPCB)


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        pcb = self.kernel.pcbTable.runningPCB 
        self.contextSwitchFromRunningTo(State.sterminated)
        pages= self.kernel.memoryManager.getPageTable(pcb.pid)

        self.kernel._memoryManager.freeFrames(pages)


class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        programName, programCode, priority = irq.parameters
        priority = 4 if priority > 4 or priority < 0 else priority
        log.logger.info("New loading {} {}".format(programName, priority))
        pages, baseDir, limit = self.kernel.loader.load(programName)
        pcb = ProcessControlBlock(programName, priority, baseDir, limit)
        pcb.state = State.snew
        #pcb.pages = pages
        self.kernel.memoryManager.putPageTable(pcb.pid, pages)
        self.kernel.pcbTable.update(pcb) #add pcb
        # to ready or running
        self.contextSwitchToReadyOrRunning(pcb)
        

class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters
        pcb = self.contextSwitchFromRunningTo(State.swaiting)
        log.logger.info(self.kernel.ioDeviceController)
        self.kernel.ioDeviceController.runOperation(pcb, operation)


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
        
        if self.kernel.scheduler.hasNext():
            pcb = self.kernel.scheduler.getNext()
            self.contextSwapPreemtiveTimeOut(pcb)
        else:
            self.kernel.dispacher.resetTimer()


#emul dispacher
class Dispacher():
    def __init__(self, kernel):
        self._kernel = kernel

    def load(self, pcb):
        #HARDWARE.cpu.pc = pcb.pc
        HARDWARE.cpu.context = pcb.context #all reg in a big tuple
        HARDWARE.mmu.baseDir = pcb.baseDir
        HARDWARE.mmu.limit = pcb.limit
        HARDWARE.mmu.resetTLB()
        pages = self._kernel.memoryManager.getPageTable(pcb.pid)
        #pages = pcb.pages
        for page in range(0, len(pages)):
            HARDWARE.mmu.setPageFrame(page, pages[page])
        HARDWARE.timer.reset()
        #print("pid: ", pcb.pid, "prio: ", pcb.priority, "TLB: ", HARDWARE.mmu._tlb)

    def save(self, pcb):
        pcb.context = HARDWARE.cpu.context # all regs in a big tuple
        #pcb.pc = HARDWARE.cpu.pc
        HARDWARE.cpu.pc = -1

    def resetTimer(self):
        HARDWARE.timer.reset()

    def addSubscriber(self, subscriber):
        HARDWARE.clock.addSubscriber(subscriber)


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

    def update(self, pcb, updState):
        if self.runningPCB != None and pcb.pid == self.runningPCB.pid and updState != State.srunning:
            self._running = None
        pcb.state = updState
        if updState == State.srunning:
            self._running = pcb
        if updState == State.sterminated:
            self._tablePcb.pop(pcb.pid)
        else:
            self._tablePcb.update({pcb.pid: pcb})

    def update(self, pcb):
        self._tablePcb.update({pcb.pid: pcb})

    def remove(self, pid):
        self._tablePcb.pop(pid)

    @property
    def table(self):
        return self._tablePcb
    
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

    def __init__(self, programName, priority, pages = [], baseDir = 0, limit = 0):
        self._pid = pid.new()
        self._baseDir = baseDir
        self._limit = limit
        self._pc  = 0 # TODO check if keep that
        self._state =State.snew
        # well knew cpu reset state
        self._context = (0, 0, 0, -1, True) # keep sync with hardware#330
        self._path = programName
        self._priority = priority 

    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, value):
        self._context = value
            
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

    @baseDir.setter
    def baseDir(self, value):
        self._baseDir = value

    @property
    def limit(self):
        return self._limit

    @baseDir.setter
    def limit(self, value):
       self._limit = value

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

    def __init__(self, fileSystem, memoryManager):
        self._memoryPos = 0
        self._fs = fileSystem
        self._mm = memoryManager

    @property
    def memoryPos(self):
        return self._memoryPos

    @memoryPos.setter
    def memoryPos(self, value):
        self._memoryPos = value

    def load(self, path):
        programCode = self._fs.read(path)
        progSize = len(programCode.instructions)
        pages = self._mm.allocFrames(progSize)
        if not pages:
            raise Exception("\x9B37;44m\x9B2J\x9B12;18HException: No Hay memoria. [BSOD]... o demandá ;P \x9B14;18H(!!!)\x9B0m")
        
        for instAddr in range(0, progSize):
            pageId = instAddr % self._mm._frameSize
            offset = pages[instAddr // self._mm._frameSize]
            physicalAddress = pageId + offset * self._mm._frameSize
            inst = programCode.instructions[instAddr]
            self._mm.memory.put(physicalAddress, inst)
            #print(physicalAddress, inst)

        # TODO eliminar baseDir
        baseDir = 0
        return pages, baseDir, progSize - 1 # limit = progSize - 1


class AbstractScheduler():

    def emptyReadyQueue(self):
        return []

    @property
    def readyQueue(self):
        return self._readyQueue

    @property
    def name(self):
        return self._name

    def __repr__(self):
        return "{}\n {}".format(self._name, self._readyQueue)


class SchedulerNonPreemtive(AbstractScheduler):

    def __init__(self):
        self._name = "Non Preemtive"
        self._cantE = 0
        self._ageReset = 1
        self._ageCount = self._ageReset
        self._readyQueue0 = self.emptyReadyQueue()
        self._readyQueue1 = self.emptyReadyQueue()
        self._readyQueue2 = self.emptyReadyQueue()
        self._readyQueue3 = self.emptyReadyQueue()
        self._readyQueue4 = self.emptyReadyQueue()

    def add(self, pcb):
        self._cantE += 1
        if pcb.priority == 0 :
            self._readyQueue0.insert(0, pcb)
        elif pcb.priority == 1 :
            self._readyQueue1.insert(0, pcb)
        elif pcb.priority == 2 :
            self._readyQueue2.insert(0, pcb)
        elif pcb.priority == 3 :
            self._readyQueue3.insert(0, pcb)
        elif pcb.priority == 4 :
            self._readyQueue4.insert(0, pcb)

    # prec: hay al menos un pcb en el queue
    def getNext(self):
        self._cantE -= 1
        self._ageCount -= 1
        if self._shouldIAging():
             self._aging()
        if self._readyQueue0 :
            return self._readyQueue0.pop()
        elif self._readyQueue1 : 
            return self._readyQueue1.pop()
        elif self._readyQueue2 :
            return self._readyQueue2.pop()
        elif self._readyQueue3 :
            return self._readyQueue3.pop()
        elif self._readyQueue4 :
            return self._readyQueue4.pop()

    def _shouldIAging(self):
        return self._ageCount == 0

    def _aging(self):
        self._ageCount = self._ageReset
        if self._readyQueue4 :
            self._readyQueue3.insert(0,
                                     self._readyQueue4.pop())
        elif self._readyQueue3 and not(self._readyQueue4): 
            self._readyQueue2.insert(0, 
                                     self._readyQueue3.pop())
        elif self._readyQueue2 and not(self._readyQueue3):
            self._readyQueue1.insert(0, 
                                     self._readyQueue2.pop())
        elif self._readyQueue1 and not(self._readyQueue2):
            self._readyQueue0.insert(0, 
                                     self._readyQueue1.pop())

    def hasNext(self):
        return self._cantE > 0

    def mustExpropiate(self, pcb1, pcb2):
        return False        

    def __repr__(self):
        return "Scheduler readyQueue {}\n0{}\n1{}\n2{}\n3{}\n4{}".format(
                self._name
                ,self._readyQueue0
                ,self._readyQueue1
                ,self._readyQueue2
                ,self._readyQueue3
                ,self._readyQueue4
                )


class SchedulerPreemtive(SchedulerNonPreemtive):

    def __init__(self):
        super().__init__()
        self._name = "Preemtive"

    def mustExpropiate (self, pcbrunning, pcbready):
        return pcbrunning.priority > pcbready.priority
  
class SchedulerFCFS(AbstractScheduler):

    def __init__(self):
        self._name = "First Come First Served"
        self._readyQueue = self.emptyReadyQueue()

    def add(self, pcb):
        self._readyQueue.insert(0, pcb) #.insert(0, x) is O(n)

    def getNext(self):
        return self._readyQueue.pop() #.pop(0) is O(n)

    def hasNext(self):
        return  self._readyQueue

    def mustExpropiate(self, pcb1, pcb2):
        return False

class SchedulerRRB(AbstractScheduler):

    def __init__(self):
        self._name = "Round Robin"
        self._readyQueue = []

    def add(self, pcb):
        self._readyQueue.insert(0, pcb)

    def getNext(self):
        return self._readyQueue.pop() #.pop(0) is O(n)

    def hasNext(self):
        return self._readyQueue

    def mustExpropiate(self, pcb1, pcb2):
        return False

class Gantt():

    def __init__(self, kernel):
        self._kernel = kernel
        self._kernel.dispacher.addSubscriber(self)
        self._ticks = -1
        self._graph = dict()

    def ticks(self):
        return self._ticks

    def tick(self, tickNbr):
        self._ticks += 1
        g = ""
        for (i, pcb)  in self._kernel.pcbTable.table.items():
            if pcb.pid not in self._graph:
                self._graph[pcb.pid] = "{}   {}    {}".format(pcb.pid, pcb.priority, " " * self._ticks)

            if pcb.state == State.srunning:
                self._graph[pcb.pid] += "\x9B7mR\x9B0m"
            elif pcb.state == State.sready:
                self._graph[pcb.pid] += "r"
            elif pcb.state == State.swaiting:
                self._graph[pcb.pid] += "w"
            else:
                self._graph[pcb.pid] += "."

        log.logger.info("Gantt ***** {}\npid prio (R)unning (r)eady (w)aiting".format(self._ticks))
        for (i, string) in self._graph.items():
            log.logger.info(string)
  

# file system basico
class Fsb:

    def __init__(self):
        self._fs = dict()

    @property
    def root(self):
        return self._fs

    def write(self, fname, content):
        self._fs.update({fname:content})

    # denota una lista con el contenido del archivo fname
    def read(self, fname):
        return self._fs.get(fname)


class MemoryManager:

    def __init__(self, memory, frameSize):
        self._memory = memory       
        self._freeFrames = [x for x in range (0,(memory.getLeng() // frameSize)) ]
        self._frameSize = frameSize
        self._pageTables = dict()

    def allocFrames(self, numberOfCells):
        framesToAlloc = 1 if numberOfCells % self._frameSize else 0
        framesToAlloc += numberOfCells // self._frameSize
        if framesToAlloc <= len(self._freeFrames):
            allocatedFrames = self._freeFrames[0:framesToAlloc]
            self._freeFrames = self._freeFrames[framesToAlloc:]
        else:
            allocatedFrames = []
        #print("Allocating: ", allocatedFrames, "Frees: ",  self._freeFrames, "FrameSize: ", self._frameSize)
        return allocatedFrames

    def freeFrames(self, frames):
        #print("Freeing: ", frames, "Prev Frees: ", self._freeFrames)
        self._freeFrames += frames
        #print("Current Frees: ", self._freeFrames)
     
    def putPageTable(self, pid, pages):
        self._pageTables.update({pid: pages})

    def getPageTable(self, pid):
        return self._pageTables.get(pid)
  

    @property
    def memory(self):
        return self._memory


# emulates the core of an Operative System
class Kernel():

    def __init__(self, hardware,scheduler, frameSize):


        self._hardware = hardware
        ## setup interruption handlers
        newHandler = NewInterruptionHandler(self)
        self._hardware.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        killHandler = KillInterruptionHandler(self)
        self._hardware.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        self._hardware.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        self._hardware.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        timeoutHandler = TimeoutInterruptionHandler(self)
        self._hardware.interruptVector.register(TIMEOUT_INTERRUPTION_TYPE, timeoutHandler)


        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(self._hardware.ioDevice)


        self._pcbTable = PcbTable()
        self._dispacher = Dispacher(self)

        self._gantt_graphic = Gantt(self)

        self._scheduler = scheduler
        self._fileSystem = Fsb()

        self._hardware.mmu.frameSize = frameSize
        self._memoryManager = MemoryManager(self._hardware.memory, self._hardware.mmu.frameSize)

        self._loader = Loader(self._fileSystem, self._memoryManager)

    @property
    def fileSystem(self):
        return self._fileSystem

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
    def gantt(self):
        return self._gantt_graphic
    
    @property
    def ioDeviceController(self):
        return self._ioDeviceController
         
    ## emulates a "system call" for programs execution
    def run(self, programName, priority):
        programCode = self.fileSystem.read(programName) # read file
        newINT = IRQ(NEW_INTERRUPTION_TYPE, (programName, programCode, priority))
        #log.logger.info("Set New Int Handler")# ayuda visual
        self._hardware.interruptVector.handle(newINT)
        log.logger.info("\n Executing program: {name}".format(name=programName))
        log.logger.info(self._hardware)

    @property
    def memoryManager(self):
        return self._memoryManager
    
    @property
    def scheduler(self):
        return self._scheduler

    def __repr__(self):
        return "Kernel "
 
