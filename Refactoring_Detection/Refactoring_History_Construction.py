import os
import sys
import json

def create_refactoring_graph_for_source_file(source_file_name, RM_result_json, output_json):
    RM_results = load_RM_result(RM_result_json)
    file_name = source_file_name
    commit_results = []
    for commit in RM_results['commits']:
        if not commit['refactorings']:
            # There are no refactorings in this commit, go to the next one
            continue
        commit_refactorings_results = []
        for refactoring in commit['refactorings']:
            if refactoring['type'] == 'Rename File':
                print('found a case of rename file, not handling it though')
            else:
                relevant_left_side_locations = []
                relevant_indices = []
                for left_side_location_index, left_side_location in enumerate(refactoring['leftSideLocations']):
                    if left_side_location['filePath'] == file_name:
                        relevant_left_side_locations.append(left_side_location)
                        relevant_indices.append(left_side_location_index)

                relevant_right_side_locations = [refactoring['rightSideLocations'][i] for i in relevant_indices]
                
                # print('*********NEW LOCATION********')
                # print(f'indices: {relevant_indices}\n')
                # print(f'left sides:{relevant_left_side_locations}\n')
                # print(f'right sides:{relevant_right_side_locations}\n')
                # print('*****************************')
                refactoring_side_pairs = []
                print('*********************')
                for relevenat_index in relevant_indices:
                    
                    side_pair_info = {
                        "Left Side" : relevant_left_side_locations[relevenat_index],
                        "Right Side" : relevant_right_side_locations[relevenat_index]
                    }
                    print(f'file name: {relevant_left_side_locations[relevenat_index]["filePath"]}, index = {relevenat_index}')

                    refactoring_side_pairs.append(side_pair_info)

                refactoring_results = {
                    "Type" : refactoring['type'],
                    "Description" : refactoring['description'],
                    "Markup" : refactoring['markup'],
                    "Side Pairs": refactoring_side_pairs
                }
                commit_refactorings_results.append(refactoring_results)
        commit_result = {
            "repository": commit["repository"],
            "sha1": commit["sha1"],
            "url": commit["url"],
            "Refactorings" : commit_refactorings_results
        }
        commit_results.append(commit_result)
        
    with open(output_json, 'w', encoding = 'utf-8') as json_output_file:
        json.dump(commit_results,json_output_file, indent = 4)
                




#TODO:
def create_refactoring_graph_for_hunk(hunk, source_file_name, RM_result_json):
    RM_results = load_RM_result(RM_result_json)
    file_name = source_file_name
    for commit in RM_results['commits']:
        if not commit['refactorings']:
            # There are no refactorings in this commit, go to the next one
            continue
        for refactoring in commit['refactorings']:

            for left_side_location in refactoring['leftSideLocations']:
                if left_side_location['filePath'] == source_file_name:
                    pass





def load_RM_result(RM_result_json):
    if not os.path.isfile(RM_result_json):
        print(f'Error: provided json result file does not exist: {RM_result_json}')
        sys.exit()
    with open(RM_result_json, 'r', encoding = 'utf-8') as result_file:
        result = json.load(result_file)
        return result
