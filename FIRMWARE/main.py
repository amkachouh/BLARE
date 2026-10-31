from machine import Pin, SPI, RTC
import st7789py as st7789
import vga2_16x32 as font
import time

# Display pins from your schematic
spi = SPI(
    1, baudrate=10_000_000,
    polarity=0, phase=0,
    sck=Pin(9), mosi=Pin(10), miso=None
)

backlight = Pin(21, Pin.OUT, value=1)

display = st7789.ST7789(
    spi, 76, 284,
    reset=Pin(8, Pin.OUT),
    dc=Pin(6, Pin.OUT),
    cs=Pin(7, Pin.OUT, value=1),
    color_order=st7789.RGB,
    custom_rotations=((0x60, 284, 76, 18, 82, False),)
)
display.inversion_mode(False)

# SW1: plus, SW2: minus, SW3: edit, SW4: screen
buttons = [
    Pin(p, Pin.IN, Pin.PULL_UP)
    for p in (2, 3, 4, 5)
]

raw = [button.value() for button in buttons]
stable = raw[:]
changed_at = [time.ticks_ms()] * 4

# Start at 12:00 PM
rtc = RTC()
rtc.datetime((2026, 1, 1, 3, 12, 0, 0, 0))

mode = 0  # 0: clock, 1: edit hours, 2: edit minutes
screen_on = True
last_draw = None


def read_buttons():
    pressed = [False] * 4
    now = time.ticks_ms()

    for i, button in enumerate(buttons):
        value = button.value()

        if value != raw[i]:
            raw[i] = value
            changed_at[i] = now

        # Debounce: wait for 30 ms of stable input
        if time.ticks_diff(now, changed_at[i]) >= 30:
            if stable[i] != raw[i]:
                stable[i] = raw[i]
                pressed[i] = stable[i] == 0

    return pressed


while True:
    plus, minus, edit, power = read_buttons()

    if power:
        screen_on = not screen_on

        if not screen_on:
            backlight.value(1)
            display.fill(st7789.BLACK)

        last_draw = None

    if screen_on:
        if edit:
            mode = (mode + 1) % 3

        change = int(plus) - int(minus)

        if change and mode:
            current = list(rtc.datetime())

            if mode == 1:
                current[4] = (current[4] + change) % 24
            else:
                current[5] = (current[5] + change) % 60
                current[6] = 0
                current[7] = 0

            rtc.datetime(tuple(current))

        hour, minute, second = rtc.datetime()[4:7]
        state = (hour, minute, second, mode)

        if state != last_draw:
            period = "PM" if hour >= 12 else "AM"

            clock = "{:02d}:{:02d}:{:02d} {}".format(
                hour % 12 or 12,
                minute,
                second,
                period
            )

            labels = (
                "EDIT TO SET",
                "EDIT HOURS",
                "EDIT MINUTES"
            )

            display.text(font, clock, 54, 3)
            display.text(
                font,
                "{:<12}".format(labels[mode]),
                46, 41
            )

            backlight.value(0)
            last_draw = state

    time.sleep_ms(10)
