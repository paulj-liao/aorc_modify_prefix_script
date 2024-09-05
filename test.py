def flatten_config(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    stack = []
    flat_config = []

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        indent_level = len(line) - len(stripped_line)
        
        while stack and stack[-1][1] >= indent_level:
            stack.pop()

        if stack:
            prefix = '.'.join(item[0] for item in stack)
            flat_config.append(f"{prefix} {stripped_line}")
        else:
            flat_config.append(stripped_line)

        stack.append((stripped_line, indent_level))

    return flat_config

# Example usage
file_path = 'config.txt'
flat_config = flatten_config(file_path)
for line in flat_config:
    print(line)