import subprocess
import sys
import shutil
import os
from merge_list import merge_llm_and_rule

def run_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)

def main():
    if len(sys.argv) != 2:
        sys.exit(1)

    original_dir = os.getcwd()   
    code_project_dir = sys.argv[1]

    # 1차 Rule-based
    ast_dir = os.path.join(original_dir, "AST-Code")
    os.chdir(ast_dir)
    cmd = ["python3", "main.py", code_project_dir]
    run_command(cmd)

    # Rule & LLM 결과 병합
    merge_llm_and_rule()

    # ID-obfuscation
    obf_dir = os.path.join(original_dir, "ID-Obf")
    os.chdir(obf_dir)
    cmd = ["python3", "main.py"]
    run_command(cmd)
    
    os.chdir(original_dir)
    file_path = "./AST-Code/output/"
    if os.path.isdir(file_path):
        shutil.rmtree(file_path)
    file_path = "./ID-Obf/output/"
    if os.path.isdir(file_path):
        shutil.rmtree(file_path)

if __name__ == "__main__":
    main()