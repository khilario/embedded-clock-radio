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
        self.Volume = 1
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
# Convert the string into a integer
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

    def GetRDS(self):
         #Try and pull the RDS data from the radio
        try:
            # Starting at 0x0A read all bits until 0x3A
            raw_data = self.radio_i2c.readfrom(self.i2c_device_address, 32)
        except:
            return ("", "")
        
        # Make the 16 bit blocks for RDSA - D
        blocks = [
            (raw_data[4] << 8) | raw_data[5],   
            (raw_data[6] << 8) | raw_data[7],   
            (raw_data[8] << 8) | raw_data[9],   
            (raw_data[10] << 8) | raw_data[11]  
        ]

        #Find the group type from block 2 which holds
        group_type = (blocks[1] >> 12) & 0xF
        #Find the program service index which tells where to put station name
        program_service_index = blocks[1] & 0x03

        # If the buffers are not initialized, create them
        if not hasattr(self, "rds_station_buf"):
            self.rds_station_buf = [' '] * 8 # Buffer for station name
            self.rds_station_name_list = [False] * 4 #Buffer for index recieved tracking
        if not hasattr(self, "rds_track_name_buf"):
            self.rds_track_name_buf = [' '] * 64 # Buffer for track name
            self.rds_track_name_segments = [False] * 16 # Track if we have a full track name
        
        index_map = {
            0: (0, 1),
            1: (2, 3),
            2: (4, 5),
            3: (6, 7)
        }

        rds_station_name = ""
        # If group type is 0, we are getting the program service name
        if group_type == 0:
            #Block 3 holds station name characters and we will extract one from each index at a time
            station_chars = [(blocks[3] >> 8) & 0xFF, blocks[3] & 0xFF]
            for buf_idx, char_code in zip(index_map[program_service_index], station_chars):
                if 32 <= char_code <= 126:
                    self.rds_station_buf[buf_idx] = chr(char_code)
                else:
                    self.rds_station_buf[buf_idx] = ' '
            self.rds_station_name_list[program_service_index] = True #Mark as seen
            #If we have seen all 4 indices, make the station name
            if all(self.rds_station_name_list):
                rds_station_name = "".join(self.rds_station_buf).strip()
            else:
                rds_station_name = ""

        rds_song_name = ""
        if group_type == 2:
            song_name_index = (blocks[1] & 0x0F) * 4
            chars = [
                (blocks[2] >> 8) & 0xFF,
                blocks[2] & 0xFF,
                (blocks[3] >> 8) & 0xFF,
                blocks[3] & 0xFF
            ]
            for i in range(4):
                # Assemble the song name in the buffer
                if song_name_index + i < 64:
                    char_code = chars[i]
                    if 32 <= char_code <= 126:
                        self.rds_track_name_buf[song_name_index + i] = chr(char_code)
                    else:
                        self.rds_track_name_buf[song_name_index + i] = ' '
            # Only assemble if all segments received:
            if all(self.rds_track_name_segments):
                rds_song_name = "".join(self.rds_track_name_buf).strip()
            else:
                rds_song_name = ""
        else:
            if hasattr(self, "rds_track_name_buf") and self.rds_track_name_segments:
                rds_song_name = "".join(self.rds_track_name_buf).strip()

        return (rds_station_name, rds_song_name)

#
# initialize the FM radio
#
fm_radio = Radio( 101.9, 2, False )

# Initialize Buttons
button_sw1 = Pin(0, Pin.IN, Pin.PULL_DOWN)  # Rotary Encoder Switch 1
button_sw2 = Pin(3, Pin.IN, Pin.PULL_DOWN)  # Left Button
button_sw3 = Pin(7, Pin.IN, Pin.PULL_DOWN)  # Right Button
button_sw4 = Pin(13, Pin.IN, Pin.PULL_DOWN)  # Rotary Encoder Switch 2

#Rotary Encoders
# Initialize the rotary encoder
# pin_num_dt: Data pin, pin_num_clk: Clock pin
# min_val, max_val: Set a range if needed, otherwise use RANGE_UNBOUNDED
# reverse: Set to True if rotation direction is inverted

