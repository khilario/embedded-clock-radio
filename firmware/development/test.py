from machine import Pin, I2C, SPI
import time
from rotary_irq_rp2 import RotaryIRQ
from machine import RTC
from ssd1306 import SSD1306_SPI

class Radio:
    
    def __init__( self, NewFrequency, NewVolume, NewMute ):

#
# set the initial values of the radio
#
        self.Volume = 2
        self.Frequency = 88
        self.Mute = False
#
# Update the values with the ones passed in the initialization code
#
        self.SetVolume( NewVolume )
        self.SetFrequency( NewFrequency )
        self.SetMute( NewMute )
        
        
# Initialize I/O pins associated with the radio's I2C interface

        self.i2c_sda = Pin(26)
        self.i2c_scl = Pin(27)

#
# I2C Device ID can be 0 or 1. It must match the wiring. 
#
# The radio is connected to device number 1 of the I2C device
#
        self.i2c_device = 1 
        self.i2c_device_address = 0x10

#
# Array used to configure the radio
#
        self.Settings = bytearray( 8 )


        self.radio_i2c = I2C( self.i2c_device, scl=self.i2c_scl, sda=self.i2c_sda, freq=200000)
        self.ProgramRadio()

    def SetVolume( self, NewVolume ):
#
# Conver t the string into a integer
#
        try:
            NewVolume = int( NewVolume )
            
        except:
            return( False )
        
#
# Validate the type and range check the volume
#
        if ( not isinstance( NewVolume, int )):
            return( False )
        
        if (( NewVolume < 0 ) or ( NewVolume >= 16 )):
            return( False )

        self.Volume = NewVolume
        return( True )



    def SetFrequency( self, NewFrequency ):
#
# Convert the string into a floating point value
#
        try:
            NewFrequency = float( NewFrequency )
            
        except:
            return( False )
#
# validate the type and range check the frequency
#
        if ( not ( isinstance( NewFrequency, float ))):
            return( False )
    
        if (( NewFrequency < 88.0 ) or ( NewFrequency > 108.0 )):
            return( False )

        self.Frequency = NewFrequency
        return( True )
        
    def SetMute( self, NewMute ):
        
        try:
            self.Mute = bool( int( NewMute ))
            
        except:
            return( False )
        
        return( True )

#
# convert the frequency to 10 bit value for the radio chip
#
    def ComputeChannelSetting( self, Frequency ):
        Frequency = int( Frequency * 10 ) - 870
        
        ByteCode = bytearray( 2 )
#
# split the 10 bits into 2 bytes
#
        ByteCode[0] = ( Frequency >> 2 ) & 0xFF
        ByteCode[1] = (( Frequency & 0x03 ) << 6 ) & 0xC0
        return( ByteCode )

#
# Configure the settings array with the mute, frequency and volume settings
#
    def UpdateSettings( self ):
        
        if ( self.Mute ):
            self.Settings[0] = 0x80
        else:
            self.Settings[0] = 0xC0
    
        self.Settings[1] = 0x09 | 0x04
        self.Settings[2:3] = self.ComputeChannelSetting( self.Frequency )
        self.Settings[3] = self.Settings[3] | 0x10
        self.Settings[4] = 0x04
        self.Settings[5] = 0x00
        self.Settings[6] = 0x84
        self.Settings[7] = 0x80 + self.Volume

#        
# Update the settings array and transmitt it to the radio
#
    def ProgramRadio( self ):

        self.UpdateSettings()
        self.radio_i2c.writeto( self.i2c_device_address, self.Settings )
        time.sleep_ms(50)


#
# Extract the settings from the radio registers
#
    def GetSettings( self ):
#        
# Need to read the entire register space. This is allow access to the mute and volume settings
# After and address of 255 the 
#
        self.RadioStatus = self.radio_i2c.readfrom( self.i2c_device_address, 256 )

        if (( self.RadioStatus[0xF0] & 0x40 ) != 0x00 ):
            MuteStatus = False
        else:
            MuteStatus = True
            
        VolumeStatus = self.RadioStatus[0xF7] & 0x0F
    
    #
    # Convert the frequency 10 bit count into actual frequency in Mhz
    #
        FrequencyStatus = (( self.RadioStatus[0x00] & 0x03 ) << 8 ) | ( self.RadioStatus[0x01] & 0xFF )
        FrequencyStatus = ( FrequencyStatus * 0.1 ) + 87.0
        
        if (( self.RadioStatus[0x00] & 0x04 ) != 0x00 ):
            StereoStatus = True
        else:
            StereoStatus = False
        
        return( MuteStatus, VolumeStatus, FrequencyStatus, StereoStatus )

