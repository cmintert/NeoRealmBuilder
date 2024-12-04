import ast
import os


def get_project_structure(root_dir):
    project_structure = {}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        relative_path = os.path.relpath(dirpath, root_dir)
        if relative_path == ".":
            relative_path = ""
        current_level = project_structure
        if relative_path:
            for part in relative_path.split(os.sep):
                current_level = current_level.setdefault(part, {})

        for filename in filenames:
            if filename.endswith(".py"):
                file_path = os.path.join(dirpath, filename)
                with open(file_path, "r", encoding="utf-8") as file:
                    tree = ast.parse(file.read(), filename=filename)
                    classes = [
                        node.name
                        for node in ast.walk(tree)
                        if isinstance(node, ast.ClassDef)
                    ]
                    current_level[filename] = classes

    return project_structure


def print_project_structure(structure, indent=0):
    for key, value in structure.items():
        print("  " * indent + "- " + key)
        if isinstance(value, dict):
            print_project_structure(value, indent + 1)
        else:
            for cls in value:
                print("  " * (indent + 1) + "- " + cls)


# Example usage
root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) + "/src"
print(f"Project structure for '{root_directory}':")
project_structure = get_project_structure(root_directory)
print_project_structure(project_structure)
