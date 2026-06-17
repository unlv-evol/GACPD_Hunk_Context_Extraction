import json
import sys
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_java as tsjava

# region UTIL FUNCTIONS

# Getters
def get_context_parent_class(context_node):
    """
    Gets the class that contains the provided context node.

    Parameters
    ----------
    context_node : A context that is located in a class.

    Returns
    -------
    context_node : The context of the parent class of the provided input context.
    """
    if context_node:
        while context_node.type != "class_declaration" and context_node.type != "program":
            context_node = context_node.parent
            if not context_node:
                return {}
        
        if context_node.type == "program":
            return {}
        
    return context_node

def get_context_parent_method (context_node):
    """
    Gets the parent method of the provided context.

    Parameters
    ----------
    context_node : The context that is located in a method.

    Returns
    -------
    context_node : The context of the parent method.
    """
    if context_node:
        while context_node.type != "class_declaration" and context_node.type != "program" and context_node.type != "method_declaration":
            context_node = context_node.parent
            if not context_node:
                return {}
        
        if context_node.type == "program" or context_node.type == "class_declaration":
            return {}
        
    return context_node

def get_context_parent_block (context_node):
    """
    Gets either the method or the class that contains the provided context_node.

    Parameters
    ----------
    context_node : The tree-sitter node to find the context parent block of.

    Returns
    -------
    context_node : The parent block of the provided context.
    """
    if context_node:
        while context_node.type != "class_declaration" and context_node.type != "program" and context_node.type != "method_declaration":
            context_node = context_node.parent
            if not context_node:
                return {}
        
        if context_node.type == "program" :
            return {}

    return context_node

def get_method_signature (method_context_node, source_code: bytes) -> str:
    """
    Returns a string that contains the signature part of a method

    Parameters
    ----------
    method_context_node : The tree-sitter node of the targeted method.
    source_code : The source code of the file that contains the method, in bytes.

    Returns
    -------
    method_signature : A string that contains the signature of the method.
    """
    if not method_context_node:
        print('WARNING: Passed null method context node to get_method_signature')
        return""
    if method_context_node.type != "method_declaration":
        print(f'WARNING: Passed non-method node to get_method_signature. The node is {method_context_node.type}')   
        return""
    
    signature_parts = []
    for child in method_context_node.children:
        if child.type == 'block':
            break

        signature_parts.append(source_code[child.start_byte:child.end_byte].decode('utf-8'))

    method_signature = " ".join(signature_parts).strip()
    method_signature = method_signature.replace(' (', '(')

    return method_signature

# Predicates

def is_context_in_method (context_node):
    if not context_node:
        return False
    if context_node.type == "program":
        return False
    while context_node.parent:
        if context_node.type == "method_declaration":
            return True
        context_node = context_node.parent
    
    return False

def is_context_in_class (context_node):
    pass

def is_context_in_class_or_method (context_node):
    pass

def is_context_import_mode (context_node):
    if not context_node:
        return False
    
    # Sometimes a dict of import nodes might be passed into this function.
    if 'import_or_package_node' in context_node:
        return True
    if context_node.type == "import_declaration" or context_node.type == "package_declaration":
        return True
    return False

# endregion


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
    context_is_import : A boolean that specifies if the context of the hunk is an "import" context,
                        meaning that it only contains "import" and "package" lines.
    immediate_context : The immediate context of the hunk. This can be a try block or an if block. 
    block_context :     The "block" context of the hunk. The type of this context will 
                        always be one of method declaration, class declaration, or program.
                        NOTE: If the immediate_context and block_context are equal to each other, 
                        then block_context will be return empty and immediate_context will represent
                        both of them (since they are equal).
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

def main():

    test_hunk_start_line = 35
    test_hunk_end_line = 35
    test_file = "temporary_test/test_file_light.java"
    with open(test_file) as java_file:
        java_code = java_file.read()
        code_bytes = bytes(java_code, "utf8")
        target_point_start = (test_hunk_start_line, 0)
        target_point_end = (test_hunk_end_line, 0)
        context_is_import, immediate_context, block_context = find_context_node(code_bytes, target_point_start, target_point_end)

    
    if not is_context_import_mode(immediate_context): 
        if is_context_in_method(immediate_context):
            print_thing = 'is'
        else:
            print_thing = 'is not'
    else:
        print_thing = 'is not'
    print(f'the provided context {print_thing} in a function')

    sys.exit()
    prev_method, next_method, prev_class, next_class = find_adjacent_context(immediate_context)

    with open('temporary_output_folder/around_context.json', 'w') as outfile:
        if immediate_context:
            immediate_context_text =  java_code.splitlines()[immediate_context.start_point[0]:immediate_context.end_point[0]+1]
        else:
            immediate_context_text= ""
        if prev_method:
            prev_method_text = java_code.splitlines()[prev_method.start_point[0]:prev_method.end_point[0]+1]
        else:
            prev_method_text = ""
        if next_method:
            next_method_text = java_code.splitlines()[next_method.start_point[0]:next_method.end_point[0]+1]
        else:
            next_method_text = ""
        if prev_class:
            prev_class_text= java_code.splitlines()[prev_class.start_point[0]:prev_class.end_point[0]+1]
        else:
            prev_class_text = ""
        if next_class:
            next_class_text = java_code.splitlines()[next_class.start_point[0]:next_class.end_point[0]+1]
        else:
            next_class_text = ""
        test_output_dic = {
            "immediate context type": immediate_context.type,
            "prev method": prev_method_text,
            "next method": next_method_text,
            "prev class": prev_class_text,
            "next class": next_class_text
        }



        json.dump(test_output_dic, outfile, indent = 2)

    

if __name__ == "__main__":
    main()


