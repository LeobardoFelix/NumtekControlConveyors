import time
import threading
from opcua import Client
import queue
from config import settings
UPDATE_TIME = 5
INPUT_INDEX_MACHINE_READY = 0
INPUT_INDEX_PROGRAM_RUNNING = 1
INPUT_INDEX_PROGRAM_PAUSED = 2
INPUT_INDEX_PROGRAM_IDLE = 3
INPUT_INDEX_PROGRAM_LOADED = 4
INPUT_INDEX_MACHINE_ON = 5
INPUT_INDEX_HOME_ALL = 6
INPUT_INDEX_CONVA_OK = 7
INPUT_INDEX_CONVB_OK = 8
INPUT_INDEX_CONVC_OK = 7
INPUT_INDEX_CONVD_OK = 8
INPUT_INDEX_CONVA_TAKEN = 9
INPUT_INDEX_CONVA_LEFT = 10
INPUT_INDEX_CONVB_TAKEN = 11
INPUT_INDEX_CONVB_LEFT = 12
INPUT_INDEX_CONVC_TAKEN = 9
INPUT_INDEX_CONVC_LEFT = 10
INPUT_INDEX_CONVD_TAKEN = 11
INPUT_INDEX_CONVD_LEFT = 12
INPUT_INDEX_CONVB_R2_TAKEN = 13
INPUT_INDEX_CONVB_R2_LEFT = 14
FLOAT_INDEX_HANGERA = 0
FLOAT_INDEX_HANGERB = 1
FLOAT_INDEX_HANGERC = 0
FLOAT_INDEX_HANGERD = 1
OUTPUT_INDEX_CONVA_PULSE = 0
OUTPUT_INDEX_CONVB_PULSE = 1
OUTPUT_INDEX_CONVC_PULSE = 0
OUTPUT_INDEX_CONVD_PULSE = 1
OUTPUT_INDEX_CONVA_TAKEN = 2
OUTPUT_INDEX_CONVB_TAKEN = 4
OUTPUT_INDEX_CONVC_TAKEN = 2
OUTPUT_INDEX_CONVD_TAKEN = 4
OUTPUT_INDEX_CONVA_LEFT = 3
OUTPUT_INDEX_CONVB_LEFT = 5
OUTPUT_INDEX_CONVC_LEFT = 3
OUTPUT_INDEX_CONVD_LEFT = 5
OUTPUT_INDEX_R2_CONVB_TAKEN = 6
OUTPUT_INDEX_R2_CONVB_LEFT = 7


