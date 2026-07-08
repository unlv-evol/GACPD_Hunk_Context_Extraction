import os
import sys
import json
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_java
import Extract_Hunk_AST_Util
import Extract_Hunk_AST
JAVA_LANGUAGE = Language(tree_sitter_java.language())
parser = Parser(JAVA_LANGUAGE)

def extract_class_information(target_node, source_code, should_include_nested_classes: bool):
    """
    Extracts the relevanet information of the target node's class.

    Parameters
    ----------
    target_node : A tree-sitter node that is either a child of a 
                  class declaration node or is a class declaration node.
    source_code : The source code of the file that includes the class.
    should_include_nested_classes : Should the class information output 
                                    include the nested classes (recursive)
                                    of the target class?
    """
    class_node = Extract_Hunk_AST_Util.get_context_parent_class(target_node)
    if not class_node:
        return None
    
    class_name = class_node.child_by_field_name("name").text.decode("utf-8")

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
    return []

def extract_imported_libraries():
    """
    Gets the imported libraries from the current working AST (saved in
    Extract_Hunk_AST.py).
    """
    imported_libraries = Extract_Hunk_AST_Util.get_current_AST_import_declarations()
    return imported_libraries

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
    method_node = Extract_Hunk_AST_Util.get_context_parent_method(target_node)
    if not method_node:
        return None
    
    query = Query(JAVA_LANGUAGE, "(method_invocation) @invocation")
    cursor = QueryCursor(query)
    captures = cursor.captures(method_node)
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

def extract_referenced_classes(target_node, source_code):
    """
    Retrieves the referenced classes inside the target node's encapsulating method.

    Parameters
    ----------
    target_node :            A tree-sitter node that should be a descendent of a method 
                             or the method declaration node itself.
    source_code :            The text of the source code that contains the method.

    Returns
    -------
    referenced_class_names : A list of referenced classes inside the taget node's encapsulating
                             method. This list is duplicate-free.

    """
    method_node = Extract_Hunk_AST_Util.get_context_parent_method(target_node)
    if not method_node:
        return []
    
    referenced_class_names = []
    file_imported_classes = Extract_Hunk_AST_Util.get_current_AST_import_declarations_classes(source_code)

    query_string = """
    (scoped_identifier) @potential_class_reference
    (type_identifier) @potential_class_reference
    (identifier) @potential_class_reference
    """
    query = Query(JAVA_LANGUAGE, query_string)
    cursor = QueryCursor(query)
    captures = cursor.captures(method_node)
    if captures:
        potential_class_references = Extract_Hunk_AST_Util.get_node_list_exact_string(captures['potential_class_reference'], source_code)
        potential_class_references = [Extract_Hunk_AST_Util.get_clean_name(x) for x in potential_class_references]
        for potential_class_reference in potential_class_references:
            if potential_class_reference in file_imported_classes and not potential_class_reference in referenced_class_names:
                referenced_class_names.append(potential_class_reference)

    return referenced_class_names

def extract_neighboring_methods_within_same_class(target_node, source_code):
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
    if previous_method:
        previous_method_info = {
            "Signature" : Extract_Hunk_AST_Util.get_method_signature(previous_method, source_code),
            "Start Line": previous_method.start_point[0],
            "End Line": previous_method.end_point[0]
        }

    # NEXT METHOD
    next_sibling = node.next_named_sibling
    if next_sibling:
        while next_sibling.type != "method_declaration":
            next_sibling = next_sibling.next_named_sibling
            if not next_sibling:
                break
    next_method = next_sibling    
    next_method_info = {
            "Signature" : Extract_Hunk_AST_Util.get_method_signature(next_method, source_code),
            "Start Line": next_method.start_point[0],
            "End Line": next_method.end_point[0]
        }

    return previous_method_info, next_method_info

