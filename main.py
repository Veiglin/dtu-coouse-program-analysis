import json
import glob
import subprocess
import pydot
import os

def get_all_files_with_extension(folder_path, extension):
    pattern = f"{folder_path}/**/*.{extension}"
    return glob.glob(pattern, recursive=True)

def extract_class_details(json_obj):
    dependencies, interfaces, fields, methods, compositions = set(), set(), set(), set(), set()

    if isinstance(json_obj, dict):
        for key, value in json_obj.items():
            if key in ["type", "ref"] and value:
                if "name" in value and "/" in value["name"] and not value["name"] == "java/lang/Object":
                    dependencies.add(value["name"])

            if key == "interfaces":
                interfaces.update({interface["name"] for interface in value})

            if key == "fields":
                fields.update(extract_fields(value))

            if key == "methods":
                methods.update(extract_methods(value))

            if key == "innerclasses" and value and isinstance(value, list) and len(value) > 0 and json_obj["name"] == value[0]["class"]:
                compositions.add(value[0]["outer"])

            sub_dependencies, sub_interfaces, sub_fields, sub_methods, sub_compositions = extract_class_details(value)
            dependencies.update(sub_dependencies)
            interfaces.update(sub_interfaces)
            fields.update(sub_fields)
            methods.update(sub_methods)
            compositions.update(sub_compositions)
            
    elif isinstance(json_obj, list):
        for item in json_obj:
            sub_dependencies, sub_interfaces, sub_fields, sub_methods, sub_compositions = extract_class_details(item)
            dependencies.update(sub_dependencies)
            interfaces.update(sub_interfaces)
            fields.update(sub_fields)
            methods.update(sub_methods)
            compositions.update(sub_compositions)

    return dependencies, interfaces, fields, methods, compositions

def extract_fields(fields_data):
    fields = set()
    for field in fields_data:
        try:
            prefix = "+ " if "public" in field.get("access", []) else "- "
            type_name = field["type"]["name"].split("/")[-1] if "name" in field["type"] else field["type"].get("base", "")
            fields.add(f"{prefix}{field['name']}: {type_name}")
        except:
            pass
    return fields

def extract_methods(methods_data):
    methods = set()
    for method in methods_data:
        try:
            prefix = "+ " if "public" in method.get("access", []) else "- "
            if method["returns"]["type"]:
                return_type = method["returns"]["type"].get("name", "").split("/")[-1] or method["returns"]["type"].get("base", "")
            else:
                return_type = "void"
            methods.add(f"{prefix}{method['name']}(): {return_type}")
        except:
            pass
    return methods

def convert_class_files_to_json(folder_path):
    for class_file in get_all_files_with_extension(folder_path, "class"):
        json_file = class_file.replace('.class', '.json')
        command = ["jvm2json", "-s", class_file, "-t", json_file]
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def generate_class_diagram(classes, two_rows=False):
    uml_diagram = pydot.Dot(graph_type='digraph', engine='neato', dpi=300)
    pydot_classes = {}

    for class_name, class_details in classes.items():
        label = "<" + class_name + "<br align='left'/>--------<br/>"
        if 'fields' in class_details:
            for field in class_details['fields']:
                label += field.replace('<', '&lt;').replace('>', '&gt;') + "<br align='left'/>"
        if label[-5:] != "<br/>":
            label += "--------<br/>"
        if 'methods' in class_details:
            for method in class_details['methods']:
                label += method.replace('<', '&lt;').replace('>', '&gt;') + "<br align='left'/>"
        if label[-5:] == "<br/>":
            label = label[:-13]
        label += ">"

        class_node = pydot.Node(class_name, shape="rectangle", label=label)

        if class_node:
            uml_diagram.add_node(class_node)
            pydot_classes[class_name] = class_node

    for class_name, class_details in classes.items():
        if 'depedencies' in class_details:
            for dependency in class_details['depedencies']:
                association = pydot.Edge(pydot_classes[class_name], pydot_classes.get(dependency, dependency), arrowhead="vee")
                if association:
                    uml_diagram.add_edge(association)
        
        if 'interfaces' in class_details:
            for interface in class_details['interfaces']:
                association = pydot.Edge(pydot_classes[class_name], pydot_classes.get(interface, interface), arrowhead="onormal")
                if association:
                    uml_diagram.add_edge(association)
        
        if 'compositions' in class_details:
            for composition in class_details['compositions']:
                association = pydot.Edge(pydot_classes[class_name], pydot_classes.get(composition, composition), arrowhead="diamond")
                if association:
                    uml_diagram.add_edge(association)

    if not two_rows:
        class_names = list(pydot_classes.keys())
        for i in range(len(class_names)-1):
            invisible_edge = pydot.Edge(pydot_classes[class_names[i]], pydot_classes[class_names[i+1]], weight=1, style="invis")
            uml_diagram.add_edge(invisible_edge)

    uml_diagram.write_png("class_diagram.png")
    uml_diagram.write_svg("class_diagram.svg")


def main(folder_path):
    convert_class_files_to_json(folder_path)

    classes = {}
    for path in get_all_files_with_extension(folder_path, "json"):
        with open(path, 'r') as file:
            json_obj = json.load(file)
            class_name = os.path.basename(path).replace(".json", "")
            class_name = class_name.split("/")[-1]  # Take only the last part of the path
            dependencies, interfaces, fields, methods, compositions = extract_class_details(json_obj)

            dependencies = dependencies.difference(compositions).difference({class_name}).difference({name for name in dependencies if '$' in name})
            interfaces = {name for name in interfaces if '$' not in name}
            fields = {name for name in fields if '$' not in name}
            methods = {name for name in methods if '$' not in name}

            classes[class_name] = {
                'dependencies': dependencies,
                'interfaces': interfaces,
                'fields': fields,
                'methods': methods,
                'compositions': compositions
            }

    # Sort class names
    sorted_classes = dict(sorted(classes.items()))

    generate_class_diagram(sorted_classes, two_rows=True)


if __name__ == "__main__":
    folder_path_input = "/Users/jk/Desktop/assignment3"
    main(folder_path_input)
