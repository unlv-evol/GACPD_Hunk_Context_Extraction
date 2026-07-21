import json
import sys
import os
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_java as tsjava

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
import Extract_Hunk_AST_Util

def get_import_hunk_source_code(source_code, hunk_start_line, hunk_end_line):
    """
    This function only returns the imports around the specified hunk
    (usually at the top of the file). It WILL NOT return all of the imports
    in the file if there are imports elsewhere from the surrounding lines of the hunk.
    """
    source_code_lines = source_code.splitlines()
    imports = []
    for line in reversed(source_code_lines[:hunk_start_line + 1]):
        line_stripped = line.strip()
        # Skipping empty and comment lines
        if not line_stripped or line_stripped.startswith('*') or line_stripped.startswith('/'):
            continue
        if line_stripped.startswith('import') or line_stripped.startswith('package'):
            imports.insert(0 , line_stripped)
        else:
            break
    for line in (source_code_lines[hunk_start_line:hunk_end_line + 1]):
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith('*') or line_stripped.startswith('/'):
            continue
        if line_stripped.startswith('import') or line_stripped.startswith('package'):
            imports.append(line_stripped)
        else:
            break
    
    for line in (source_code_lines[hunk_end_line:]):
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith('*') or line_stripped.startswith('/'):
            continue
        if line_stripped.startswith('import') or line_stripped.startswith('package'):
            imports.append(line_stripped)
        else:
            break
    
    #imports_string = '\n'.join(imports)
    
    return imports

def context_node_to_dict(node, source_code, short_mode: bool = False):
    """
    Converts a tree-sitter node to a dictionary ready for json saving and debug printing.

    Parameters
    ----------
    node :              The context node from which the data for the dictionary will be extracted.
    source_code :       The source code that contains the text of the node. The source code should be in bytes.

    Returns
    -------
    node_dict :         A dictionary that contains the info for the context to either be printed or saved.
                        The format of the dictionary might change depending on whether the provided context 
                        node is "import" context or not.
    """
    
    if short_mode:
        node_dict = {
            "type": node.type,
            "children": []
        }
    else:
        node_text = Extract_Hunk_AST_Util.get_node_exact_string(node, source_code)
        node_dict = {
            "type": node.type,
            "start_point": [node.start_point[0], node.start_point[1]],
            "end_point": [node.end_point[0], node.end_point[1]],
            "text": node_text,
            "children": []
        }

    for child in node.children:
        node_dict["children"].append(context_node_to_dict(child, source_code, short_mode))
            
    return node_dict

def find_context_node(AST, target_point_start, target_point_end):
    """
    Finds and returns the context of a section of the source code.

    Parameters
    ----------
    code_bytes : The source code of the specified hunk in bytes.
    target_point_start: A tuple that specifies the beginning row and column of the hunk.
    target_point_end : A tuple that specifies the ending row and cloumn of the hunk.

    Returns
    -------
    immediate_context : The closest encapsulating context of the hunk. 
                        This can be an if block, a try block, or any other type of context.
    method_context :    The context of the encapsulating method.
    """
    
    immediate_context = {}
    method_context = {}

    # Finding the named node for the point range
    node = AST.root_node.named_descendant_for_point_range(target_point_start, target_point_end)

    if not node:
        print(f'WARNING: in function find_context_node, could not find named node for point range.')
    else: 
        if node.type == "program":
            immediate_context = node
        else:
            immediate_context = node.parent
            if Extract_Hunk_AST_Util.is_context_in_method(immediate_context):
                method_context = Extract_Hunk_AST_Util.get_context_parent_method(immediate_context)
                if immediate_context == method_context:
                    immediate_context = {}

    return immediate_context, method_context

