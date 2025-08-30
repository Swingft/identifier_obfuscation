import os  
import re

def remove_tagging(swift_file_path):
    for path in swift_file_path:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for i in range (len(lines)):
                lines[i] = lines[i].replace("team_ufo_swingft", "")
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines)

def tagging_string(source_code, name):
    new_source_code = ""
    for line in source_code.splitlines():
        new_line = ""
        idx = 0
        in_string = False  

        while idx < len(line):
            char = line[idx]

            if char == '"':
                if idx == 0 or line[idx-1] != '\\': 
                    in_string = not in_string
                new_line += char
                idx += 1
                continue

            if in_string:
                if char == '\\' and idx + 1 < len(line) and line[idx + 1] == '(':
                    start = idx + 2
                    depth = 1
                    j = start
                    while j < len(line) and depth > 0:
                        if line[j] == '(':
                            depth += 1
                        elif line[j] == ')':
                            depth -= 1
                        j += 1
                    new_line += line[idx:j]
                    idx = j
                    continue
                else:
                    match = re.match(rf'\b{name}\b', line[idx:])
                    if match:
                        new_line += f"team_ufo_swingft{name}"
                        idx += len(name)
                        continue

            new_line += char
            idx += 1

        new_source_code += new_line + "\n"
    return new_source_code

def change_name(SWIFT_FILE_PATH, identifier_info, mapping_info):
    # function, variable, case 난독화
    for path in SWIFT_FILE_PATH:
        if not os.path.exists(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            source_code = f.read()
        
        for kind, names in identifier_info.items():
            if kind in ["function", "variable"]:
                for name in names:
                    source_code = tagging_string(source_code, name)
                    changed_name = mapping_info[name]
                    pattern = rf'(?<![\w"]){re.escape(name)}(?![\w"])'
                    source_code = re.sub(pattern, changed_name, source_code)
                    
            elif kind == "case":
                for name in names:
                    source_code = tagging_string(source_code, name)

                    original_name = name
                    if name.startswith("`") and name.endswith("`"):
                        name = name[1:-1]
                    
                    changed_name = mapping_info[name]

                    pattern_decl = rf'(?<![\w"]){re.escape(original_name)}(?![\w"])'
                    source_code = re.sub(pattern_decl, rf"{changed_name}", source_code)
                    
                    pattern = rf'(?<=\.){re.escape(name)}(?![\w"])'
                    source_code = re.sub(pattern, changed_name, source_code)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(source_code)
    
    # Struct, Protocol, Class, Enum 난독화
    for path in SWIFT_FILE_PATH:
        if not os.path.exists(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            source_code = f.read()
            
        for kind, names in identifier_info.items():
            if kind not in ["function", "variable", "case"]:
                for name in names:
                    source_code = tagging_string(source_code, name)
                    
                    changed_name = mapping_info[name]
                    pattern = rf'(?<![\w"]){re.escape(name)}(?![\w"])'
                    source_code = re.sub(pattern, changed_name, source_code)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(source_code)
