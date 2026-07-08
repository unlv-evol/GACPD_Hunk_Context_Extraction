import json
import os
import sys
import re
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_java as tsjava
from enum import Enum

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
import Extract_Hunk_AST

class Construct_Flow_Type(Enum):
    NONE = 0
    IF_STATEMENT = 1
    FOR_STATEMENT = 2
    WHILE_STATEMENT = 3
    DO_STATEMENT = 4
    ENHANCED_FOR_STATEMENT = 5
    ELSE_IF_STATEMENT = 6
    ELSE_STATEMENT = 7
    SWITCH_EXPRESSION = 8
    SWITCH_CASE = 9
    BREAK_STATEMENT = 10
    RETURN_STATEMENT = 11
    CONTINUE_STATEMENT = 12
    TRY_STATEMENT = 13
    TRY_WITH_RESOURCE_STATEMENT = 14 
    THROW_STATEMENT = 15  
# region GLOBAL VARIABLES
context_is_import_mode = False

# endregion

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
                return None
        
        if context_node.type == "program":
            return None
        
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
                return None
        
        if context_node.type == "program" or context_node.type == "class_declaration":
            return None
        
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

def get_method_signature (method_context_node, source_code) -> str:
    """
    Returns a string that contains the signature of the inputted method context node.

    Parameters
    ----------
    method_context_node : The tree-sitter node of the target method.
    source_code : The source code of the file that contains the method in text

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
        # source_code = source_code.encode('utf-8')
        signature_parts.append(source_code[child.start_byte:child.end_byte])

    method_signature = " ".join(signature_parts).strip()
    method_signature = method_signature.replace(' (', '(')

    return method_signature

def get_node_block_child(node):
    """
    Gets the block node in the provided tree-sitter node.
    """
    if node:
        if node.type == "block":
            return node
        
        for child_node in node.children:
            if child_node.type == "block":
                return child_node
    
    return None

def get_node_construct_flow_type(node):
    """
    Returns an enum Construct_Flow_Type that will specify what type of 
    construct type the provided node is, if at all.
    """
    if not node:
        return Construct_Flow_Type.NONE
    
    # Iteration Statements(while, do-while, for, enhanced for)
    if node.type == "for_statement": 
        return Construct_Flow_Type.FOR_STATEMENT
    if node.type == "while_statement":
        return Construct_Flow_Type.WHILE_STATEMENT
    if node.type == "do_statement":
        return Construct_Flow_Type.DO_STATEMENT
    if node.type == "enhanced_for_statement":
        return Construct_Flow_Type.ENHANCED_FOR_STATEMENT
    
    # Selection Statements (if, else if, else, switch, switch case)
    if node.type == "if_statement":
        if node.prev_sibling:
            if node.prev_sibling.type == "else":
                return Construct_Flow_Type.ELSE_IF_STATEMENT
        return Construct_Flow_Type.IF_STATEMENT
    if node.type == "block":
        if node.prev_sibling:
            if node.prev_sibling.type == "else":
                return Construct_Flow_Type.ELSE_STATEMENT
    if node.type == "switch_expression":
        return Construct_Flow_Type.SWITCH_EXPRESSION
    if node.type == "switch_block_statement_group":
        return Construct_Flow_Type.SWITCH_CASE
    
    # Jumps
    if node.type == "break_statement":
        return Construct_Flow_Type.BREAK_STATEMENT
    if node.type == "return_statement":
        return Construct_Flow_Type.RETURN_STATEMENT
    if node.type == "continue_statement":
        return Construct_Flow_Type.CONTINUE_STATEMENT

    # Exceptions 
    if node.type == "try_statement":
        return Construct_Flow_Type.TRY_STATEMENT
    if node.type == "try_with_resources_statement":
        return Construct_Flow_Type.TRY_WITH_RESOURCE_STATEMENT
    if node.type == "throw_statement":
        return Construct_Flow_Type.THROW_STATEMENT

    # Ternary Expression
    if node.type in { "ternary_expression"}:
        return Construct_Flow_Type.NONE


    return Construct_Flow_Type.NONE
# Predicates

def is_context_in_method (context_node):
    """
    Returns whether the inputted node is in a method or not.

    Parameters
    ----------
    context_node : The tree-sitter node that will be the subject of the search.

    Returns
    -------
    Boolean : Whether the inputted node was in a method or not.
    """
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
    """
    Returns whether the inputted node is in a class or not.

    Parameters
    ----------
    context_node : The tree-sitter node that will be the subject of the search.

    Returns
    -------
    Boolean : Whether the inputted node was in a class or not.
    """
    if not context_node:
        return False
    if context_node.type == "program":
        return False
    while context_node.parent:
        if context_node.type == "class_declaration":
            return True
        context_node = context_node.parent
    
    return False

def is_context_in_class_or_method (context_node):
    """
    Finds out whether the inputted context node is either in a class and/or method.

    Parameters
    ----------
    context_node : The tree-sitter node that will be the subject of the search.

    Returns
    -------
    Boolean : Whether the inputted context_node is in a method and/or class or not.
    """
    if not context_node:
        return False
    if context_node.type == "program":
        return False
    while context_node.parent:
        if context_node.type == "method_declaration" or context_node.type == "class_declaration":
            return True
        context_node = context_node.parent
    
    return False

def determine_hunk_import_mode (source_code_lines, hunk_start_line, hunk_end_line):
    """
    Will set the value of Extract_Hunk_AST_Util.context_is_import_mode to either true or false depending
    on if all of the lines of the hunk are (import or package) lines or not. 

    Parameters
    ----------
    source_code_lines:  The lines of the source code arranged in a list (use readlines() on the file).
    hunk_start_line :   The number of the starting line of the hunk (inclusive) (first line is 0).
    hunk_end_line:      The number of the ending line of the hunk (inclusive) (first line is 0).

    Returns
    -------
    This function is void type and does not return anything. Instead it sets the value of 
    Extract_Hunk_AST_Util.context_is_import_mode to either True or False. After calling this function,
    Extract_Hunk_AST_Util.context_is_import_mode can be used to determine if the inputted hunk is import mode or not.

    """
    global context_is_import_mode
    for line_num, line_content in enumerate(source_code_lines[hunk_start_line: hunk_end_line + 1], start= hunk_start_line):
        line_content_stripped = line_content.strip()
        # Skipping empty and comment lines
        if not line_content_stripped or line_content_stripped.startswith('*') or line_content_stripped.startswith('/'):
            continue
        
        if not line_content_stripped.startswith('import') and not line_content.startswith('package'):
            context_is_import_mode = False
            return
        # The else here is necessary in case an emtpy line is fed to the function
        # Otherwise we could just set context_is_import_mode to True at the end of the function.
        else:
            context_is_import_mode = True
    
    return


# endregion

def get_file_content(file_address):
    with open(file_address, 'r') as f:
        return f.read()
    
def get_node_exact_string(node, source_code_text):
    source_code_lines = source_code_text.splitlines()
    start_row, start_col = node.start_point
    end_row, end_col = node.end_point

    node_lines = source_code_lines[start_row:end_row + 1]

    if start_row == end_row:
        exact_string = node_lines[0][start_col:end_col + 1]
    else:
        node_lines[0] = node_lines[0][start_col:]
        node_lines[-1] = node_lines[-1][:end_col + 1]
        exact_string = "\n".join(node_lines)

    return exact_string

def get_node_list_exact_string(node_list, source_file_text):
    output = []
    if node_list:
        for node in node_list:
            output.append(f'{get_node_exact_string(node, source_file_text)}') 
    
    return output

def get_clean_name(messy_name: str):
    """
    Removes any non-letter and non-digit characters from the provided string.
    """
    cleaned_name = re.sub(r'[^a-zA-Z0-9]', '', messy_name)
    return cleaned_name


def sort_nodes_by_start_point(nodes):
    """
    Sort the provided list of tree-sitter nodes by their starting points,
    first by line, then by row.
    """
    sorted_nodes = sorted(
        nodes,
        key = lambda node: node.start_point
    )
    return sorted_nodes

# region IMPORT DECLARATIONS
def get_current_AST_import_declarations():
        """
        Gets all the import nodes in the current generated AST
        (which is generated by calling Extract_Hunk_AST.find_context_node())
        """
        if Extract_Hunk_AST.current_generated_AST:
            query_string = """
            (import_declaration) @import
            """
            JAVA_LANGUAGE = Language(tsjava.language())
            query = Query(JAVA_LANGUAGE, query_string)
            cursor = QueryCursor(query)
            captures = cursor.captures(Extract_Hunk_AST.current_generated_AST.root_node)
            return captures['import']
        else:
            return None
        
def get_current_AST_import_declarations_classes(file_content):
    """
    Returns the class name for the imports in the source file. 
    Requires the text for the source code to be passed in via the parameter.
    """
    imports = get_current_AST_import_declarations()
    imports = sort_nodes_by_start_point(imports)
    import_classes = []
    for individual_import in imports:
        for child in individual_import.children:
            if child.type == "scoped_identifier":
                import_text = get_node_exact_string(child, file_content)
                if '.' in import_text:
                    class_text = import_text.split('.')[-1]
                    if ';' in class_text:
                        class_text = class_text.split(';')[0]
                    import_classes.append(class_text)
    return import_classes
# endregion


