import json
import Config
from GACPD_Output_Processing.GACPD_Result_Processing import save_GACPD_result_data
from Making_AST.GACPD_Hunk_Info_Processing import get_GACPD_hunk_info
from Making_AST.Extract_Hunk_AST import extract_hunk_context_from_file





def main ():
    # save_GACPD_result_data()
    GACPD_hunks_info = get_GACPD_hunk_info()
    for pr in GACPD_hunks_info:
         print(f'PR number: {pr["PR number"]}{pr["PR classification"]}')
         for classification in pr['classifications']:
              print(f'  File classification category: {classification["classification type"]}')
              for file in classification['files']:
                   print(f'     file name: {file["file name"]}')


    context_tree =extract_hunk_context_from_file('Making_AST/temporary_test/test_file_light.java', 24, 24)

    with open('Making_AST/temporary_output_folder/test_context_output.json', 'w', encoding = "utf-8") as output_json:
            json.dump(context_tree, output_json, indent= 2)





if __name__ == "__main__":
    main()