import pandas as pd
import numpy as np
import sys
sys.path.append('.')
from flag_viewer import FLAG_PARAMS, HW_HEALTH_BITS

def decode_flag_value(col_name, raw):
    active = set()
    errors = set()
    if col_name not in FLAG_PARAMS:
        return active, errors
    
    kind, definition = FLAG_PARAMS[col_name]
    
    if kind == "text":
        if isinstance(raw, str):
            active = {f.strip() for f in raw.split("|") if f.strip()}
    elif kind == "bits":
        try:
            val = int(raw)
            if col_name == "hwHealthStatus":
                for bit_pos, name in HW_HEALTH_BITS.items():
                    status = (val >> bit_pos) & 0x03
                    if status == 1:
                        active.add(name)
                    elif status == 2:
                        errors.add(name)
            else:
                for bit, name in definition.items():
                    if val & (1 << bit):
                        active.add(name)
        except (ValueError, TypeError):
            pass
    elif kind == "enum":
        try:
            val = int(raw)
            state_name = definition.get(val, f"STATE_{val}")
            active.add(state_name)
        except (ValueError, TypeError):
            pass
    elif kind == "scalar":
        try:
            val = int(raw)
            active.add(f"{definition}: {val}")
        except (ValueError, TypeError):
            pass
            
    return active, errors

print(decode_flag_value("flightModeFlags (flags)", "ARM|ANGLE"))
print(decode_flag_value("hwHealthStatus", "1")) # 1 = GYRO healthy
