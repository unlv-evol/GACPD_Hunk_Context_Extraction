import json
import Config
import os
import sys
import argparse
from pathlib import Path
from GACPD_Output_Processing.GACPD_Result_Processing import save_GACPD_result_data
from Making_AST.GACPD_Hunk_Info_Processing import get_GACPD_hunk_info
from Making_AST.Extract_Hunk_AST import extract_hunk_context_from_file

def get_safe_abs_path(file_path):
     """
     Returns OS safe absolute paths. Will return long paths for Windows
     """
     if os.name == 'nt':
          abs_path = "\\\\?\\" + os.path.normpath(os.path.abspath(file_path))
     else:
          abs_path = os.path.abspath(file_path)   

     return abs_path

def main ():
     parser = argparse.ArgumentParser()
     parser.add_argument("--DebugPrint", type = int, default = 0, help = "Turn on debug printing")
     args = parser.parse_args()

     GACPD_hunks_info = get_GACPD_hunk_info()
     if not GACPD_hunks_info:
          print(f'Error: Could not retrieve the hunk info from the project folder')
          sys.exit()
          
     main_context_save_directory = os.path.join(Config.output_folder, f'{Config.GACPD_project_folder_name}_{Config.HUNK_CONTEXT_OUTPUT_FOLDER_NAME}')
     main_context_save_directory = get_safe_abs_path(main_context_save_directory)

     if args.DebugPrint:
          print('\n**********************************************\n')
     for pr in GACPD_hunks_info:
          if args.DebugPrint:
               print(f'Processing PR {pr["PR number"]} with {pr["PR classification"]} classification')
          pr_folder_name = f'{pr["PR number"]}_{pr["PR classification"]}'
          pr_folder_address = os.path.join(main_context_save_directory,pr_folder_name)
          if not os.path.isdir(pr_folder_address):
               os.makedirs(pr_folder_address)
          
          for classification in pr['classifications']:
               if args.DebugPrint:
                    print(f'\tProcessing files with {classification["classification type"]} classification')
               classification_folder_name = f"{classification['classification type']}_Files"
               classification_folder_address = os.path.join(pr_folder_address, classification_folder_name)
               if not os.path.isdir(classification_folder_address):
                    os.makedirs(classification_folder_address)

               for file in classification['files']:
                    if args.DebugPrint:
                         print(f'\t\tProcessing file {file["file name"]}')

                    file_folder_name = file['file name']
                    file_folder_address = os.path.join(classification_folder_address, file_folder_name)
                    if not os.path.isdir(file_folder_address):
                         os.makedirs(file_folder_address)

                    # Sometimes GACPD returns no hunk info for a file (not an error).
                    # In these cases we want to skip making the directories.
                    if len(file['file hunk info']) == 0:
                         continue
                    if os.path.isfile(file['source file address']):
                         source_code = Path(file['source file address']).read_text()
                    if os.path.isfile(file['target file address']):
                         target_code = Path(file['target file address']).read_text()

                    for hunk_pair_index, hunk_pair in enumerate(file['file hunk info']):
                         hunk_pair_folder_name = f'hunk_pair_{hunk_pair_index + 1}'
                         hunk_pair_folder_address = os.path.join(file_folder_address, hunk_pair_folder_name)
                         if not os.path.isdir(hunk_pair_folder_address):
                              os.makedirs(hunk_pair_folder_address)
                         
                         source_hunk_folder_name = f's_{hunk_pair["source hunk"]["hunk file name"]}'
                         source_hunk_folder_name = source_hunk_folder_name.split('.',1)[0]
                         source_hunk_folder_name = source_hunk_folder_name.replace('\\', '_').strip()
                         source_hunk_folder_address = os.path.join(hunk_pair_folder_address, source_hunk_folder_name)
                         if not os.path.isdir(source_hunk_folder_address):
                              os.makedirs(source_hunk_folder_address)

                         target_hunk_folder_name = f't_{hunk_pair["target hunk"]["hunk file name"]}'
                         target_hunk_folder_name = target_hunk_folder_name.split('.',1)[0]
                         target_hunk_folder_name = target_hunk_folder_name.replace('\\', '_').strip()                  
                         target_hunk_folder_address = os.path.join(hunk_pair_folder_address, target_hunk_folder_name)
                         if not os.path.isdir(target_hunk_folder_address):
                              os.makedirs(target_hunk_folder_address)

                         if os.path.isfile(file['source file address']):
                              # Retrieving the source hunk context
                              context_AST, context_source_code = extract_hunk_context_from_file(source_code, 
                                                                                               hunk_pair["source hunk"]["hunk line start"],
                                                                                               hunk_pair["source hunk"]["hunk line end"])
                              source_context_AST_address = os.path.join(source_hunk_folder_address,
                                                                           f'AST_{source_hunk_folder_name}.json')
                              
                              with open(source_context_AST_address, "w", encoding="utf-8") as outfile:
                                   json.dump(context_AST, outfile, indent= 2)
                              
                              source_context_SC_address = os.path.join(source_hunk_folder_address,
                                                                           f'SC_{source_hunk_folder_name}.json')
                              
                              with open(source_context_SC_address, "w", encoding = "utf-8") as outfile:
                                   json.dump(context_source_code, outfile, indent = 4)
                              
                         if os.path.isfile(file['target file address']):
                              # Retrieving the target hunk context
                              context_AST, context_source_code = extract_hunk_context_from_file(target_code, 
                                                                                               hunk_pair["target hunk"]["hunk line start"],
                                                                                               hunk_pair["target hunk"]["hunk line end"])
                              target_context_AST_address =  os.path.join(target_hunk_folder_address,
                                                                           f'AST_{target_hunk_folder_name}.json')
                              with open(target_context_AST_address, "w", encoding="utf-8") as outfile:
                                   json.dump(context_AST, outfile, indent= 2)
                              
                              target_context_SC_address =  os.path.join(target_hunk_folder_address,
                                                                           f'SC_{target_hunk_folder_name}.json')
                              with open(target_context_SC_address, "w", encoding = "utf-8") as outfile:
                                   json.dump(context_source_code, outfile, indent = 4)
          if args.DebugPrint:
               print('\n**********************************************\n')
                    
if __name__ == "__main__":
    main()