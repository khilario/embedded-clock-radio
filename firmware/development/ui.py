from ssd1306 import SSD1306_SPI
from machine import Pin, SPI
import time

class UI:
    def __init__(self, radio, clock):
        self.radio = radio
        self.clock = clock

        spi = SPI(0, baudrate=100000, sck=Pin(18), mosi=Pin(19))
        self.oled = SSD1306_SPI(128, 64, spi, dc=Pin(20), res=Pin(21), cs=Pin(17), external_vcc=True)

    def draw_splash(self):
        self.oled.fill(0)
        self.text_centered("ECE 299", 10)
        self.text_centered("Animal Clock Radio", 30)
        self.text_centered("Loading...", 50)
        self.oled.show()
        time.sleep(2)

    def text_centered(self, text, y):
        x = max(0, (128 - len(text)*8)//2)
        self.oled.text(text, x, y)

    def draw_main(self, now, station, song):
        hour, minute, second = now[4], now[5], now[6]
        time_str = "%02d:%02d:%02d" % (hour, minute, second)
        self.oled.fill(0)
        self.text_centered(time_str, 0)
        self.text_centered(station if station else "%.1f MHz" % self.radio.Frequency, 16)
        self.text_centered(song, 32)
        self.oled.text("Vol:%d" % self.radio.Volume, 0, 50)
        self.oled.text("A:%s" % ("✓" if self.clock.alarm_enabled else "✗"), 100, 50)
        self.oled.show()

    def set_volume(self, rotary, button):
        while not button.value():
            v = rotary.value()
            self.radio.SetVolume(v)
            self.radio.SetMute(False if v > 0 else True)
            self.radio.ProgramRadio()
            self.oled.fill(0)
            self.text_centered("Volume: %d" % v, 24)
            self.text_centered("SW1 to confirm", 45)
            self.oled.show()
            time.sleep(0.1)

    def set_frequency(self, radio, rotary, button):
        while not button.value():
            val = rotary.value()
            freq = 88.1 + val * 0.2
            radio.SetFrequency(freq)
            radio.ProgramRadio()
            self.oled.fill(0)
            self.text_centered("Frequency: %.1f" % freq, 24)
            self.text_centered("SW4 to confirm", 45)
            self.oled.show()
            time.sleep(0.1)

    def set_time(self, clock, r_hour, r_min, b_confirm, b_format, b_toggle):
        hour = r_hour.value()
        minute = r_min.value()
        self.oled.fill(0)
        self.text_centered("Set Time", 0)
        self.text_centered("Hour: %02d" % hour, 20)
        self.text_centered("Minute: %02d" % minute, 35)
        self.text_centered("SW2 to confirm", 50)
        self.oled.show()
        while not b_confirm.value():
            clock.set_time(r_hour.value(), r_min.value())
            time.sleep(0.1)

    def set_alarm(self, clock, r_hour, r_min, b_toggle, b_confirm):
        self.oled.fill(0)
        self.text_centered("Set Alarm", 0)
        while not b_confirm.value():
            h, m = r_hour.value(), r_min.value()
            self.text_centered("Hour: %02d  Min: %02d" % (h, m), 20)
            self.text_centered("SW4 to confirm", 40)
            self.oled.show()
            time.sleep(0.1)
        clock.set_alarm(r_hour.value(), r_min.value())