class Robot:
    def __init__(self, ip, port, name, simulation=False):
        self.ip = ip
        self.port = port
        self.name = name
        self.simulation = simulation
        self._thread_started = False
        self.client = None
        self.connected = False
        self.robot = None

        self.inputs = []
        self.outputs = []
        self.floats = []
        self.floatInputs = []
        self.floatOutputs = []
        self.booleanOutputs = []
        self.hanger_pos_ok = []

        self.heartbeat = None
        self.last_hb = None
        self.timeout_counter = 0

        self.lock = threading.Lock()
        self.write_queue = queue.Queue()

        self.reader_values = [False]*16
        self.reader_float = [0.0]*8
        self.writer_float = [0.0]*8

        # -------- LinuxCNC Status Flags --------
        self.machine_ready= False
        self.program_running = False
        self.program_paused = False
        self.program_idle = False
        self.program_loaded = False
        self.machine_on = False
        self.home_all = False
        self.alarm = False
        self.hangerA = 0
        self.hangerB = 0
        self.hangerC = 0
        self.hangerD = 0
        self.convAOk = False
        self.convBOk = False
        self.convCOk = False
        self.convDOk = False
        self.takenConvA = 0
        self.leftConvA = 0
        self.takenConvB =0
        self.leftConvB = 0
        self.takenConvC = 0
        self.leftConvC = 0
        self.takenConvD =0
        self.leftConvD = 0


    def connect(self):

        try:
            if self.client is None:
                self.client = Client(f"opc.tcp://{self.ip}:{self.port}")
                self.client.session_timeout = 100

            # Try a lightweight operation to confirm connection
            if not self.connected:
                self.client.connect()

            obj = self.client.get_objects_node()
            self.robot = obj.get_child([f"2:{self.name}"])
            self.classify()

            self.connected = True

        except Exception as e:
            self.connected = False
            print(f"ERROR ROBOT {self.name}: {e}")

    def classify(self):
        self._browse(self.robot)

    def _browse(self, node):
        self.inputs = []
        self.outputs = []
        self.floats = []
        self.floatInputs = []
        self.floatOutputs = []
        self.booleanOutputs = []
        for child in node.get_children():
            try:
                name = child.get_browse_name().Name.lower()
            except:
                name = ""

            try:
                value = child.get_value()
                dtype = type(value)

                # ---- Classification ----
                if "heartbeat" in name:
                    self.heartbeat = child

                if "floatoutput" in name:
                    self.floatOutputs.append(child)
                elif "floatinput" in name:
                    self.floatInputs.append(child)
                elif "output" in name:
                    self.outputs.append(child)
                elif "input" in name:
                    self.inputs.append(child)
                #else:
                #    print(f"{self.name}: No es output o input {name} {value}")
                

                # Debug print
                #print(f"{name} | {child.nodeid} | {value} | {dtype}")

            except:
                # Not a variable node → keep browsing
                self._browse(child)


    
    def start_connection_loop(self):
        if getattr(self, "_thread_started", False) and getattr(self, "robot_connection_thread") and self.robot_connection_thread.is_alive():
            return  # already started
        self._thread_started = True
        self.robot_connection_thread = threading.Thread(target=self.robot_connection_loop, daemon=True)
        self.robot_connection_thread.start()

    def robot_connection_loop(self):
        self.isListening = True

        while self.isListening:
            if not self.connected:
                try:
                    self.connect()
                except:
                    time.sleep(1)
                    continue

            if self.connected:
                try:
                    # Only fetch the values, NOT the nodes
                    with self.lock:
                        self.classify()
                        self.reader_values = [inp.get_value() for inp in self.inputs]
                        self.write_values = [inp.get_value() for inp in self.outputs]
                        self.float_values = [fl.get_value() for fl in self.floats]
                        self.reader_float = [fl.get_value() for fl in self.floatInputs]
                        self.writer_float = [fl.get_value() for fl in self.floatOutputs]
                    # Update robot status flags
                    self._update_status_flags()
                    # if self.name == "Robot2":
                    #     print(f"NAME: {self.name} : CONV C: {self.convCOk}")
                    #     print(f"NAME: {self.name} : CONV D: {self.convDOk}")

                except Exception as e:
                    self.connected = False
                    print(f"{self.name}: Connection loop error {e}")
                    try:
                        self.client.disconnect()
                    except:
                        pass

            time.sleep(UPDATE_TIME)

    def stopListening(self):
        if self.client and not self.simulation:
            self.client.disconnect()
        self.isListening = False

    def joinListeningThread(self):
        if hasattr(self, "robot_connection_thread") and self.robot_connection_thread.is_alive():
            self.robot_connection_thread.join()
        print("robot_connection_thread Cycle stopped and thread finished")
        


    # -----------------------------------------
    # Decode machine states
    # -----------------------------------------
    def _update_status_flags(self):

        v = self.reader_values
        if len(v) >= 8:

            self.machine_ready = v[0]
            self.program_running = v[1]
            self.program_paused = v[2]
            self.program_idle = v[3]
            self.program_loaded = v[4]
            self.machine_on = v[5]
            self.home_all = v[6]
            self.hanger_pos_ok = [v[7], v[8]]
            if self.name == "Robot1":
                self.convAOk = v[7]
                self.convBOk = v[8] 
                self.takenConvA = v[9]
                self.leftConvA = v[10]
                self.takenConvB = v[11]
                self.leftConvB = v[12]
                self.hangerA = self.reader_float[0]
                self.hangerB = self.reader_float[2]
            else:
                self.convCOk = v[7]
                self.convDOk = v[8]
                self.takenConvC = v[9]
                self.leftConvC = v[10]
                self.takenConvD = v[11]
                self.leftConvD = v[12]
                self.takenConvB = v[13]
                self.leftConvB = v[14]
                self.hangerC = self.reader_float[0]
                self.hangerD = self.reader_float[2]


    # -----------------------------------------
    # Write outputs
    # -----------------------------------------
    def set_output(self, index, value):
        self.write_queue.put((index, value))


    def set_outputs_batch(self, indices_values):

        for idx, val in indices_values:
            self.write_queue.put((idx, val))


    # -----------------------------------------
    # Debug helper
    # -----------------------------------------
    def print_status(self):

        print(f"\n{self.name} STATUS")
        print("--------------------")
        print("Machine Ready:", self.machine_ready)
        print("Program running:", self.program_running)
        print("Program paused:", self.program_paused)
        print("Program idle:", self.program_idle)
        print("Program Loaded:", self.program_loaded)
        print("Machine On:", self.machine_on)
        print("Home All:", self.home_all)
        #print("Alarm:", self.alarm)

    def set_float_output(self, index, value):
        """
        Set a floating-point output value.

        index: position in self.floatOutputs
        value: float value to send
        """
        #if not self.connected:
        #    print("Robot not connected")
        #    return
        try:
            with self.lock:
                self.floatOutputs[index].set_value(float(value))
                

        except Exception as e:
            print(f"{self.name}: Error setting float output {index}: {e}")
            self.connected = False

    def set_bool_output(self, index, value):
        """
        Set a floating-point output value.

        index: position in self.outputs
        value: boolean value to send
        0 is for conveyor A or C
        1 is for conveyor B or D
        """
        try:
            with self.lock:
                self.outputs[index].set_value(float(value))

        except Exception as e:
            print(f"{self.name}: Error setting boolean output {index}: {e}")
            self.connected = False

    def shut_down_all_outputs(self):
        try:
            with self.lock:
                for output in self.outputs:
                    output.set_value(0)
        except Exception as e:
            print(f"{self.name}: Error shutting down all signals {e}")
            self.connected = False