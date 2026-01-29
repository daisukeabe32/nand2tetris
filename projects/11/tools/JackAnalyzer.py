# JackAnalyzer.py
import os
import sys
from CompilationEngine_ref import CompilationEngine_ref


def is_jack_file(path: str) -> bool:
    return os.path.isfile(path) and path.lower().endswith(".jack")

def collect_jack_files(input_path: str) -> list[str]:
    if os.path.isdir(input_path):
        # Directory: gather all .jack files (non-recursive)
        files = []
        for name in os.listdir(input_path):
            p = os.path.join(input_path, name)
            if is_jack_file(p):
                files.append(p)
        files.sort()
        return files

    # Single file
    if is_jack_file(input_path):
        return [input_path]

    raise ValueError(f"Input must be a .jack file or a directory containing .jack files: {input_path}")

def output_xml_path(jack_path: str) -> str:
    base, _ = os.path.splitext(jack_path)
    return base + ".xml"

def main():
    if len(sys.argv) != 2:
        print("Usage: python JackAnalyzer.py <input.jack | directory>")
        sys.exit(1)

    input_path = sys.argv[1]
    jack_files = collect_jack_files(input_path)

    for jack_path in jack_files:
        out_path = output_xml_path(jack_path)
        ce = CompilationEngine_ref(jack_path, out_path)
        ce.compileClass()
        ce.close()

if __name__ == "__main__":
    main()