def get_if_statement_next_if(if_statement_node):
    """
    Returns the subsequent "if-type" (else if, or else).

    Parameters
    ----------
    if_statement_node : Can be "if_statment", "else_if_statement", or "else_statement" type.
    """
    if if_statement_node:
        if_set = {Extract_Hunk_AST_Util.Construct_Flow_Type.IF_STATEMENT,
                  Extract_Hunk_AST_Util.Construct_Flow_Type.ELSE_IF_STATEMENT,
                  Extract_Hunk_AST_Util.Construct_Flow_Type.ELSE_STATEMENT
                  }
        for child in if_statement_node.children:
            child_construct_flow_type = Extract_Hunk_AST_Util.get_node_construct_flow_type(child)
            if child_construct_flow_type in if_set:
                return child

    return None

#TODO:
def extract_control_flow_constructs(target_node, source_code, override_type: str = "", should_be_on_child_block: bool = True):
    # test_temp = Extract_Hunk_AST_Util.get_node_construct_flow_type(target_node)
    # match test_temp:
    #     case Extract_Hunk_AST_Util.Construct_Flow_Type.IF_STATEMENT:
    #         print("\n************IF STATEMENT*********")
    #         print(f'{Extract_Hunk_AST_Util.get_node_exact_string(target_node, source_code)}')
    #         print("***********************************\n")
    #     case Extract_Hunk_AST_Util.Construct_Flow_Type.ELSE_IF_STATEMENT:
    #         print("\n*******ELSE IF STATEMENT*********")
    #         print(f'{Extract_Hunk_AST_Util.get_node_exact_string(target_node, source_code)}')
    #         print("***********************************\n")
    #     case Extract_Hunk_AST_Util.Construct_Flow_Type.ELSE_STATEMENT:
    #         print("\n*******ELSE STATEMENT************")
    #         print(f'{Extract_Hunk_AST_Util.get_node_exact_string(target_node, source_code)}')
    #         print("***********************************\n")
    #     case _:
    #         print("\n*************default*************")
    #         print(f'{Extract_Hunk_AST_Util.get_node_exact_string(target_node, source_code)}')
    #         print("***********************************\n")
    if not target_node:
        print('1')
        return None
    
    if should_be_on_child_block:
        node_block = Extract_Hunk_AST_Util.get_node_block_child(target_node)
        if not node_block:
            print(f'{target_node.type}, should be on child block: {should_be_on_child_block}')
            return None
    else:
        # Some constructs don't have a block child. They usually contain the block in themeselves (like the switch cases)
        node_block = target_node

    if override_type == "":
        target_node_type = target_node.type
    else:
        target_node_type = override_type

    construct_flow_dict = {
        "Type" : target_node_type,
        "Children" : []
    }
    for child in node_block.children:
        child_construct_flow_type = Extract_Hunk_AST_Util.get_node_construct_flow_type(child)
        match child_construct_flow_type:
            case Extract_Hunk_AST_Util.Construct_Flow_Type.NONE:
                continue
            # IF, ELSE IF, ELSE:
            case Extract_Hunk_AST_Util.Construct_Flow_Type.IF_STATEMENT:
                construct_flow_dict["Children"].append(extract_control_flow_constructs(child, source_code))
                next_if = get_if_statement_next_if(child)
                while(next_if):
                    next_if_construct_flow_type = Extract_Hunk_AST_Util.get_node_construct_flow_type(next_if)
                    match next_if_construct_flow_type:
                        case Extract_Hunk_AST_Util.Construct_Flow_Type.ELSE_IF_STATEMENT:
                            
                            construct_flow_dict["Children"].append(extract_control_flow_constructs(next_if, source_code,"else_if_statement"))
                        case Extract_Hunk_AST_Util.Construct_Flow_Type.ELSE_STATEMENT:

                            construct_flow_dict["Children"].append(extract_control_flow_constructs(next_if, source_code,"else_statement"))
                        case _:
                            continue
                    next_if = get_if_statement_next_if(next_if)
            # FOR LOOP    
            case Extract_Hunk_AST_Util.Construct_Flow_Type.FOR_STATEMENT:
                construct_flow_dict["Children"].append(extract_control_flow_constructs(child, source_code))
            case Extract_Hunk_AST_Util.Construct_Flow_Type.WHILE_STATEMENT:
                construct_flow_dict["Children"].append(extract_control_flow_constructs(child, source_code))
            case Extract_Hunk_AST_Util.Construct_Flow_Type.DO_STATEMENT:
                construct_flow_dict["Children"].append(extract_control_flow_constructs(child, source_code))
            case Extract_Hunk_AST_Util.Construct_Flow_Type.ENHANCED_FOR_STATEMENT:
                construct_flow_dict["Children"].append(extract_control_flow_constructs(child, source_code))
            case Extract_Hunk_AST_Util.Construct_Flow_Type.SWITCH_EXPRESSION:
                # Have to find the body of the switch
                for switch_child in child.children:
                    if switch_child.type == "switch_block":
                        construct_flow_dict["Children"].append(extract_control_flow_constructs(switch_child, source_code,"switch", should_be_on_child_block= False))
            case Extract_Hunk_AST_Util.Construct_Flow_Type.SWITCH_CASE:
                construct_flow_dict["Children"].append(extract_control_flow_constructs(child, source_code,"switch_case", should_be_on_child_block= False))
            # JUMPS
            case Extract_Hunk_AST_Util.Construct_Flow_Type.BREAK_STATEMENT:
                break_dict = {
                    "Type" : child.type
                }
                construct_flow_dict["Children"].append(break_dict)
            case Extract_Hunk_AST_Util.Construct_Flow_Type.RETURN_STATEMENT:
                return_dict = {
                    "Type" : child.type
                }
                construct_flow_dict["Children"].append(return_dict)
            case Extract_Hunk_AST_Util.Construct_Flow_Type.CONTINUE_STATEMENT:
                continue_dict = {
                    "Type" : child.type
                }
                construct_flow_dict["Children"].append(continue_dict)
            
            # EXCEPTION
            case Extract_Hunk_AST_Util.Construct_Flow_Type.TRY_STATEMENT:
                construct_flow_dict["Children"].append(extract_control_flow_constructs(child, source_code, "try"))
                for try_child in child.children:
                    if try_child.type == "catch_clause":
                        construct_flow_dict["Children"].append(extract_control_flow_constructs(try_child, source_code, "catch"))
                    if try_child.type == "finally_clause":
                        construct_flow_dict["Children"].append(extract_control_flow_constructs(try_child, source_code, "finally"))
            case Extract_Hunk_AST_Util.Construct_Flow_Type.TRY_WITH_RESOURCE_STATEMENT:
                construct_flow_dict["Children"].append(extract_control_flow_constructs(child, source_code, "try_with_resource"))
                for try_child in child.children:
                    if try_child.type == "catch_clause":
                        construct_flow_dict["Children"].append(extract_control_flow_constructs(try_child, source_code, "catch"))
                    if try_child.type == "finally_clause":
                        construct_flow_dict["Children"].append(extract_control_flow_constructs(try_child, source_code, "finally"))                
            case Extract_Hunk_AST_Util.Construct_Flow_Type.THROW_STATEMENT:
                throw_dict = {
                    "Type" : child.type
                }
                construct_flow_dict["Children"].append(throw_dict)
            case _:
                continue
    return construct_flow_dict

#TODO:
def generate_structured_context_metadata(target_node, source_code):
    method_node = Extract_Hunk_AST_Util.get_context_parent_method(target_node)
    if not method_node:
        return None
    node_structured_context_metadaa = {
        "Encapsulating Class Information": extract_class_information(method_node, source_code, True),
        "Package Information": extract_package_information(),
        "Globally Imported Libraries": extract_imported_libraries(),
        "Invoked Methods" : extract_called_methods(method_node, source_code),
        "Referenced Classes" : extract_referenced_classes(method_node, source_code),
        "Neighboring Methods" : extract_neighboring_methods_within_same_class(method_node, source_code),
        "Control-Flow Constructs": extract_control_flow_constructs(method_node, source_code)
    }
    return node_structured_context_metadaa