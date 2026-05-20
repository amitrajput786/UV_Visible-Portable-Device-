# Circuit Pin Mapping — J1 Header to Raspberry Pi GPIO

## J1 (6-pin header on custom PCB) → RPi 4B GPIO

| J1 Pin | Label  | RPi Physical Pin | RPi GPIO Name | Function                  |
|--------|--------|-----------------|----------------|---------------------------|
| 1      | GPIO17 | 11              | GPIO 17        | UV LED MOSFET gate control|
| 2      | NC     | —               | —              | Not connected             |
| 3      | GPIO4  | 7               | GPIO 4         | DS18B20 temperature data  |
| 4      | +3.3V  | 1 or 17         | +3.3V          | Sensor VDD                |
| 5      | NC     | —               | —              | Not connected             |
| 6      | GND    | 6 (or any GND)  | GND            | Common ground             |

## Power Rails

| Rail  | Voltage | Max Current | Source               | Notes              |
|-------|---------|-------------|----------------------|--------------------|
| +12V  | 12V DC  | ~100 mA     | J2 (external PSU)    | UV LED supply      |
| +3.3V | 3.3V    | ~10 mA      | RPi Pin 1/17         | DS18B20 VDD        |
| GND   | 0V      | —           | Common               | All grounds tied   |

**External supply:** 12V DC, 1A minimum (barrel jack or wire to J2 screw terminal)

## UV LED Current Calculation

```
V_supply = 9V (battery) or 12V (PSU)
V_forward(LED) = 3.4V
V_resistor = 9 - 3.4 = 5.6V
R = 470 Ω
I = 5.6 / 470 = 11.9 mA per LED (safe, rated 20 mA)
```

## DS18B20 Wiring

```
DS18B20 Pin 1 (GND)  → RPi GND (Pin 6)
DS18B20 Pin 2 (DATA) → RPi GPIO4 (Pin 7) + 4.7kΩ pull-up to 3.3V
DS18B20 Pin 3 (VDD)  → RPi +3.3V (Pin 1)
```

**Important:** Pin 1 must be 3.3V (not GND) — incorrect VDD wiring causes wrong family code (41- instead of 28-).

## IRLZ44N MOSFET Wiring

```
Gate   → 1kΩ resistor → RPi GPIO17 (Pin 11)
Source → GND
Drain  → LED cathode return
```

Logic-level MOSFET: fully switches on at 3.3V gate voltage from RPi GPIO.
