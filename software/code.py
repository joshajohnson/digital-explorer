import time
import board
import digitalio
import busio
from rainbowio import colorwheel
import neopixel
from adafruit_lsm6ds.lsm6ds33 import LSM6DS33
from adafruit_mcp230xx.mcp23017 import MCP23017

# UART Init
uart = busio.UART(board.GP0, board.GP1, baudrate=115200)

# Neopixel Init
num_pixels = 3
pixels = neopixel.NeoPixel(board.GP2, num_pixels, brightness=0.3, auto_write=False)

# I2C Bus Init
i2c = busio.I2C(board.GP13, board.GP12)

# LSM6 CONFIGURATION
sensor = LSM6DS33(i2c)

# MCP23017 CONFIGURATION
# Address within range 0x20 - 0x28 depending on A2 A1 A0
mcp = MCP23017(i2c, address=0x20)

mcp_in_0 = mcp.get_pin(0)
mcp_in_0.direction = digitalio.Direction.INPUT
mcp_in_0.pull = digitalio.Pull.UP

mcp_in_1 = mcp.get_pin(1)
mcp_in_1.direction = digitalio.Direction.INPUT
mcp_in_1.pull = digitalio.Pull.UP

mcp_in_2 = mcp.get_pin(2)
mcp_in_2.direction = digitalio.Direction.INPUT
mcp_in_2.pull = digitalio.Pull.UP

mcp_in_3 = mcp.get_pin(3)
mcp_in_3.direction = digitalio.Direction.INPUT
mcp_in_3.pull = digitalio.Pull.UP

mcp_out_0 = mcp.get_pin(8)
mcp_out_0.direction = digitalio.Direction.OUTPUT
mcp_out_0.value = False

mcp_out_1 = mcp.get_pin(9)
mcp_out_1.direction = digitalio.Direction.OUTPUT
mcp_out_0.value = False

mcp_out_2 = mcp.get_pin(10)
mcp_out_2.direction = digitalio.Direction.OUTPUT
mcp_out_0.value = False

mcp_out_3 = mcp.get_pin(11)
mcp_out_3.direction = digitalio.Direction.OUTPUT
mcp_out_0.value = False

# SHIFT REG CONFIGURATION

# 74HC165 shift in pins
si_data = digitalio.DigitalInOut(board.GP11)
si_data.direction = digitalio.Direction.INPUT
si_data.pull = digitalio.Pull.UP

si_clk = digitalio.DigitalInOut(board.GP7)
si_clk.direction = digitalio.Direction.OUTPUT
si_clk.value = False

si_nlatch = digitalio.DigitalInOut(board.GP6)
si_nlatch.direction = digitalio.Direction.OUTPUT
si_nlatch.value = True

# 74HC595 shift out pins
so_data = digitalio.DigitalInOut(board.GP8)
so_data.direction = digitalio.Direction.OUTPUT
so_data.value = False

so_clk = digitalio.DigitalInOut(board.GP10)
so_clk.direction = digitalio.Direction.OUTPUT
so_clk.value = False

so_nlatch = digitalio.DigitalInOut(board.GP9)
so_nlatch.direction = digitalio.Direction.OUTPUT
so_nlatch.value = True

# FUNCTION DEFINITIONS

# Shift out 8 bit field to 595 shift register
def shift_out(bitfield):
    # Chip enable low to begin transaction
    so_nlatch.value = False

    # For each bit in the bitfield
    for i in range(0, 8):
        # Set clock low
        so_clk.value = False

        # Check if bit is set and set data high / low accordingly
        if bitfield & (1 << i):
            so_data.value = True
        else:
            so_data.value = False
        
        # Clock going high shift the above set data in
        so_clk.value = True

        # Return data to zero value (not required, but easier for timing)
        so_data.value = False

    # Ensure clock is low when transaction finished
    so_clk.value = False
    # Chif enable high now transaction is done
    so_nlatch.value = True

# Shift in 8 bits from 165 shift register
def shift_in():
    # Var to store read value in
    readback = 0

    # Set chip select high to begin read
    # Normally chip select is active low, but it's not this time
    # I know the name is wrong, but I'm keeping it identical to the schematic / PCB
    si_nlatch.value = True

    # For the 8 inputs on the shift register, read them into the temp var
    for i in range(0, 8):
        # Clock going high triggers shift out of next value
        si_clk.value = True

        # Bitwise or with 0 will set value if set on shift reg
        readback |= (si_data.value) << (7-i)
        
        # Clock low so we can bring it high next time
        si_clk.value = False

    # Transaction over, return chip select to default state
    si_nlatch.value = False

    # Bitshifting to align values to MSB and invert as DIP switch is active low
    return (readback << 3) ^ 0xFF


# Cycling rainbow on all LEDs
def rainbow_cycle():
    for j in range(255):
        for i in range(num_pixels):
            rc_index = (i * 256 // num_pixels) + j
            pixels[i] = colorwheel(rc_index & 255)
        pixels.show()
        time.sleep(0.005)

# DEMO TIME!
# For more info, please reads the docs: https://joshajohnson.com/digital-explorer-board/
while True:

    # SHIFT REGISTER DIP SWITCH
    # Read in the DIP switch values
    sr_dip_val = shift_in()
    # Write values out to LEDs
    shift_out(sr_dip_val)
    # Print info to user for debug
    # print("Shift Reg Value: {:04b}".format(sr_dip_val >> 4))

    # I2C SCANNER
    # while not i2c.try_lock():
    #     pass
    # try:
    #     print(
    #         "I2C addresses found:",
    #         [hex(device_address) for device_address in i2c.scan()],
    #     )
    # finally:  # unlock the i2c bus when ctrl-c'ing out of the loop
    #     i2c.unlock()


    # MCP I2C IO EXPANDER
    # Read input DIP switch, and write out inverted value to LED (switch is active low)
    mcp_out_0.value = not mcp_in_0.value
    mcp_out_1.value = not mcp_in_1.value
    mcp_out_2.value = not mcp_in_2.value
    mcp_out_3.value = not mcp_in_3.value

    # UART TRANSMIT 
    uart.write(bytes("Hello World!", "ascii"))

    # I2C ACCEL
    print("Acceleration: X:%.2f, Y: %.2f, Z: %.2f m/s^2" % (sensor.acceleration))
    # print("Gyro X:%.2f, Y: %.2f, Z: %.2f radians/s" % (sensor.gyro))
    # print("")

    # WS2812 "NEOPIXEL" DEMO
    # Cycle though rainbow colours on LEDs
    # This is a blocking function that takes approx 1.4s to finish
    # Comment out if you want everything else to run fast!
    rainbow_cycle()

    # If you comment out rainbow_cycle(), you may want to add in a delay such as below
    # time.sleep(0.1) # Sleep time in seconds (i.e. 100ms delay for each loop)
    