#
# initialize the FM radio
#
fm_radio = Radio( 107.3, 2, False )

# === Initialize Buttons ===
button_sw1 = Pin(0, Pin.IN, Pin.PULL_DOWN)  # Rotary Encoder Switch 1
button_sw2 = Pin(3, Pin.IN, Pin.PULL_DOWN)  # Left Button
button_sw3 = Pin(7, Pin.IN, Pin.PULL_DOWN)  # Right Button
button_sw4 = Pin(13, Pin.IN, Pin.PULL_DOWN)  # Rotary Encoder Switch 2

#Rotary Encoders
# Initialize the rotary encoder
# pin_num_dt: Data pin, pin_num_clk: Clock pin
# min_val, max_val: Set a range if needed, otherwise use RANGE_UNBOUNDED
# reverse: Set to True if rotation direction is inverted

# === Initialize Rotary Encoders ===
rotary1 = RotaryIRQ(pin_num_dt=1, pin_num_clk=2,
                    min_val=0, max_val=16.0, reverse=False,
                    range_mode=RotaryIRQ.RANGE_WRAP,
                    pull_up=True)

# Set up rotary2 for frequency selection: 0 to 99 steps (for 88.1 to 107.9)
rotary2 = RotaryIRQ(pin_num_dt=14, pin_num_clk=15,
                    min_val=1, max_val=99, reverse=False,
                    range_mode=RotaryIRQ.RANGE_WRAP,
                    pull_up=True)

r1_old = rotary1.value()
r2_old = rotary2.value()

# FSM for button checking
prevButton = 0
curButton = 0

# Time settings
current_hour = 12
current_minute = 0
is_24_hour_format = True

# Alarm variables
alarm_hour = None
alarm_minute = None
alarm_enabled = False
alarm_triggered = False

rtc = RTC()
# Set the RTC to your initial time (only once, or when user sets time)
rtc.datetime((2025, 7, 17, 0, 12, 0, 0, 0))  # (year, month, day, weekday, hour, minute, second, microsecond)

#OLED setup
# OLED display resolution
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64

# OLED pin setup
spi_sck = Pin(18)
spi_sda = Pin(19)
spi_res = Pin(21)
spi_dc  = Pin(20)
spi_cs  = Pin(17)

SPI_DEVICE = 0

# Initialize SPI and OLED
oled_spi = SPI(SPI_DEVICE, baudrate=100000, sck=spi_sck, mosi=spi_sda)
oled = SSD1306_SPI(SCREEN_WIDTH, SCREEN_HEIGHT, oled_spi, spi_dc, spi_res, spi_cs, True)

last_tick = time.ticks_ms()

while True:  # <-- Add this outer loop
    last_tick = time.ticks_ms()
    select = None

    # --- Main menu display and button wait ---
    while True:
        # === 1. Update time display every second ===
        if time.ticks_diff(time.ticks_ms(), last_tick) >= 1000:
            now = rtc.datetime()
            current_hour = now[4]
            current_minute = now[5]
            current_second = now[6]

            time_str = "%02d:%02d:%02d" % (current_hour, current_minute, current_second)

            oled.fill(0)
            oled.text("ECE 299 Clock", 10, 0)
            oled.text("Time:", 10, 20)
            oled.text(time_str, 10, 35)
            oled.rect(0, 50, 128, 5, 1)
            oled.show()

            print("Current time:", time_str)
            print("")
            print("ECE 299 FM Radio Demo Menu")
            print("Press SW1 for: change volume level")
            print("Press SW2 for: change between 12/24hr time")
            print("Press SW3 for: set alarm")
            print("Press SW4 for: change radio frequency")
            print("")

            # Alarm trigger check
            if alarm_enabled and not alarm_triggered:
                if current_hour == alarm_hour and current_minute == alarm_minute:
                    print("Alarm! Turning radio on at max volume.")
                    fm_radio.SetMute(False)
                    fm_radio.SetVolume(15)
                    fm_radio.ProgramRadio()
                    alarm_triggered = True

            last_tick = time.ticks_ms()

        if button_sw1.value():
            select = "1"
            break
        elif button_sw2.value():
            select = "2"
            break
        elif button_sw3.value():
            select = "3"
            break
        elif button_sw4.value():
            select = "4"
            break
        time.sleep_ms(50)

    # Debounce: wait for button release
    while (button_sw1.value() == 1 or button_sw2.value() == 1 or
           button_sw3.value() == 1 or button_sw4.value() == 1):
        time.sleep(0.05)

    # --- Menu selection handling ---
    if select == "1":
