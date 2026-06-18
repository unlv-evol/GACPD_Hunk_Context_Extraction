import json
import os
import sys
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
import Config


def natural_sort_key(s):
    return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', s['hunk file name'])]


def get_GACPD_hunk_info():
    '''
    Will return source and target hunk positions (starting and ending lines),
    and also the name of the hunk the info belongs to.
    '''
    
    GACPD_project_address = get_GACPD_project_folder_address()

    general_info = []
    for PR_folder in os.listdir(GACPD_project_address):
        # Skipping hidden files that might exist due to various reasons (like OS interference)
        if PR_folder.startswith('.'):
            continue
        # Skipping undesired PR classifications
        if not PR_folder.endswith("MO") and not PR_folder.endswith("ED"):
            continue
        if PR_folder.endswith("MO") and not Config.should_take_in_MO_PRs:
            continue
        if PR_folder.endswith("ED") and not Config.should_take_in_ED_PRs:
            continue

        PR_info = {
            "PR number": PR_folder.split('_')[0],
            "PR classification": PR_folder.split('_')[1],
            "classifications": []
        }

        PR_folder_address = os.path.join(GACPD_project_address, PR_folder)
        

        for classification_folder in os.listdir(PR_folder_address):
            if classification_folder.startswith('.'):
                continue
            # Skipping undesired file classifications.
            if not classification_folder.endswith('ED') and not classification_folder.endswith('MO'):
                continue
            if classification_folder.endswith("MO") and not Config.should_take_in_MO_files:
                continue
            if classification_folder.endswith("ED") and not Config.should_take_in_ED_files:
                continue

            
            classification_info = {
                "classification type" : classification_folder,
                "files" : []
            }
            classification_folder_address = os.path.join(PR_folder_address, classification_folder)


            for file_folder in os.listdir(classification_folder_address):
                if file_folder.startswith('.'):
                    continue
                
                                    
                source_folder_address = os.path.join(classification_folder_address, file_folder, Config.SOURCE_FOLDER_NAME)
                
                patch_file_name = [f for f in os.listdir(source_folder_address) if f.endswith(Config.PATCH_FILE_SUFFIX)][0]
                patch_file_address = os.path.join(source_folder_address, patch_file_name)

                report_file_name = 'reports/jscpd-report.json'
                report_file_address = os.path.join(classification_folder_address,file_folder, report_file_name)

                result_file_address = os.path.join(classification_folder_address, file_folder, Config.RESULT_FILE_NAME)

                # Retrieving the full address of the source and target files to be saved for the hunks.
                # These addresses will be slightly different (more complete) from the ones generated in the GACPD_Result_Processing.py
                hunk_associated_source_file_incomplete = ''
                hunk_associated_target_file_incomplete = ''
                with open(result_file_address, "r", encoding= "utf-8") as opened_result_file:
                    for line in opened_result_file:
                        line = line.strip()
                        # Extracts the name of the source repository. This will be used to reconstruct
                        # the address of the source repository absolutely.
                        if line.startswith('Mainline'):
                            source_repo_name = line.split(':',1)[1].strip()
                        # The source file regardless of whether it was renamed or not
                        if line.startswith('File:'):
                            hunk_associated_source_file_incomplete = line.split(':', 1)[1].strip()
                        # For when the target repository has not been renamed
                        if line.startswith('Is called in Divergent Path is'): 
                            hunk_associated_target_file_extra = line.split(':', 1)[1]
                            hunk_associated_target_file_incomplete = '/'.join(hunk_associated_target_file_extra.split('/')[1:])
                        # For when the target repository has been renamed
                        if line.startswith('Renamed Divergent Path is'): 
                            hunk_associated_target_file_extra = line.split(':', 1)[1]
                            hunk_associated_target_file_incomplete = '/'.join(hunk_associated_target_file_extra.split('/')[1:])

                    hunk_associated_source_file = os.path.join(Config.GACPD_results_folder, 'Repos_clones', Config.GACPD_project_folder_name,
                                                                source_repo_name, hunk_associated_source_file_incomplete)
                    hunk_associated_target_file = os.path.join(Config.GACPD_results_folder, hunk_associated_target_file_incomplete)
                    hunk_associated_source_file = hunk_associated_source_file.replace('\\', '/')
                    hunk_associated_target_file = hunk_associated_target_file.replace('\\', '/')
                    file_info={
                        "file name" : file_folder,
                        "source file address": hunk_associated_source_file,
                        "target file address": hunk_associated_target_file,
                        "file hunk info": []
                    } 

                # The patch file contains the "origin point" of the source hunk. The report file 
                # contains the "start line offset" and "end line offset" of the source file, and the 
                # start line and end line of the target file.
                with open(patch_file_address, "r", encoding = "utf-8") as opened_patch_file:
                    source_hunk_line_origin_points = []
                    hunk_count = 0
                    for line in opened_patch_file:
                        
                        if line.startswith('@@'):
                            hunk_count += 1
                            line_sections = line.split('@')
                            source_hunk_line_origin_points.append(abs(int(line_sections[2].split(',')[0])))
                    with open(report_file_address) as report_file:
                        
                        report_file_data = json.load(report_file)
                        report_file_hunk_info = report_file_data["duplicates"]
                        file_hunks_line_info = {
                            "source hunk info": [],
                            "target hunk info": []
                        }

                        file_hunks_line_info = []
                        for individual_hunk_info in report_file_hunk_info:
                            hunk_number = individual_hunk_info["firstFile"]["name"].split('_')[1]

                            source_hunk_start_line_offset_number = individual_hunk_info["firstFile"]["start"]
                            source_hunk_end_line_offset_number = individual_hunk_info["firstFile"]["end"]

                            source_hunk_info = {
                                "hunk file name": individual_hunk_info["firstFile"]["name"],
                                "hunk line start": source_hunk_line_origin_points[int(hunk_number) - 1] + source_hunk_start_line_offset_number,
                                "hunk line end": source_hunk_line_origin_points[int(hunk_number) - 1] + source_hunk_end_line_offset_number
                            }
                            target_hunk_start_line_number = individual_hunk_info["secondFile"]["start"]
                            target_hunk_end_line_number = individual_hunk_info["secondFile"]["end"]
                            target_hunk_info = {
                                "hunk file name":individual_hunk_info["secondFile"]["name"],
                                "hunk line start": target_hunk_start_line_number,
                                "hunk line end": target_hunk_end_line_number
                            }
                            pair_hunk_line_info = {
                                "source hunk": source_hunk_info,
                                "target hunk": target_hunk_info
                            }
                            file_hunks_line_info.append(pair_hunk_line_info)
                        
                        file_info["file hunk info"] = file_hunks_line_info

                classification_info["files"].append(file_info)
            PR_info["classifications"].append(classification_info)
        general_info.append(PR_info)         
                

    return general_info

def save_results_to_json(results):
    output_file_name = f'{ Config.GACPD_project_folder_name}_{Config.HUNK_INFO_OUTPUT_FILE_SUFFIX_NAME}'
    output_file_address = os.path.join(Config.output_folder, output_file_name)

    if not os.path.exists(Config.output_folder):
        os.makedirs(Config.output_folder)

    with open(output_file_address, "w", encoding="utf-8") as outfile:
        json.dump(results, outfile, indent= 2)
        print(f'Done, patch data saved to "{output_file_address}"')


def get_GACPD_project_folder_address():
    GACPD_repos_results_folder = os.path.join(Config.GACPD_results_folder, Config.REPOS_RESULTS_FOLDER_NAME)
    GACPD_project_address = os.path.join(GACPD_repos_results_folder, Config.GACPD_project_folder_name)
    if not os.path.exists(GACPD_project_address):
        print(f'ERROR: The provided project folder does not exist.  "{GACPD_project_address}"')    
        sys.exit()
    return GACPD_project_address

def main():
    results = get_GACPD_hunk_info()
    save_results_to_json(results)

if __name__ == "__main__":
    main()
