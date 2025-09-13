#!/usr/bin/env python3
import time
import threading
from contextlib import ExitStack
import tfluna  # pip install tfluna-driver

PORTS = ["/dev/ttyS3", "/dev/ttyS4"]
BAUD = 115200
SAMPLE_HZ = 100   # 1..250 supported by TF-Luna

def reader(tf: tfluna.TfLuna, key: str, latest: dict, stop: threading.Event):
    """Continuously read frames from one TF-Luna and stash the latest values."""
    while not stop.is_set():
        try:
            dist, strength, temp = tf.read_tfluna_data()
            latest[key] = (dist, strength, temp, time.time())
        except Exception:
            # Mark as missing on error; keep trying
            latest[key] = (None, None, None, time.time())
            time.sleep(0.02)

def fmt_m(val):
    return f"{val:5.2f}" if val is not None else "  ---"

def fmt_delta(a, b):
    return f"{(a-b):+6.2f}" if (a is not None and b is not None) else "  --- "

def main():
    latest = {}                     # {port: (dist, strength, temp, ts)}
    stop = threading.Event()

    with ExitStack() as stack:
        # Open both sensors
        tf_objs = []
        for port in PORTS:
            tf = stack.enter_context(tfluna.TfLuna(serial_name=port, baud_speed=BAUD))
            tf_objs.append((port, tf))
            try:
                ver = tf.get_version()
                tf.set_samp_rate(SAMPLE_HZ)
                print(f"TF-Luna @ {port} ({BAUD} baud) | FW: {ver} | {SAMPLE_HZ} Hz")
            except Exception as e:
                print(f"(warning) setup step failed on {port}: {e}")

        # Start a thread per sensor
        threads = []
        for port, tf in tf_objs:
            t = threading.Thread(target=reader, args=(tf, port, latest, stop), daemon=True)
            t.start()
            threads.append(t)

        print("Streaming... Ctrl+C to stop.")
        try:
            while True:
                # Pull current values
                d3 = latest.get("/dev/ttyS3", (None, None, None, None))[0]
                d4 = latest.get("/dev/ttyS4", (None, None, None, None))[0]
                print(f"S3: {fmt_m(d3)} m | S4: {fmt_m(d4)} m | Δ(S3-S4): {fmt_delta(d3, d4)} m")
                time.sleep(0.05)  # print ~20 Hz
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            stop.set()
            for t in threads:
                t.join(timeout=0.5)

if __name__ == "__main__":
    main()