def get_hunk_context_info(AST, java_code, hunk_start_line , hunk_end_line):
    """
    Returns the context of a hunk based on its starting and ending lines.

    Parameters
    ----------
    java_code : The code (string) of the source file that contains the hunk.
    hunk_start_line : The starting line of the hunk. This is inclusive.
    hunk_end_line : The ending line of the hunk. This is inclusive.

    Returns
    -------
    context_AST_output :    The Abstract Syntax Tree representation of the context of the provided hunk.
                            Will contain both the immediate and block contexts.
    context_source_code_output :    The associated source code of the context of the provided hunk.
                                    Will contain both the immediate and block contexts.
    """
    


    immediate_context_AST_dict = {}
    method_context_AST_dict = {}
    immediate_context_source_code = ""
    method_context_source_code = ""
    is_hunk_import = Extract_Hunk_AST_Util.is_hunk_import(java_code, hunk_start_line, hunk_end_line)

    if is_hunk_import: 
        # When the hunk is in the imports section, we will not be working with tree-sitter nodes.
        immediate_context_source_code = get_import_hunk_source_code(java_code, hunk_start_line, hunk_end_line)
    else:
        hunk_start_position = (hunk_start_line, 0)
        hunk_end_position = (hunk_end_line, 0)
        immediate_context, method_context = find_context_node(AST, hunk_start_position, hunk_end_position )
        # Sometimes the method and the immediate context are the same, in which case the immediate will be left out as 
        # empty and the method context will contain the context.
        if immediate_context:
            immediate_context_AST_dict = context_node_to_dict(immediate_context, java_code, short_mode= True)
            immediate_context_source_code = Extract_Hunk_AST_Util.get_node_exact_string(immediate_context, java_code).splitlines()
        if method_context:
            method_context_AST_dict = context_node_to_dict(method_context, java_code, short_mode= True)
            method_context_source_code = java_code.splitlines()[method_context.start_point[0]:method_context.end_point[0]+1]
    hunk_source_code = java_code.splitlines()[int(hunk_start_line):int(hunk_end_line) + 1]
    context_AST_output = {
        "Is_Hunk_Import" : is_hunk_import,
        "Immediate_AST": immediate_context_AST_dict,
        "Method_AST": method_context_AST_dict
    }

    context_source_code_output = {
        "Is_Hunk_Import" : is_hunk_import,
        "Immediate_SC": immediate_context_source_code,
        "Method_SC": method_context_source_code
    }


    return context_AST_output, context_source_code_output

def find_adjacent_context(context_node):
    """
    Returns the previous and next method and class relative to the provided context node

    Parameters
    ----------
    context_node : Tree-sitter node. Does not have to be a "block context"

    Returns
    -------
    previous_method : context of the previous method relative to the provided context node
    next_method : context of the next method relative to the provided context node
    previous_class : context of the previous class relative to the provided context node
    next_class : context of the next class relative to the provided context node
    
    """
    if not context_node.type == "method_declaration" and not context_node.type == "class_declaration":
        while not context_node.type == "method_declaration" and not context_node.type == "class_declaration" and not context_node.type == "program":
            context_node = context_node.parent
        
    previous_class,next_class,previous_method,next_method = [{} for _ in range(4)]
    
    if context_node.type == "class_declaration":
        # PREVIOUS CLASS
        previous_sibling = context_node.prev_named_sibling
        if previous_sibling:
            while previous_sibling.type != "class_declaration":
                previous_sibling = previous_sibling.prev_named_sibling
                if not previous_sibling:
                    break
        previous_class = previous_sibling

        # NEXT CLASS
        next_sibling = context_node.next_named_sibling
        if next_sibling:
            while next_sibling.type != "class_declaration":
                next_sibling = next_sibling.next_named_sibling
                if not next_sibling:
                    break
        next_class = next_sibling
        
        # PREVIOUS METHOD
        previous_method = {}
        # NEXT METHOD
        next_method = {}

    if context_node.type == "method_declaration":

        # PREVIOUS METHOD
        previous_sibling = context_node.prev_named_sibling
        if previous_sibling:
            while previous_sibling.type != "method_declaration":
                previous_sibling = previous_sibling.prev_named_sibling
                if not previous_sibling:
                    break
        previous_method = previous_sibling

        # NEXT METHOD
        next_sibling = context_node.next_named_sibling
        if next_sibling:
            while next_sibling.type != "method_declaration":
                next_sibling = next_sibling.next_named_sibling
                if not next_sibling:
                    break
        next_method = next_sibling

        # Finding the encapsulating class for the method
        while(context_node.type != "class_declaration" and context_node.type != "program"):
            context_node = context_node.parent
            if not context_node:
                break
        
        if context_node:
            if context_node.type == "class_declaration":
                # PREVIOUS CLASS
                previous_sibling = context_node.prev_named_sibling
                if previous_sibling:
                    while previous_sibling.type != "class_declaration":
                        previous_sibling = previous_sibling.prev_named_sibling
                        if not previous_sibling:
                            break
                previous_class = previous_sibling

                # NEXT CLASS
                next_sibling = context_node.next_named_sibling
                if next_sibling:
                    while next_sibling.type != "class_declaration":
                        next_sibling = next_sibling.next_named_sibling
                        if not next_sibling:
                            break
                next_class = next_sibling

    
    return previous_method, next_method, previous_class, next_class
