import json
import sys
import os
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_java as tsjava

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
import Extract_Hunk_AST_Util

def node_to_dict(node_is_import, node, source_code):
    """
    Converts a tree-sitter node to a dictionary ready for json saving and debug printing.

    Parameters
    ----------
    node_is_import :    A boolean that specifies whether the provided context node is "import" context node.
    node :              The context node from which the data for the dictionary will be extracted.
    source_code :       The source code that contains the text of the node. The source code should be in bytes.

    Returns
    -------
    node_dict :         A dictionary that contains the info for the context to either be printed or saved.
                        The format of the dictionary might change depending on whether the provided context 
                        node is "import" context or not.
    """
    
    if node_is_import:
        import_nodes = node['import_or_package_node']
        first_import_line = import_nodes[0].start_point[0]
        last_import_line = import_nodes[0].end_point[0]
        for individual_import_node in import_nodes:
            if individual_import_node.start_point[0] < first_import_line:
                first_import_line = individual_import_node.start_point[0]
            if individual_import_node.end_point[0] > last_import_line:
                last_import_line = individual_import_node.end_point[0]
        node_dict = {
            "first import line": first_import_line,
            "last import line": last_import_line
        }       
    else:
        node_text = source_code[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
        node_dict = {
            "type": node.type,
            "is_named": node.is_named,
            # "start_byte": node.start_byte,
            # "end_byte": node.end_byte,
            "start_point": [node.start_point[0], node.start_point[1]],  # [row, column]
            "end_point": [node.end_point[0], node.end_point[1]],
            "text": node_text,
            "children": []
        }

        for child in node.children:
            node_dict["children"].append(node_to_dict(False, child, source_code))
            
    return node_dict

def find_context_node(code_bytes, target_point_start, target_point_end):
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
    class_context :     The context of the encapsulating class.
    """
    immediate_context = {}
    method_context = {}
    class_context = {}

    # Finding the named node for the point range
    JAVA_LANGUAGE = Language(tsjava.language())
    parser = Parser(JAVA_LANGUAGE)
    tree = parser.parse(code_bytes)
    node = tree.root_node.named_descendant_for_point_range(target_point_start, target_point_end)

    if not node:
        print(f'WARNING: in function find_context_node, could not find named node for point range.')
    else: 
        # If the node is an import node, we will only return the imports
        # sections as immediate context and nothing for block context.
        if Extract_Hunk_AST_Util.context_is_import_mode:
            query_string = """
            (import_declaration) @import_or_package_node
            (package_declaration) @import_or_package_node
            """
            query = Query(JAVA_LANGUAGE, query_string)
            cursor = QueryCursor(query)
            immediate_context = cursor.captures(tree.root_node)
        else:
            if node.type == "program":
                immediate_context = node
            else:
                # If the node is not the global scope ("program"), then the immediate context is always the parent of the node.
                immediate_context = node.parent

                if Extract_Hunk_AST_Util.is_context_in_method(immediate_context):
                    method_context = Extract_Hunk_AST_Util.get_context_parent_method(immediate_context)
                if Extract_Hunk_AST_Util.is_context_in_class(immediate_context):
                    class_context = Extract_Hunk_AST_Util.get_context_parent_class(immediate_context)

    return immediate_context, method_context, class_context

#TODO: Change this function's name to better indicate what it actually does and 
#      remove any confusion about its difference with the 'find_context_node' function.
def extract_hunk_context_from_file(java_file_address, hunk_start_line , hunk_end_line):
    """
    Returns the context of a hunk based on its starting and ending lines.

    Parameters
    ----------
    java_file_address : Address of the original file that contains the specified hunk (and other hunks).
    hunk_start_line : The starting line of the hunk. This is inclusive.
    hunk_end_line : The ending line of the hunk. This is inclusive.

    Returns
    -------
    context_AST_output :    The Abstract Syntax Tree representation of the context of the provided hunk.
                            Will contain both the immediate and block contexts.
    context_source_code_output :    The associated source code of the context of the provided hunk.
                                    Will contain both the immediate and block contexts.
    """
    
    with open(java_file_address) as java_file:
        Extract_Hunk_AST_Util.determine_hunk_import_mode(java_file.readlines(), hunk_start_line, hunk_end_line)
        java_file.seek(0)
        java_code = java_file.read()
        code_bytes = bytes(java_code, "utf8")
        target_point_start = (hunk_start_line, 0)
        target_point_end = (hunk_end_line, 0)
        immediate_context, method_context, class_context = find_context_node(code_bytes, target_point_start, target_point_end)

        immediate_context_AST_dict = {}
        method_context_AST_dict = {}
        class_context_AST_dict = {}
        immediate_context_source_code = ""
        method_context_source_code = ""
        class_context_source_code = ""

        immediate_context_AST_dict = node_to_dict(Extract_Hunk_AST_Util.context_is_import_mode, immediate_context, code_bytes)
        
        if Extract_Hunk_AST_Util.context_is_import_mode: 
            immediate_context_source_code = java_code.splitlines()[int(immediate_context_AST_dict['first import line']):int(immediate_context_AST_dict['last import line'])+1]
        else:
            immediate_context_source_code = java_code.splitlines()[immediate_context.start_point[0]:immediate_context.end_point[0]+1]
            # Sometiems the block context and immediate context are the same, in which case to preserve space we don't 
            # write the block context (the find_context_node function above returns a null method_context).
            if method_context:
                method_context_source_code = java_code.splitlines()[method_context.start_point[0]:method_context.end_point[0]+1]
                method_context_AST_dict = node_to_dict(Extract_Hunk_AST_Util.context_is_import_mode, method_context, code_bytes)
            if class_context:
                class_context_source_code = java_code.splitlines()[class_context.start_point[0]:class_context.end_point[0]+1]
                class_context_AST_dict = node_to_dict(Extract_Hunk_AST_Util.context_is_import_mode, class_context, code_bytes)

        context_AST_output = {
            "Is Context Import" : Extract_Hunk_AST_Util.context_is_import_mode,
            "Immediate Context AST Representaion": immediate_context_AST_dict,
            "Method Context AST Representation": method_context_AST_dict,
            "Class Context AST Represenetation": class_context_AST_dict
        }

        context_source_code_output = {
            "Is Context Import" : Extract_Hunk_AST_Util.context_is_import_mode,
            "Immediate Context Source Code": immediate_context_source_code,
            "Method Context Source Code": method_context_source_code,
            "Class Context Source Code": class_context_source_code
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