# Initialize Rotary Encoders
rotary1 = RotaryIRQ(pin_num_dt=1, pin_num_clk=2,
                    min_val=0, max_val=15.0, reverse=False,
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
alarm_snoozed_until = None
alarm_snooze_count = 0

rtc = RTC()
# Set the RTC to your initial time (only once, or when user sets time)
rtc.datetime((2025, 7, 31, 0, 12, 0, 0, 0))  # (year, month, day, weekday, hour, minute, second, microsecond)

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
last_menu_print = time.ticks_ms()

last_station_name = ""
last_freq = fm_radio.Frequency

scroll_index = 0
scroll_last_update = time.ticks_ms()
SCROLL_INTERVAL = 250

while True:
    last_tick = time.ticks_ms()
    select = None

    # Main menu display and button wait
    while True:
        # Update time display every second
        if time.ticks_diff(time.ticks_ms(), last_tick) >= 1000:
            now = rtc.datetime()
            current_hour = now[4]
            current_minute = now[5]
            current_second = now[6]

            # Format time string based on 12/24hr setting
            if is_24_hour_format:
                time_str = "%02d:%02d:%02d" % (current_hour, current_minute, current_second)
            else:
                hour_12 = current_hour % 12
                if hour_12 == 0:
                    hour_12 = 12
                am_pm_display = "AM" if current_hour < 12 else "PM"
                time_str = "%02d:%02d:%02d %s" % (hour_12, current_minute, current_second, am_pm_display)

            # Get RDS info
            new_station_name, new_song_title = fm_radio.GetRDS()

            # Only update if new full data arrives
            if new_station_name.strip() and new_station_name != last_station_name:
                last_station_name = new_station_name
                station_scroll_index = 0
                station_scroll_last_update = time.ticks_ms()
            if new_song_title.strip():
                song_title = new_song_title
                scroll_index = 0
                scroll_last_update = time.ticks_ms()

            # If frequency changed, clear PS buffer and update last_freq
            if fm_radio.Frequency != last_freq:
                if hasattr(fm_radio, "rds_station_buf"):
                    fm_radio.rds_station_buf = [' '] * 8
                last_freq = fm_radio.Frequency
                station_name = ""  # Force blank until new RDS arrives

            # Only show frequency if no RDS station name
            if not last_station_name or last_station_name.strip() == "":
                display_text = "%.1f MHz" % fm_radio.Frequency
            else:
                display_text = last_station_name


            # OLED main info display
            oled.fill(0)
            oled.text(time_str, 0, 0)  # Line 1: Time at the top
            oled.text("%.1f MHz" % fm_radio.Frequency, 0, 16) # Line 2: Frequency display

            # RDS RadioText scrolling display (Line 3)
            display_width = 16
            if 'song_title' not in locals():
                song_title = ""
            if len(song_title) > display_width:
                if time.ticks_diff(time.ticks_ms(), scroll_last_update) > SCROLL_INTERVAL:
                    scroll_index = (scroll_index + 1) % (len(song_title) - display_width + 1)
                    scroll_last_update = time.ticks_ms()
                scroll_text = song_title[scroll_index:scroll_index + display_width]
            else:
                scroll_text = song_title
                scroll_index = 0
                scroll_last_update = time.ticks_ms()
            oled.text(scroll_text, 0, 32)  # Line 3: RDS RadioText

            oled.text("Vol:%d" % fm_radio.Volume, 0, 50)   # Volume in corner
            oled.show()

            last_tick = time.ticks_ms()

        # Print menu to console once per second
        if time.ticks_diff(time.ticks_ms(), last_menu_print) >= 1000:
            # If the time string is set, print it
            print("Current time:", time_str if 'time_str' in locals() else "Loading...")
            print("")
            print("ECE 299 FM Radio Demo Menu")
            print("Press SW1 for: change volume level")
            print("Press SW2 for: change between 12/24hr time")
            print("Press SW3 for: set alarm")
            print("Press SW4 for: change radio frequency")
            print("")
            # Print RDS info to console
            print("RDS Station Name:", last_station_name if last_station_name else "(none)")
            print("RDS RadioText:", song_title if 'song_title' in locals() and song_title else "(none)")

            last_menu_print = time.ticks_ms()

            # Alarm trigger check
            if alarm_enabled:
                # If snoozing, wait until snooze expires
                if alarm_snoozed_until is not None:
                    if time.time() < alarm_snoozed_until:
                        # Still snoozing, do nothing
                        pass
                    else:
                        # Snooze expired
                        alarm_snoozed_until = None
                        alarm_triggered = False  # Allow retrigger
                # If not snoozing and alarm time has passed, trigger alarm
                elif (
                    not alarm_triggered and
                    (
                        (current_hour > alarm_hour) or
                        (current_hour == alarm_hour and current_minute >= alarm_minute)
                    )
                ):
                    print("Alarm! Turning radio on at max volume.")
                    fm_radio.SetMute(False)
                    fm_radio.SetVolume(15)
                    fm_radio.ProgramRadio()
                    alarm_triggered = True

                    # OLED alarm display and snooze/cancel handling
                    alarm_active = True
                    while alarm_active:
                        oled.fill(0)
                        oled.text("ALARM GOING OFF!", 5, 10)
                        oled.text("SW4: Snooze", 10, 30)
                        oled.text("SW1: Cancel", 10, 45)
                        oled.show()

                        # Snooze (SW4)
                        if button_sw4.value():
                            print("Alarm snoozed for 30 seconds.")
                            alarm_snoozed_until = time.time() + 15
                            alarm_active = False
                            alarm_triggered = False  # Allow retrigger after snooze
                            time.sleep(0.5)  # debounce
                            break

                        # Cancel (SW1)
                        if button_sw1.value():
                            print("Alarm cancelled.")
                            alarm_enabled = False
                            alarm_triggered = False
                            alarm_active = False
                            alarm_snoozed_until = None
                            time.sleep(0.5)  # debounce
                            break

                        time.sleep_ms(50)
            
            if fm_radio.Frequency != last_freq:
                # Reset RDS buffers
                if hasattr(fm_radio, "rds_station_buf"):
                    fm_radio.rds_station_buf = [' '] * 8
                    fm_radio.rds_ps_received = [False] * 4
                if hasattr(fm_radio, "rds_track_name_buf"):
                    fm_radio.rds_track_name_buf = [' '] * 64
                last_freq = fm_radio.Frequency
                station_name = ""


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

#
# Set volume level of radio
#
    # Menu selection handling
    if select == "1":
        print("Rotate rotary1 to change volume.")
        print("Press Button SW1 (Pin 0) to confirm and return to menu.")
        val_old = rotary1.value()
        
        while True:
            val_new = rotary1.value()
            
            # Only update display when rotary changes
            if val_new != val_old:
                val_old = val_new
                print("Volume:", val_new)
                time.sleep_ms(50) # debounce delay

            # OLED live update for volume
            oled.fill(0)
            oled.text("Set Volume", 10, 0)
            oled.text("Volume: %d" % val_old, 10, 10)
            if val_old == 0:
                oled.text("(Muted)", 10, 25)
            oled.text("SW1: Confirm", 10, 40)
            oled.text("SW4: Cancel", 10, 50)
            oled.show()

            # Only program the radio when button is pressed
            if button_sw1.value() == 1:
                # Apply the volume setting to the radio
                if val_old == 0:
                    fm_radio.SetMute(True)
                else:
                    fm_radio.SetMute(False)
                
                if fm_radio.SetVolume(val_old):
                    fm_radio.ProgramRadio()
                    print("Volume set to:", val_old)
                    print("Returning to menu...")
                else:
                    print("Error setting volume")
                
                time.sleep(0.5)  # debounce delay
                break

            # Cancel and return to menu when SW4 is pressed
            if button_sw4.value() == 1:
                print("Volume selection cancelled. Returning to menu...")
                time.sleep(0.5)  # debounce delay
                break
            
            time.sleep_ms(50)  # Main loop delay

#        
# Set time and change between 12hr/24hr time     
#        
    elif( select == "2" ):
        print("Set Time Mode")
        print("Rotary1: Set hour")
        print("Rotary2: Set alarm minute")
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

        while True:
            new_hour = rotary1.value()
            new_minute = rotary2.value()

            # Update time if changed
            if new_hour != hour or new_minute != minute:
                hour = new_hour
                minute = new_minute

                # Automatically update AM/PM in 12-hour mode
                if not is_24_hour_format:
                    # If hour is 12, AM/PM depends on previous state and minute rollover
                    if hour == 12:
                        if am_pm_state == "AM" and new_minute < minute:
                            am_pm_state = "PM"
                        elif am_pm_state == "PM" and new_minute < minute:
                            am_pm_state = "AM"
                    else:
                        pass

                time.sleep_ms(100)

            # OLED live update for time setting
            oled.fill(0)
            oled.text("Set Time", 10, 0)
            if is_24_hour_format:
                oled.text("Time: %02d:%02d" % (hour, minute), 10, 10)
            else:
                # Concatenate time for display
                display_hour = hour
                display_am_pm = am_pm_state
                oled.text("Time: %02d:%02d %s" % (display_hour, minute, display_am_pm), 10, 10)
            oled.text("SW1: Cancel", 10, 20)
            oled.text("SW2: Save", 10, 30)
            oled.text("SW3: 12/24hr", 10, 40)
            oled.text("SW4: AM/PM", 10, 50)
            oled.show()

            # Toggle 12/24 hour format with SW3
            if button_sw3.value() == 1:
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
                time.sleep(0.5)  # debounce

            # Cancel and return to menu when SW1 is pressed
            if button_sw1.value() == 1:
                print("Frequency selection cancelled. Returning to menu...")
                time.sleep(0.5)  # debounce delay
                break

            # AM/PM toggle in 12-hour mode
            if not is_24_hour_format and button_sw4.value() == 1:
                am_pm_state = "PM" if am_pm_state == "AM" else "AM"
                time.sleep(0.5)  # debounce

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
        print("Press SW3 to toggle AM/PM (in 12hr mode).")

        # Set up rotary ranges for alarm setting
        if is_24_hour_format:
            rotary1.set(min_val=0, max_val=23, value=current_hour)
            am_pm_state = None  # Not used in 24hr mode
        else:
            # 12-hour mode: 1-12, track AM/PM
            hour_12 = current_hour % 12
            if hour_12 == 0:
                hour_12 = 12
            rotary1.set(min_val=1, max_val=12, value=hour_12)
            am_pm_state = "AM" if current_hour < 12 else "PM"

        rotary2.set(min_val=0, max_val=59, value=current_minute)

        alarm_set_hour = rotary1.value()
        alarm_set_minute = rotary2.value()

        # Update alarm values
        while True:
            new_alarm_hour = rotary1.value()
            new_alarm_minute = rotary2.value()
            if new_alarm_hour != alarm_set_hour or new_alarm_minute != alarm_set_minute:
                alarm_set_hour = new_alarm_hour
                alarm_set_minute = new_alarm_minute
                time.sleep_ms(100)

            # OLED live update for alarm time
            oled.fill(0)
            oled.text("Set Alarm", 10, 0)
            if is_24_hour_format:
                alarm_str = "Alarm: %02d:%02d" % (alarm_set_hour, alarm_set_minute)
            else:
                alarm_str = "Alarm: %02d:%02d %s" % (alarm_set_hour, alarm_set_minute, am_pm_state)
            oled.text(alarm_str, 10, 10)
            oled.text("SW4: Confirm", 10, 30)
            oled.text("SW1: Cancel", 10, 40)
            if not is_24_hour_format:
                oled.text("SW3: AM/PM", 10, 50)
            oled.show()

            # AM/PM toggle in 12-hour mode
            if not is_24_hour_format and button_sw3.value() == 1:
                am_pm_state = "PM" if am_pm_state == "AM" else "AM"
                time.sleep(0.5)  # debounce

            # Confirm alarm with SW4
            if button_sw4.value() == 1:
                if is_24_hour_format:
                    alarm_hour = alarm_set_hour
                else:
                    # Convert 12h to 24h
                    if am_pm_state == "AM":
                        alarm_hour = alarm_set_hour if alarm_set_hour != 12 else 0
                    else:
                        alarm_hour = alarm_set_hour if alarm_set_hour == 12 else alarm_set_hour + 12
                alarm_minute = alarm_set_minute
                alarm_enabled = True
                alarm_triggered = False
                print("Alarm set for %02d:%02d%s" % (alarm_hour 
                                                        if is_24_hour_format else alarm_set_hour,
                                                    alarm_minute,
                                                        "" if is_24_hour_format else " " + am_pm_state
                ))
                time.sleep(0.5)
                break

            # Cancel and return to menu when SW4 is pressed
            if button_sw1.value() == 1:
                print("Volume selection cancelled. Returning to menu...")
                time.sleep(0.5)  # debounce delay
                break

        # Restore rotary1 and rotary2 to original volume/freq range
        rotary1.set(min_val=0, max_val=15)
        rotary2.set(min_val=0, max_val=99)
    
#
# Set radio frequency
#
    elif ( select == "4" ):
        print("Rotate rotary2 to change frequency.")
        print("Press Button SW4 to confirm and return to menu.")
        val_old = rotary2.value()
        freq_old = 88.1 + val_old * 0.2
        print("Frequency:", "%.1f" % freq_old)

        while True:
            val_new = rotary2.value()
            
            # Only update display when rotary changes
            if val_new != val_old:
                val_old = val_new
                freq_new = 88.1 + val_new * 0.2
                print("Frequency:", "%.1f" % freq_new)
                time.sleep_ms(50)  # Small delay for display update

            # OLED live update for frequency
            oled.fill(0)
            oled.text("Set Frequency", 10, 0)
            oled.text("Freq: %.1f MHz" % (88.1 + val_old * 0.2), 10, 20)
            oled.text("SW4: Confirm", 10, 40)
            oled.text("SW1: Cancel", 10, 50)
            oled.show()

            # Program when SW4 is pressed
            if button_sw4.value() == 1:
                freq_final = 88.1 + val_old * 0.2
                if fm_radio.SetFrequency(freq_final):
                    fm_radio.ProgramRadio()
                    print("Frequency set to:", "%.1f" % freq_final)
                    print("Returning to menu...")
                else:
                    print("Error setting frequency")
                
                time.sleep(0.5)  # debounce delay
                break

            # Cancel and return to menu when SW1 is pressed
            if button_sw1.value() == 1:
                print("Frequency selection cancelled. Returning to menu...")
                time.sleep(0.5)  # debounce delay
                break
            
            time.sleep_ms(50)  # Main loop delay

    else:
        print( "Invalid menu option" )

