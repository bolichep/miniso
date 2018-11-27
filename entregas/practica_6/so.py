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

        ## now test if last instruction is EXIT or RET
        ## if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXITorRET(last):
            expanded.append(INSTRUCTION_EXIT)

        return ASM.secondPass(expanded)

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

        #self.kernel._memoryManager.freeFrames(pages)


class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        programName, programCode, priority = irq.parameters
        priority = 4 if priority > 4 or priority < 0 else priority
        log.logger.info("New loading {} {}".format(programName, priority))
        pages, limit = self.kernel.loader.create(programName)
        pcb = ProcessControlBlock(programName, priority, pages, limit)
        pcb.state = State.snew
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

class PageFaultInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        #(4)
        pageId = irq.parameters
        pcb = self.kernel.pcbTable.runningPCB
        hasFrame, frameId = self.kernel._memoryManager.allocFrame()
        #print("Frame allocated:", frameId, "hasFrame:", hasFrame,"for Page:", pageId)
        if hasFrame:
            self.kernel.loader.loadPage(pcb.path, pageId, frameId)
            #print(HARDWARE.memory)
        else:
            print("FATAL ERROR No Frames to alloc", pageId)
            raise Exception("\n*\n* FATAL ERROR No Frames to alloc\n*\n")

        return frameId

#emul dispacher
class Dispacher():
    def __init__(self, kernel):
        self._kernel = kernel

    def load(self, pcb):
        HARDWARE.cpu.context = pcb.context #all reg in a big tuple
        HARDWARE.mmu.limit = pcb.limit
        HARDWARE.mmu.resetTLB()
        # pasamos las paginas del pid q estan en MM al mmu
        pages = self._kernel.memoryManager.getPageTable(pcb.pid)
        for pageId in range(0, len(pages)):
            HARDWARE.mmu.setPageFrame(pageId, pages[pageId])
        HARDWARE.timer.reset()

    def save(self, pcb):
        #En el pcb las paginas son una lista
        #En el tlb las paginas estan mapeadas  pagina/Page(framestate)
        #En el MM  las paginas estab mapeadas  pid/Pages (todas)
        #Debemos pasar las paginas del mmu.tlb a la MM.pageTable
        pcb.pages = list(HARDWARE.mmu.tlb.values())
        self._kernel.memoryManager.putPageTable(pcb.pid, pcb.pages)
        pcb.context = HARDWARE.cpu.context # all regs in a big tuple
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

    def __init__(self, programName, priority, pages = [], limit = 0):
        self._pid = pid.new()
        self._limit = limit
        self._pc  = 0 # TODO check if keep that
        self._state =State.snew
        # well knew cpu reset state
        self._context = (0, 0, 0, -1, True) # keep sync with hardware#330
        self._path = programName
        self._priority = priority
        self._pages = pages

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
    def limit(self):
        return self._limit

    @limit.setter
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
        return "PCB: path:{:<8} pid:{:>3} prio:{:>2} pc:{:>3} limit:{:>3} state: {} pages: {}\n".format(
                self._path, self._pid, self._priority, self._pc, self._limit, self._state, self._pages)

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

    # denota una lista con Page()s vacios y el limite o largo del prog -1
    def create(self, path):
        programCode = self._fs.read(path)
        programSize = len(programCode.instructions)
        #print("###", programSize, programCode.instructions)
        pagesToCreate = programSize // self._mm._frameSize
        pagesToCreate += 1 if programSize % self._mm._frameSize >= 1 else 0
        # limit = programSize - 1
        return [Page() for x in range(0, pagesToCreate)], programSize - 1

    """
    # Load a page from disk, fs or (...swap ?)
    # we got a frame where to write the page that
    # we load from path (or...)
    # frameId : int
    """
    def loadPage(self, path, pageId, frameId):
        programCode = self._fs.read(path)
        progSize  = len(programCode.instructions)
        seekFrom  = pageId * self._mm._frameSize
        seekTo    = seekFrom + self._mm._frameSize
        pageOfCode = programCode.instructions[seekFrom: seekTo]

        physicalAddress = frameId * self._mm._frameSize

        for instruction in pageOfCode:
            self._mm.memory.put(physicalAddress, instruction)
            physicalAddress += 1

        #print("At load Page:\n", "programCode", programCode, "progSize", progSize, "seekFrom", seekFrom, "seekTo" , seekTo , "pageOfCode", pageOfCode, "physicalAddress", physicalAddress )

    def load(self, path):
        programCode = self._fs.read(path)
        progSize = len(programCode.instructions)
        pages = self._mm.allocFrames(progSize)
        if not pages:
            #print(" SEPARAR LOAD y CREATE" )
            raise Exception("\x9B37;44m\x9B2J\x9B12;18HException: No Hay memoria. [BSOD]... o demandá ;P \x9B14;18H(!!!)\x9B0m")

        for instAddr in range(0, progSize):
            offset = instAddr % self._mm._frameSize
            frameId = pages[instAddr // self._mm._frameSize].frame
            physicalAddress = offset + frameId  * self._mm._frameSize
            inst = programCode.instructions[instAddr]
            self._mm.memory.put(physicalAddress, inst)

        return pages, progSize - 1 # limit = progSize - 1


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
        self._quiet = False
        self._graph = dict()

    def ticks(self):
        return self._ticks

    def tick(self, tickNbr):
        self._ticks += 1
        g = ""
        for (i, pcb)  in self._kernel.pcbTable.table.items():
            if pcb.pid not in self._graph:
                self._graph[pcb.pid] = "{}   {}    {}".format(pcb.pid, pcb.priority, " " * self._ticks)

            case = {State.srunning   : "\x9B7mR\x9B0m",
                    State.sready     : "r",
                    State.swaiting   : "w",
                    State.snew       : "n",
                    State.sterminated: "."}
            self._graph[pcb.pid] += case[pcb.state]

        if not self._quiet:
            log.logger.info("Gantt {} {}\npid prio (R)unning (r)eady (w)aiting".format(self._kernel._scheduler.name, self._ticks))
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

# QQ
class frameDummy: # dummy counter while migrate to demand
    number = -1
    @classmethod
    def new(self):
        self.number += 1
        return self.number

class Page:

    # temporaly assign a frame number instead of None
    def __init__(self):
        self._frame = None # frameDummy.new() # QQ
        self._dirty = False
        self._chance = 0

    def isValid(self):
        return not self._frame == None

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, value):
        self._frame = value

    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, value):
        self._dirty = value

    def __repr__(self):
        return "Page: frame:{} dirty:{} chance:{}\n".format( self._frame, self._dirty, self._chance)


