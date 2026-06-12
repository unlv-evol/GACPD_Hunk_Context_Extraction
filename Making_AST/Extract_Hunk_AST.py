import json
import sys
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_java as tsjava



def node_to_dict(node_is_import, node, source_code):
    """
    Converts a tree-sitter node to a dictionary ready for json saving.
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
    Finds the context of a section of the source code (in bytes). The section
    is specified using its beginning and end line positions.
    """
    context_is_import = False
    
    JAVA_LANGUAGE = Language(tsjava.language())
    parser = Parser(JAVA_LANGUAGE)

    tree = parser.parse(code_bytes)
    node = tree.root_node.named_descendant_for_point_range(target_point_start, target_point_end)


    # If the node is an import node, we will only return the imports
    # sections as immediate context and nothing for block context.
    if node.type == "import_declaration" or node.type == "package_declaration":
        query_string = """
        (import_declaration) @import_or_package_node
        (package_declaration) @import_or_package_node
        """
        query = Query(JAVA_LANGUAGE, query_string)
        cursor = QueryCursor(query)
        immediate_context = cursor.captures(tree.root_node)
        context_is_import = True 
        block_context = {}
    else:
        if node.type == "program":
            block_context= {}
            return False, node, {}
    
        immediate_context = node.parent
        if immediate_context.type != "program":
            block_context = node.parent
            while(block_context.type != "class_declaration" and block_context.type != "method_declaration" and block_context.type != "program"):
                block_context= block_context.parent
            if immediate_context == block_context:
                block_context = {}
        else:
            block_context = {}
    return context_is_import, immediate_context, block_context




def extract_hunk_context_from_file(java_file_address, hunk_start_line , hunk_end_line):
    
    with open(java_file_address) as java_file:
        java_code = java_file.read()
        code_bytes = bytes(java_code, "utf8")
        target_point_start = (hunk_start_line, 0)
        target_point_end = (hunk_end_line, 0)
        context_is_import, immediate_context, block_context = find_context_node(code_bytes, target_point_start, target_point_end)

        immediate_context_AST_dict = node_to_dict(context_is_import, immediate_context, code_bytes)
        
        if context_is_import: 
            immediate_context_source_code = java_code.splitlines()[int(immediate_context_AST_dict['first import line']):int(immediate_context_AST_dict['last import line'])+1]
            block_context_source_code = ""
            block_context_AST_dict = {}
        else:
            immediate_context_source_code = java_code.splitlines()[immediate_context.start_point[0]:immediate_context.end_point[0]+1]
            # Sometiems the block context and immediate context are the same, in which case to preserve space we don't 
            # write the block context (the find_context_node function above returns a null block_context).
            if block_context:
                block_context_source_code = java_code.splitlines()[block_context.start_point[0]:block_context.end_point[0]+1]
                block_context_AST_dict = node_to_dict(context_is_import, block_context, code_bytes)
            else:
                block_context_source_code = ""
                block_context_AST_dict = {}

        context_AST_output = {
            "Is Context Import" : context_is_import,
            "Immediate Context AST Representaion": immediate_context_AST_dict,
            "Block Context AST Representation": block_context_AST_dict
        }

        context_source_code_output = {
            "Is Context Import" : context_is_import,
            "Immediate Context Source Code": immediate_context_source_code,
            "Block Context Source Code": block_context_source_code
        }


        return context_AST_output, context_source_code_output






