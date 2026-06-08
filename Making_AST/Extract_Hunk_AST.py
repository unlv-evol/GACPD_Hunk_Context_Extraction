import json
import sys
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_java as tsjava



def node_to_dict(node_is_import, node, source_code):
    
    if node_is_import:
        import_nodes = node['import_node']
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
            node_dict["children"].append(node_to_dict(child, source_code))
            
    return node_dict




def find_context_node(code_bytes, target_point_start, target_point_end):
    
    context_is_import = False
    
    JAVA_LANGUAGE = Language(tsjava.language())
    parser = Parser(JAVA_LANGUAGE)

    tree = parser.parse(code_bytes)
    node = tree.root_node.named_descendant_for_point_range(target_point_start, target_point_end)

    # If the node is an import node, we will only return the imports
    # sections as context.
    if node.type == "import_declaration":
        query_string = "(import_declaration) @import_node"
        query = Query(JAVA_LANGUAGE, query_string)
        cursor = QueryCursor(query)
        context = cursor.captures(tree.root_node)
        context_is_import = True 
    else:
        #TODO: return the parent node and the encapsulating method/class declaration node.
        context= node.parent

    print(f'TEST PRING: PARENT TYPE: {node.parent.type}')
    return context_is_import, context




def main():

    #********************************************************
    #****************** DEBUG SECTION ***********************
    java_file_address = 'temporary_test/test_file_light.java'
    if not len(sys.argv) > 2:
        print('DEBUG ERROR: please provide line number as command line argumnet')
        print('USAGE: python Extract_Hunk_AST.py {line number}')
        sys.exit()

    target_point_start = (int(sys.argv[1]), 0)
    target_point_end = (int(sys.argv[1]), 0)
    #********************************************************
    #********************************************************
    
    with open(java_file_address) as java_file:
        java_code = java_file.read()
        code_bytes = bytes(java_code, "utf8")
        context_is_import, context = find_context_node(code_bytes, target_point_start, target_point_end)
        context_AST_dict = node_to_dict(context_is_import, context, code_bytes)
        if context_is_import: 
            context_source_code = java_code.splitlines()[int(context_AST_dict['first import line']):int(context_AST_dict['last import line'])+1]
        else:
            context_source_code = java_code.splitlines()[context.start_point[0]:context.end_point[0]+1]

        context_output = {
            "Is Context Import" : context_is_import,
            "Context AST Representaion": context_AST_dict,
            "Context Source Code": context_source_code
        }


        with open('temporary_output_folder/test_context_output.json', 'w', encoding = "utf-8") as output_json:
            json.dump(context_output, output_json, indent= 2)


if __name__ == "__main__":
    main()




