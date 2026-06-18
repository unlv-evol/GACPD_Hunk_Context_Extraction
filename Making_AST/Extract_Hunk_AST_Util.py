import json
import sys
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_java as tsjava
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
    Returns a string that contains the signature of the inputted method context node.

    Parameters
    ----------
    method_context_node : The tree-sitter node of the target method.
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