#
# Set volume level of radio
#
        print("Rotate rotary1 to change volume.")
        print("Press Button SW1 (Pin 0) to return to menu.")
        val_old = rotary1.value()
        
        while True:
            val_new = rotary1.value()
            
            if val_new != val_old:
                val_old = val_new
                print("Volume:", val_new)
                if fm_radio.SetVolume(val_new):
                    fm_radio.ProgramRadio()
                time.sleep_ms(100)

            # --- OLED live update for volume ---
            oled.fill(0)
            oled.text("Set Volume", 10, 0)
            oled.text("Volume: %d" % val_old, 10, 20)
            oled.text("SW1: Confirm", 10, 40)
            oled.show()
            # -----------------------------------

            # Check for button press to return to menu
            if button_sw1.value() == 1:
                print("Returning to menu...")
                time.sleep(0.5)  # debounce delay
                break

#        
# Set time and change between 12hr/24hr time     
#        
    elif( select == "2" ):
        print("Set Time Mode")
        print("Rotary1: Set hour")
        print("Rotary2: Set minute")
        print("Press SW2 to confirm and return to menu.")
        print("Press SW3 to toggle 12/24 hour format.")

        am_pm = "AM"
        if not is_24_hour_format and current_hour >= 12:
            am_pm = "PM"

        # Set hour limits depending on format
        if is_24_hour_format:
            rotary1.set(min_val=0, max_val=23, value=current_hour)
        else:
            # 12-hour mode: 1-12, track AM/PM
            hour_12 = current_hour % 12
            if hour_12 == 0:
                hour_12 = 12
            rotary1.set(min_val=1, max_val=12, value=hour_12)
            am_pm = "AM" if current_hour < 12 else "PM"

        rotary2.set(min_val=0, max_val=59, value=current_minute)

        hour = rotary1.value()
        minute = rotary2.value()
        am_pm_state = am_pm

        def print_time(hour, minute, is_24, am_pm):
            if is_24:
                print("Hour: %02d, Minute: %02d (24h)" % (hour, minute))
            else:
                print("Hour: %02d, Minute: %02d %s (12h)" % (hour, minute, am_pm))

        print_time(hour, minute, is_24_hour_format, am_pm_state)

        while True:
            new_hour = rotary1.value()
            new_minute = rotary2.value()

            # Toggle 12/24 hour format with SW4
            if button_sw4.value() == 1:
                is_24_hour_format = not is_24_hour_format
                if is_24_hour_format:
                    # Convert to 24-hour
                    if am_pm_state == "PM" and hour != 12:
                        current_hour = hour + 12
                    elif am_pm_state == "AM" and hour == 12:
                        current_hour = 0
                    else:
                        current_hour = hour
                    rotary1.set(min_val=0, max_val=23, value=current_hour)
                else:
                    # Convert to 12-hour
                    if current_hour == 0:
                        hour_12 = 12
                        am_pm_state = "AM"
                    elif current_hour > 12:
                        hour_12 = current_hour - 12
                        am_pm_state = "PM"
                    elif current_hour == 12:
                        hour_12 = 12
                        am_pm_state = "PM"
                    else:
                        hour_12 = current_hour
                        am_pm_state = "AM"
                    rotary1.set(min_val=1, max_val=12, value=hour_12)
                hour = rotary1.value()
                print("Toggled time format.")
                print_time(hour, minute, is_24_hour_format, am_pm_state)
                time.sleep(0.5)  # debounce

            # Toggle AM/PM in 12-hour mode with SW1
            if not is_24_hour_format and button_sw3.value() == 1:
                am_pm_state = "PM" if am_pm_state == "AM" else "AM"
                print_time(hour, minute, is_24_hour_format, am_pm_state)
                time.sleep(0.5)  # debounce

            if new_hour != hour or new_minute != minute:
                hour = new_hour
                minute = new_minute
                print_time(hour, minute, is_24_hour_format, am_pm_state)
                time.sleep_ms(100)

            if button_sw2.value() == 1:
                # Save time
                if is_24_hour_format:
                    set_hour = hour
                else:
                    # Convert 12h to 24h
                    if am_pm_state == "AM":
                        set_hour = hour if hour != 12 else 0
                    else:
                        set_hour = hour if hour == 12 else hour + 12
                set_minute = minute

                # Get current date to preserve it
                y, m, d, wd, _, _, _, _ = rtc.datetime()
                rtc.datetime((y, m, d, wd, set_hour, set_minute, 0, 0))
                print("Time set to %02d:%02d %s" % (
                    hour if not is_24_hour_format else set_hour,
                    set_minute,
                    "" if is_24_hour_format else am_pm_state
                ))
                time.sleep(0.5)
                break

        # Restore rotary1 and rotary2 to original volume/freq range
        rotary1.set(min_val=0, max_val=15)
        rotary2.set(min_val=0, max_val=99)

