import json
import Config
import os
import sys

def get_GACPD_data_hierarchical(GACPD_project_address):

    results = []
    for PR_folder in os.listdir(GACPD_project_address):
        
        if not PR_folder.endswith("MO") and not PR_folder.endswith("ED"):
            continue
        if PR_folder.endswith("MO") and not Config.should_take_in_MO_PRs:
            continue
        if PR_folder.endswith("ED") and not Config.should_take_in_ED_PRs:
            continue


        PR_folder_address = os.path.join(GACPD_project_address, PR_folder)

        classification_data = []
        for classification_folder in os.listdir(PR_folder_address):
            # Saving Classification name here. It will be used
            # when saving the classification results
            if classification_folder.endswith('ED'):
                classification_name = 'ED'
            elif classification_folder.endswith('MO'):
                classification_name = 'MO'
            else: 
                continue

            GACPD_file_saved_data = []
            classification_folder_address = os.path.join(PR_folder_address, classification_folder)

            for file_folder in os.listdir(classification_folder_address):

                result_file_address = os.path.join(classification_folder_address, file_folder, Config.RESULT_FILE_NAME)

                # Getting the data stored in the result file
                result_extracted_data = {}
                line_similarity_scores = {}
                with open(result_file_address, "r", encoding="utf-8") as opened_result_file:
                    for line in opened_result_file:
                        line = line.strip()
                        # Skipping headers
                        if line.startswith("Similarity Check") or line.startswith("Classification"):
                            continue
                        
                        # Handling the similarity score case
                        if line.startswith("src"):
                            line_part_1, similarity_value = line.split(":", 1)
                            similarity_line, _ = line_part_1.split("-", 1)
                            line_similarity_scores[similarity_line.strip()] = similarity_value.strip()
                            continue
                        # Handling all the other cases
                        else:
                            key, value = line.split(":", 1)

                        result_extracted_data[key.strip()] = value.strip()
                    result_extracted_data["Similarity Scores"] = line_similarity_scores


                GACPD_file_extracted_data = {
                    "source_repository": result_extracted_data.get("Mainline is"),
                    "target_repository": result_extracted_data.get("Divergent Repo is"),
                    "source_file": result_extracted_data.get("File"),
                    "target_file": "",
                    "clone_similarity": result_extracted_data.get("Similarity Scores")
                }
                GACPD_file_extracted_data["target_file"] = GACPD_file_extracted_data["source_file"].replace(GACPD_file_extracted_data["source_repository"], GACPD_file_extracted_data["target_repository"])
                
                GACPD_file_saved_data.append(GACPD_file_extracted_data)

            classification_results = {
                classification_name: GACPD_file_saved_data
            }
            classification_data.append(classification_results)
        PR_results = {
            PR_folder: classification_data
        }
        results.append(PR_results)

    return results

def get_GACPD_data_flat(GACPD_project_address):

    results = []
    for PR_folder in os.listdir(GACPD_project_address):
        
        if not PR_folder.endswith("MO") and not PR_folder.endswith("ED"):
            continue
        if PR_folder.endswith("MO") and not Config.should_take_in_MO_PRs:
            continue
        if PR_folder.endswith("ED") and not Config.should_take_in_ED_PRs:
            continue

        PR_folder_address = os.path.join(GACPD_project_address, PR_folder)

        _, PR_classification = PR_folder.split('_', 1)
        for classification_folder in os.listdir(PR_folder_address):
            # No need to save classification name here, since we are not going for the hierarchical
            # json output. We do want to skip the rest of the loop if the classification folder does not 
            # end with 'ED' or 'MO'. 
             
            if not classification_folder.endswith('ED') and not classification_folder.endswith('MO'):
                continue

            classification_folder_address = os.path.join(PR_folder_address, classification_folder)

            for file_folder in os.listdir(classification_folder_address):

                result_file_address = os.path.join(classification_folder_address, file_folder, Config.RESULT_FILE_NAME)

                # Getting the data stored in the result file
                result_extracted_data = {}
                line_similarity_scores = {}
                with open(result_file_address, "r", encoding="utf-8") as opened_result_file:
                    for line in opened_result_file:
                        line = line.strip()
                        # Skipping headers
                        if line.startswith("Similarity Check") or line.startswith("Classification"):
                            continue
                        
                        # Handling the similarity score case
                        if line.startswith("src"):
                            line_part_1, similarity_value = line.split(":", 1)
                            similarity_line, _ = line_part_1.split("-", 1)
                            line_similarity_scores[similarity_line.strip()] = similarity_value.strip()
                            continue
                        # Handling all the other cases
                        else:
                            key, value = line.split(":", 1)

                        result_extracted_data[key.strip()] = value.strip()
                    result_extracted_data["Similarity Scores"] = line_similarity_scores


                GACPD_result_data = {
                    "source_repository": result_extracted_data.get("Mainline is"),
                    "target_repository": result_extracted_data.get("Divergent Repo is"),
                    "PR_number": result_extracted_data.get("In PR"),
                    "source_file": result_extracted_data.get("File"),
                    "target_file": "",
                    "file_classification" : classification_folder,
                    "PR_classification": PR_classification,
                    "clone_similarity": result_extracted_data.get("Similarity Scores")
                }
                source_repository_org, _ = GACPD_result_data["source_repository"].split('/',1)
                target_repository_org, _ = GACPD_result_data["target_repository"].split('/',1)
                GACPD_result_data["target_file"] = GACPD_result_data["source_file"].replace(source_repository_org,target_repository_org)
                results.append(GACPD_result_data)
    return results

def save_results_to_json(results):
    output_file_name = f'{ Config.GACPD_project_folder_name}_{Config.OUTPUT_FILE_SUFFIX_NAME}'
    output_file_address = os.path.join(Config.output_folder, output_file_name)

    if not os.path.exists(Config.output_folder):
        os.makedirs(Config.output_folder)

    if(Config.should_json_be_hierarchical) :
        indent_value = 1
    else:
        indent_value = 4
    
    with open(output_file_address, "w", encoding="utf-8") as outfile:
        json.dump(results, outfile, indent= indent_value)

def get_GACPD_project_folder_address():
    GACPD_project_address = os.path.join(Config.GACPD_repos_results_folder, Config.GACPD_project_folder_name)
    if not os.path.exists(GACPD_project_address):
        print(f'ERROR: The provided project folder does not exist.  "{GACPD_project_address}"')    
        sys.exit()
    return GACPD_project_address

def main():
    if not Config.should_take_in_ED_PRs and not Config.should_take_in_MO_PRs:
        print('Error: The Config file currently is specifying that neither MO nor ED PRs are to be processed. Please select at least one of them to be processed')
        sys.exit()
    
    GACPD_project_address = get_GACPD_project_folder_address()
    if(Config.should_json_be_hierarchical):
        results = get_GACPD_data_hierarchical(GACPD_project_address)
    else:
        results = get_GACPD_data_flat(GACPD_project_address)

    save_results_to_json(results)

if __name__ == "__main__":
    main()