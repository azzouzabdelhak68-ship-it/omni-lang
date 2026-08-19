with open('omni_compiler/parser.py', 'r') as f:
    lines = f.readlines()
for i in range(422, 440):
    print(f"{i+1}: {repr(lines[i])}")