#
# Set alarm
#
    elif( select == "3" ):
        print("Set Alarm Mode")
        print("Rotary1: Set alarm hour")
        print("Rotary2: Set alarm minute")
        print("Press SW4 to confirm and return to menu.")

        # Set up rotary ranges for alarm setting
        rotary1.set(min_val=0, max_val=23, value=current_hour)
        rotary2.set(min_val=0, max_val=59, value=current_minute)

        alarm_set_hour = rotary1.value()
        alarm_set_minute = rotary2.value()

        def print_alarm_time(hour, minute):
            print("Alarm set for %02d:%02d" % (hour, minute))

        print_alarm_time(alarm_set_hour, alarm_set_minute)

        while True:
            new_alarm_hour = rotary1.value()
            new_alarm_minute = rotary2.value()
            if new_alarm_hour != alarm_set_hour or new_alarm_minute != alarm_set_minute:
                alarm_set_hour = new_alarm_hour
                alarm_set_minute = new_alarm_minute
                print_alarm_time(alarm_set_hour, alarm_set_minute)
                time.sleep_ms(100)

            # --- OLED live update for alarm time ---
            oled.fill(0)
            oled.text("Set Alarm", 10, 0)
            alarm_str = "Alarm: %02d:%02d" % (alarm_set_hour, alarm_set_minute)
            oled.text(alarm_str, 10, 20)
            oled.text("SW4: Confirm", 10, 40)
            oled.show()
            # --------------------------------------

            # Confirm alarm with SW4
            if button_sw4.value() == 1:
                alarm_hour = alarm_set_hour
                alarm_minute = alarm_set_minute
                alarm_enabled = True
                alarm_triggered = False
                print("Alarm set for %02d:%02d" % (alarm_hour, alarm_minute))
                time.sleep(0.5)
                break

        # Restore rotary1 and rotary2 to original volume/freq range
        rotary1.set(min_val=0, max_val=15)
        rotary2.set(min_val=0, max_val=99)
    
#
# Set radio frequency
#
    elif ( select == "4" ):
        print("Rotate rotary2 to change frequency (88.1 - 107.9 MHz, odd tenths only).")
        print("Press Button SW4 to return to menu.")
        val_old = rotary2.value()
        freq_old = max(88.0, min(108.0, 88.1 + val_old * 0.2))
        fm_radio.SetFrequency(freq_old)
        fm_radio.ProgramRadio()
        print("Frequency:", "%.1f" % freq_old)

        while True:
            val_new = rotary2.value()
            if val_new != val_old:
                val_old = val_new
                freq_new = 88.1 + val_new * 0.2
                print("Frequency:", "%.1f" % freq_new)
                if fm_radio.SetFrequency(freq_new):
                    fm_radio.ProgramRadio()
                time.sleep_ms(100)

            # --- OLED live update for frequency ---
            oled.fill(0)
            oled.text("Set Frequency", 10, 0)
            oled.text("Freq: %.1f MHz" % (88.1 + val_old * 0.2), 10, 20)
            oled.text("SW4: Confirm", 10, 40)
            oled.show()
            # --------------------------------------

            # Check for button press to return to menu
            if button_sw4.value() == 1:
                print("Returning to menu...")
                time.sleep(0.5)  # debounce delay
                break


    else:
        print( "Invalid menu option" )


