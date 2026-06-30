import os
import sys
import json
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_java
import Extract_Hunk_AST_Util

JAVA_LANGUAGE = Language(tree_sitter_java.language())
parser = Parser(JAVA_LANGUAGE)

#TODO: Complete the function comments
def extract_class_information(target_node, source_code, should_include_nested_classes: bool):
    """
    Extracts the relevanet information of the target node's class.

    """
    class_node = Extract_Hunk_AST_Util.get_context_parent_class(target_node)
    if not class_node:
        return None
    
    class_name = class_node.child_by_field_name("name").text.decode("utf-8")
    print(f'brother, class name: {class_name}')

    class_structure = {
        "class_name": class_name,
        "fields": [],
        "methods": [],
        "nested_classes": []
    }

    class_body_node = class_node.child_by_field_name("body")
    # If the class has no body, there is no point searching it for members.
    if not class_body_node:
        return class_structure
    
    class_info_query_string = ("""
    (class_body [
        (field_declaration) @field
        (method_declaration) @method
        (class_declaration) @nested_class
        ])
    """)
    query = Query(JAVA_LANGUAGE, class_info_query_string)
    cursor = QueryCursor(query)
    captures = cursor.captures(class_body_node)

    if "field" in captures:
        sorted_fields = Extract_Hunk_AST_Util.sort_nodes_by_start_point(captures['field'])
        for captured_field in sorted_fields:
            # Skip the nested classes' fields (they get captured in the query unfortunately)
            if captured_field.parent != class_body_node:
                continue
            field_text = Extract_Hunk_AST_Util.get_node_exact_string(captured_field, source_code)
            class_structure['fields'].append(field_text)
    if "method" in captures:
        sorted_methods = Extract_Hunk_AST_Util.sort_nodes_by_start_point(captures['method'])
        for captured_method in sorted_methods:
            # Skip the nested classes' methods (they get captured in the query unfortunately)
            if captured_method.parent != class_body_node:
                continue
            method_signature = Extract_Hunk_AST_Util.get_method_signature(captured_method, source_code)
            class_structure['methods'].append(method_signature)
    if "nested_class" in captures and should_include_nested_classes:
        sorted_nested_classes = Extract_Hunk_AST_Util.sort_nodes_by_start_point(captures['nested_class'])
        for nested_class in sorted_nested_classes:
            # The query will capture the deeply nested classes as well. 
            # We have to skip these cases otherwise due to the recursive structure,
            # some classes will be included multiple times.
            if nested_class.parent != class_body_node:
                continue
            nested_class_info = extract_class_information(nested_class, source_code, should_include_nested_classes)
            class_structure['nested_classes'].append(nested_class_info)
    
    return class_structure

#TODO:
def extract_package_information():
    pass

#TODO:
def extract_imported_libraries():
    pass


def get_called_methods(target_node):
    """
    Returns the target node's encapsulating method's called methods.

    Parameters
    ----------
    target_node :           The target tree-sitter node to work on. Should be located within a method
                            to return correct output.

    Returns
    -------
    sorted_invocations :    A list of invocations sorted by their starting points.
    """
    node = target_node
    if not node:
        print('Error, received NONE node in extract_neighboring_methods_within_same_class function.')
        return None


    if not node.type == "method_declaration":
        while not node.type == "method_declaration" and not node.type == "class_declaration" and not node.type == "program":
            node = node.parent
    
    # The passed in target node is not inside a method:
    if node.type != "method_declaration":
        return None
    
    query = Query(JAVA_LANGUAGE, "(method_invocation) @invocation")
    cursor = QueryCursor(query)
    captures = cursor.captures(node)
    sorted_invocations = Extract_Hunk_AST_Util.sort_nodes_by_start_point(captures['invocation'])

    return sorted_invocations
    
def extract_called_methods(target_node, source_code):
    """
    Calls get_called_methods and converts its output to human-readable dict and returns it.

    Parameters
    ----------
    target_node :               The target tree-sitter node to work on. Should be located within a method
                                to return correct output.
    source_code :               The source code that contains the target_node. Should be text.

    Returns
    -------
    method_invocations_info :   A list of dict objects containing the called methods' source codes and position data.
    """
    method_invocations = get_called_methods(target_node)
    if not method_invocations:
        return {}
    method_invocations_info = []
    for method_invocation in method_invocations:
        
        method_invocation_information = {
            "Source Code" : Extract_Hunk_AST_Util.get_node_exact_string(method_invocation, source_code),
            "Start Line" : method_invocation.start_point[0],
            "Start Column" : method_invocation.start_point[1],
            "End Line" : method_invocation.end_point[0],
            "End Column" : method_invocation.end_point[1]
        }
        method_invocations_info.append(method_invocation_information)
    
    return method_invocations_info

    



#TODO:
def extract_referenced_classes():
    pass

def extract_neighboring_methods_within_same_class(target_node):
    """
        Returns the previous and next method relative to the provided context node (if they exist).

        Parameters
        ----------
        target_node :       The target tree-sitter node to work on. Can be a child of method 
                            or method declaration.

        Returns
        -------
        previous_method :   Node of the previous method relative to the provided target node
        next_method :       Node of the next method relative to the provided target node
    """
    node = target_node
    if not node:
        print('Error, received NONE node in extract_neighboring_methods_within_same_class function.')
        return None


    if not node.type == "method_declaration":
        while not node.type == "method_declaration" and not node.type == "class_declaration" and not node.type == "program":
            node = node.parent
    
    # The passed in target node is not inside a method:
    if node.type != "method_declaration":
        return {}, {}
    
    # PREVIOUS METHOD
    previous_sibling = node.prev_named_sibling
    if previous_sibling:
        while previous_sibling.type != "method_declaration":
            previous_sibling = previous_sibling.prev_named_sibling
            if not previous_sibling:
                break
    previous_method = previous_sibling

    # NEXT METHOD
    next_sibling = node.next_named_sibling
    if next_sibling:
        while next_sibling.type != "method_declaration":
            next_sibling = next_sibling.next_named_sibling
            if not next_sibling:
                break
    next_method = next_sibling    

    return previous_method, next_method


#TODO:
def extract_control_flow_constructs():
    pass

#TODO:
def generate_structured_context_metadata():
    pass