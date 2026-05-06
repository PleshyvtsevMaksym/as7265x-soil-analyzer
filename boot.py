# boot.py -- executed on boot

import gc

gc.collect()

print("Boot complete")
print("Free memory:", gc.mem_free())