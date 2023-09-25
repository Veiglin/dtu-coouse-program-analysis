import pytest
import json
import random
import sys
import math
import glob
import subprocess
import pathlib
from interpreter import Interpreter

@pytest.fixture(scope="session", autouse=True)
def before_tests():
    def get_paths(folder_path):
        return glob.glob(folder_path + '/**/*.json', recursive=True)
    
    def get_function_bytecode(json_obj):
        return json_obj['code']
    
    def get_functions(json_obj):
        functions = {}
        for func in json_obj['methods']:
            is_case = any(annotation['type'] == 'dtu/compute/exec/Case' for annotation in func['annotations'])
            if is_case:
                functions[func['name']] = get_function_bytecode(func)
        return functions
    
    def analyse_bytecode(folder_path, target_folder_path):
        class_files = glob.glob(folder_path + '/**/*.class', recursive=True)
        for class_file in class_files:
            json_file = pathlib.Path(class_file).name.replace('.class', '.json')
            command = ["jvm2json", "-s", class_file, "-t", target_folder_path + json_file]
            subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    global byte_codes
    folder_path_class_files = "src/executables/java/dtu/compute/exec"
    folder_path = "decompiled/dtu/compute/exec/"
    analyse_bytecode(folder_path_class_files, folder_path)
    
    files = get_paths(folder_path)
    byte_codes = {}
    for file_path in files:
        with open(file_path, 'r') as file:
            byte_codes.update(get_functions(json.load(file)))

def run_interpreter(byte_code, memory=None, stack=None, locals=None):
    interpret = Interpreter(byte_code, False, byte_codes)
    interpret.memory = memory or []
    return interpret.run((locals or [], stack or [], 0))

def test_noop():
    assert run_interpreter(byte_codes['noop']) is None

def test_zero():
    assert run_interpreter(byte_codes['zero']) == 0

def test_hundredAndTwo():
    assert run_interpreter(byte_codes['hundredAndTwo']) == 102

def test_identity():
    test_int = random.randint(-sys.maxsize, sys.maxsize)
    assert run_interpreter(byte_codes['identity'], locals=[test_int]) == test_int

@pytest.mark.parametrize("byte_code_name, operation", [
    ("add", lambda x, y: x + y),
    ("min", min),
])
def test_binary_operations(byte_code_name, operation):
    test_int1 = random.randint(-sys.maxsize, sys.maxsize)
    test_int2 = random.randint(-sys.maxsize, sys.maxsize)
    assert run_interpreter(byte_codes[byte_code_name], locals=[test_int1, test_int2]) == operation(test_int1, test_int2)

def test_factorial():
    test_int = random.randint(-100, 100)
    expected = math.factorial(test_int) if test_int >= 0 else 1
    assert run_interpreter(byte_codes['factorial'], locals=[test_int]) == expected

def test_helloWorld():
    assert run_interpreter(byte_codes['helloWorld']) is None

def test_first():
    test_arr = [random.randint(0, 25) for _ in range(random.randint(0, 25))]
    assert run_interpreter(byte_codes['first'], memory=[test_arr], locals=[0]) == test_arr[0]

def test_access():
    test_arr = [random.randint(0, 25) for _ in range(random.randint(0, 25))]
    test_int = random.randint(0, len(test_arr))
    assert run_interpreter(byte_codes['access'], memory=[test_arr], locals=[test_int, 0]) == test_arr[test_int]

def test_newArray():
    assert run_interpreter(byte_codes['newArray']) == 1