class MemoryManager:

    def __init__(self, memory, frameSize):
        self._memory = memory
        ## keep a list of free framesIds
        ## and a list of used frameIds
        self._freeFrameIds = [x for x in range(0,memory.getLeng() // frameSize)]
        self._usedFrameIds = []
        self._frameSize = frameSize
        self._pageTable = dict()  # {pid : pages} pages list of Page()

    def allocFrame(self): #(3)
        # QQ
        if self._freeFrameIds:
            allocatedFrame = self.allocateFrame()
        else:
            allocatedFrame = self.deallocateFrame()
        return True, allocatedFrame

    def allocateFrame(self): 
        self._usedFrameIds += [self._freeFrameIds.pop()]
        return self._usedFrameIds[-1]

    def deallocateFrame(self):
        # QQ
        self._freeFrameIds += [self._usedFrameIds.pop()]
        return self._freeFrameIds[-1]

    # en Memory Manager

    def freeFrames(self, frames): 
        #print("Freeing: ", frames, "Prev Frees: ", self._freeFrameIds)
        FrameIds = [page.frame for page in frames]
        [(self._usedFrameIds.remove(x), self._freeFrameIds.append(x)) for x in FrameIds]
        #print("Current Frees: ", FrameIds)

    def putPageTable(self, pid, pages):
        self._pageTable.update({pid: pages})

    def getPageTable(self, pid):
        return self._pageTable.get(pid)

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

        pageFaultHandler = PageFaultInterruptionHandler(self)
        self._hardware.interruptVector.register(PAGE_FAULT_INTERRUPTION_TYPE, pageFaultHandler)

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

