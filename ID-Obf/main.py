import os  
import json
import subprocess
from obf_tool.collect_identifiers import collect_identifiers
from obf_tool.change_name import change_name
from obf_tool.change_name import remove_tagging

SWIFT_FILE_PATH = []

def run_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)

def read_file():
    # swift 파일 경로 저장
    swift_file_path = "../AST-Code/output/swift_file_list.txt"
    if os.path.exists(swift_file_path):
        with open(swift_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                SWIFT_FILE_PATH.append(line)
                
    # 식별자 매핑 정보 저장
    mapping_info = {}
    mapping_file_path = "./mapping_result.json"
    if os.path.exists(mapping_file_path):
        with open(mapping_file_path, "r", encoding="utf-8") as f:
            mapping_data = json.load(f)
        
        for _, items in mapping_data.items():
            for item in items:
                mapping_info[item.get("target")] = item.get("replacement")
    return mapping_info
               

def main():
    os.makedirs("./output/", exist_ok=True)
    identifier_info, all_identifier_info = collect_identifiers()
    identifier_path = "./output/identifier.json"
    with open(identifier_path, "w", encoding="utf-8") as f:
        json.dump(identifier_info, f, indent=2, ensure_ascii=False, default=list)
    
    external_name_path = "../AST-Code/output/external_name.txt"
    if os.path.exists(external_name_path):
        with open(external_name_path, "r", encoding="utf-8") as f:
            for line in f:
                name = line.strip()
                if name not in all_identifier_info:
                    all_identifier_info.append(name)

    all_identifier_path = "./output/all_identifier.json"
    with open(all_identifier_path, "w", encoding="utf-8") as f:
        json.dump(all_identifier_info, f, indent=2, ensure_ascii=False, default=list)
    
    cmd = ["python3", "./mapping_tool/service_mapping.py", 
           "--targets", "./output/identifier.json", 
           "--exclude", "./output/all_identifier.json",
           "--output", "mapping_result.json", 
           "--pool-dir", "./mapping_tool/test_name_clusters", 
           "--index-dir", "./mapping_tool/test_name_clusters"]
    run_command(cmd)

    mapping_info = read_file()
    change_name(SWIFT_FILE_PATH, identifier_info, mapping_info)
    
    remove_tagging(SWIFT_FILE_PATH)

if __name__ == "__main__":
    main()