#!/usr/bin/env python3
import time
from smbus2 import SMBus

# TF-Luna defaults (I2C mode)
I2C_BUS = 1
TFLUNA_ADDR = 0x10  # Benewake default I2C address

# Register map (per Benewake TF-Luna manual)
REG_DIST_L   = 0x00  # Distance low byte (cm)
REG_DIST_H   = 0x01  # Distance high byte
REG_AMP_L    = 0x02  # Signal strength low byte
REG_AMP_H    = 0x03  # Signal strength high byte
# Optional: temperature is at 0x04/0x05 (see manual)

AMP_MIN_RELIABLE = 100  # below this, distance is considered unreliable (manual guidance)

def read_u16(bus: SMBus, addr: int, low_reg: int) -> int:
    """Read a little-endian 16-bit value starting at low_reg."""
    # Use a single block read for consistency
    data = bus.read_i2c_block_data(addr, low_reg, 2)
    return data[0] | (data[1] << 8)

def main():
    print("TF-Luna I2C reader (distance in cm). Press Ctrl+C to stop.")
    with SMBus(I2C_BUS) as bus:
        # Poll at ~20 Hz (TF-Luna default output is 100 Hz; this is a safe, light poll rate)
        while True:
            try:
                # Read distance and amplitude
                dist_cm = read_u16(bus, TFLUNA_ADDR, REG_DIST_L)
                amp     = read_u16(bus, TFLUNA_ADDR, REG_AMP_L)

                # Validate amplitude per datasheet guidance
                if amp < AMP_MIN_RELIABLE or amp == 0xFFFF:
                    # Unreliable (too low) or overexposed (0xFFFF)
                    print(f"Distance: --- cm   (unreliable, Amp={amp})")
                else:
                    print(f"Distance: {dist_cm:4d} cm   (Amp={amp})")

                time.sleep(0.05)  # 50 ms
            except KeyboardInterrupt:
                print("\nExiting.")
                break
            except OSError as e:
                # I2C bus hiccup (e.g., not connected yet) — show and continue
                print(f"I2C error: {e}")
                time.sleep(0.2)

if __name__ == "__main__":
    main()