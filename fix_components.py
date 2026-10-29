"""Fix the missing comma after space_payload_frame in components.py."""
import re

with open(r"D:\BLUEPRINT\components.py", "rb") as f:
    content = f.read()

# Decode preserving CRLF
text = content.decode("utf-8")

# The problem: line 248 is `    }\r\n` followed by a comment line
# We need it to be `    },\r\n`
# Pattern: closing brace of space_payload_frame dict (after spec_status line)
# Find the exact sequence and add comma

old = '        \"spec_status\": \"example\"\r\n    }\r\n    # -------------------- NASA-INSPIRED'
new = '        \"spec_status\": \"example\"\r\n    },\r\n    # -------------------- NASA-INSPIRED'

if old in text:
    text = text.replace(old, new, 1)
    print("Fixed: added missing comma after space_payload_frame dict.")
else:
    print("ERROR: Pattern not found. Checking content around line 248...")
    lines = text.split("\r\n")
    for i, line in enumerate(lines[240:260], start=241):
        print(f"{i}: {repr(line)}")

with open(r"D:\BLUEPRINT\components.py", "wb") as f:
    f.write(text.encode("utf-8"))

print("Done writing components.py")

