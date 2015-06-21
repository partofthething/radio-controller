'''
Beginnings of a remote controller for the IC-7100 ham radio

Started by Nick Touran
'''
import time
import serial
import logging

logging.basicConfig(level=logging.DEBUG)

class Radio():
    """
    The radio state.

    This is the Model in the Model-Controller-Viewer pattern
    It represents the current settings/etc. of the radio
    as best as it is known. It can be viewed by a viewer.

    The state should be changed by the Controller.
    """
    def __init__(self):
        self.frequency = 146.960
        self.mode = 'VHF'
        self.memory_num = 1
        self.memory_bank = 1
        self.transmitting = False
        self.power_frac = 0.05
        self.data_mode = True
        self.swr_meter = 0
        self.signal_meter = 0
        self.external_speaker_active = True
        self.backlight_frac = 0.3



class Connection():
    """
    A serial connection between this program and the radio

    Sends/receives commands
    """
    BAUD = 9600
    PORT = "/dev/ttyUSB0"
    def __init__(self):
        pass

    def connect(self):
        self._port = serial.Serial(port=self.PORT, baudrate=self.BAUD, timeout=0.1)

    def disconnect(self):
        self._port.close()

    def send_cmd(self, cmd):

        logging.info('Sending {0} to radio'.format(' '.join([hex(b) for b in cmd])))
        self._port.write(''.join([chr(i) for i in cmd]))

        response = []
        for i in range(500):  # big number to avoid potential infinite loop
            char = self._port.read(1)
            if not char:
                break
            newbyte = ord(char)
            response.append(newbyte)
            if newbyte == 0xFD:
                break

        logging.info('Radio returned: {0}'.format(' '.join([hex(c) for c in response])))
        return response

class Controller():
    """
    a controller that modifies the state of the radio
    """
    def __init__(self, radio=None):
        self.connection = Connection()
        self.connection.connect()
        self.radio = radio or Radio()

    def turn_on(self):
        """
        attempt to turn on radio.

        Send command 13 times at 9600 baud

        FE * 7 + FE FE 88 E0 18 01 FD
        """
        repeatedFEs = {19200:25, 9600:13, 4800:7, 1200:3, 300:2}
        on_cmd_pre = [0xFE] * repeatedFEs[self.connection.BAUD]
        on_cmd = Command()
        on_cmd.set_num(0x18)
        on_cmd.set_subcmd_num(0x01)

        self.connection.send_cmd(on_cmd_pre + on_cmd.render())

    def turn_off(self):

        off_cmd = Command()
        off_cmd.set_num(0x18)
        off_cmd.set_subcmd_num(0x0)
        self.connection.send_cmd(off_cmd.render())

    def goto_mem(self, mem_num):
        if not 1 <= mem_num <= 100:
            raise ValueError('Invalid memory number {0} requested'.format(mem_num))
        cmd = Command()
        cmd.set_num(0x08)
        mem_num_hex = int('0x{0}'.format(mem_num), 0)
        cmd.set_data([mem_num_hex])
        self.connection.send_cmd(cmd.render())

    def select_bank(self, bank_num):
        if not 1 <= bank_num <= 6:
            raise ValueError('Invalid bank number {0} requested'.format(bank_num))
        cmd = Command()
        cmd.set_num(0x08)
        cmd.set_subcmd_num(0xA0)
        bank_num_hex = int('0x{0}'.format(bank_num), 0)
        cmd.set_data([bank_num_hex])
        bank_response = self.connection.send_cmd(cmd.render())

    def rx(self):
        """
        Go to receive mode
        """
        cmd = Command()
        cmd.set_num(0x1C)
        cmd.set_subcmd_num(0x00)
        cmd.set_data([0x00])
        self.connection.send_cmd(cmd.render())

    def tx(self):
        """
        key up! start transmitting
        """
        cmd = Command()
        cmd.set_num(0x1C)
        cmd.set_subcmd_num(0x00)
        cmd.set_data([0x01])
        self.connection.send_cmd(cmd.render())

    def data_mode_on(self):
        cmd = Command()
        cmd.set_num(0x1A)
        cmd.set_subcmd_num(0x06)
        cmd.set_data([0x01, 0x02])  # FIL2
        self.connection.send_cmd(cmd.render())
        self.radio.data_mode = True

    def data_mode_off(self):
        cmd = Command()
        cmd.set_num(0x1A)
        cmd.set_subcmd_num(0x06)
        cmd.set_data([0x00, 0x00])
        self.connection.send_cmd(cmd.render())
        self.radio.data_mode = False


class Command():
    """
    A command to or from the radio
    """
    PREAMBLE = [0xFE, 0xFE]
    TRANSCEIVER_ADDRESS = [0x88]
    CONTROLLER_ADDRESS = [0xE0]
    END_OF_MSG = 0xFD

    def __init__(self):
        self.cmd_num = None
        self.subcmd_num = None
        self.data = None

    def set_num(self, num):
        """
        Set the command number
        """
        self.cmd_num = num

    def set_subcmd_num(self, num):
        self.subcmd_num = num

    def set_data(self, bcd_bytes):
        self.data = bcd_bytes

    def render(self):
        cmd = self.PREAMBLE + self.TRANSCEIVER_ADDRESS + self.CONTROLLER_ADDRESS
        cmd.append(self.cmd_num)

        if self.subcmd_num is not None:
            cmd.append(self.subcmd_num)
        if self.data is not None:
            cmd.extend(self.data)

        cmd.append(self.END_OF_MSG)

        return cmd


class Operator():
    """
    Interacts between user and controller.

    Super basic until we build a GUI.

    Commands are:
        - t for transmit. Press enter to stop transmitting
        - m5 for go to memory number A5.
        - q for quit.
    """

    def operate(self):
        """
        basic loop
        """

        self.controller = Controller()
        self.radio = self.controller.radio
        cmd = ''
        print('Welcome to the basic IC-7100 control program')
        print('q to quit\nt to transmit\nm5 to go to memory 5\n'
              'd - data mode toggle\n\n')
        while cmd != 'q':
            cmd = raw_input('Enter command: ')
            if cmd == 't':
                self.transmit()
            elif cmd.startswith('m'):
                memory_number = int(cmd[1:])
                self.controller.goto_mem(memory_number)
            elif cmd == 'd':
                if self.radio.data_mode:
                    self.controller.data_mode_off()
                else:
                    self.controller.data_mode_on()


    def transmit(self):
        self.controller.tx()
        raw_input('Press enter to end transmission')
        self.controller.rx()



def cmd_from_binary(binary_string):
    """
    build a command from a response from the radio
    """
    cmd = Command()
    if binary_string[:2] != cmd.PREAMBLE:
        raise ValueError('Invalid command preamble in: {0}'.format(binary_string))
    if binary_string[2] != cmd.CONTROLLER_ADDRESS or binary_string[3] != cmd.TRANSCEIVER_ADDRESS:
        raise ValueError('Invalid controller/transceiver addresses: {0}'.format(binary_string[2:4]))

    cmd.cmd_num = binary_string[4]

    # how will we know if there's a subcommand?


if __name__ == '__main__':
    o = Operator()
    o.operate()
    # controller = Controller()
    # controller.turn_on()
    # time.sleep(10)

    # controller.select_bank(1)
    # controller.goto_mem(1)
    # controller.tx()
    # time.sleep(4)
    # controller.rx()

    # controller.turn_off()
    # controller.connection.disconnect()
    # print get_num_bcd(5501)
