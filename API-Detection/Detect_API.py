import sys
import subprocess
import os
from enum import Enum

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
import Config

class line_category(Enum):
    IRRELEVANT = 0
    SUB_PROJECT_EXP= 1
    SUB_PROJECT = 2
    DEPENDENCY= 3

temp_address = "C:/Users/pahla/Documents/Personals/Parham/Work/MOVis 0.15/MOVis_Release/Results/Repos_files/onePr_10/linkedin/kafka/"
gradle_script_address = "C:/Users/pahla/Documents/Personals/Parham/Work/Code/Ouput Extraction/API-Detection/global_deps.init.gradle"
output_file_location = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'temporary_output_folder\\extracted_dependencies.txt')

def determine_line_category(line, line_number):
    if line_number < 5:
        return line_category.IRRELEVANT
    if line.startswith('No dependencies'):
        return line_category.IRRELEVANT
    if line.startswith('A web-based, searchable dependency'):
        return line_category.IRRELEVANT
    if line.startswith('('):
        return line_category.IRRELEVANT
    if line == '\n':
        return line_category.IRRELEVANT

    if line.startswith('|'):
        return line_category.DEPENDENCY
    if line.startswith('\\'):
        return line_category.DEPENDENCY
    if line.startswith('+'):
        return line_category.DEPENDENCY
    if line.startswith(' '):
        return line_category.DEPENDENCY
    
    if '-' in line:
        return line_category.SUB_PROJECT_EXP
    return line_category.SUB_PROJECT

def retrieve_API_versions_from_build():
    """
    Gets all the API versions that exist in the build file.

    Parameters
    ----------

    Returns
    -------
    API_versions: A list containing API names and their associated versions.
    """
    # print(f'hey bro, output file is : {output_file_location}')
    # result=  subprocess.run(
    #     [r".\gradlew", "ProjectDependencyAnalysis", "-I", gradle_script_address, f"-PoutputFile={output_file_location}"],
    #     cwd=temp_address, capture_output=True, text=True, shell = True)
    
    sub_project_list = []
    with open(output_file_location, 'r', encoding = 'utf-8') as result_file:
        for line_number, line in enumerate(result_file):
            line_categorization = determine_line_category(line, line_number)
            match line_categorization:
                case line_category.IRRELEVANT:
                    continue
                case line_category.DEPENDENCY:
                    continue
                case line_category.SUB_PROJECT_EXP:
                    sub_project_name = line.split('-')[0].strip()
                case line_category.SUB_PROJECT:
                    sub_project_name = line.strip()
                case _:
                    print(f'unknown case, line number: {line_number}, line:{line}')
                    continue
            sub_project_list.append(sub_project_name)
        
        print(f'sub_project_list:\n{sub_project_list}')

            

    #print(f'here is the results: {result}')

    #return API_versions

def get_file_imports():
    pass
    #with open(temp_address, 'r', encoding = 'utf-8'):
        
        

def get_file_API(source_code: bytes):
    """
    Gets all the API (external libraries) that are present in the file with their versions.

    Parameters
    ----------
    source_code:    The source code of the file that contains the library imports.

    Returns
    -------
    file_API:       A list of dicts containing the API call and its associated version (found in the build file)
    """
    file_API = ""
    return file_API


def main ():
    pass
    retrieve_API_versions_from_build()


if __name__ == "__main__":
    main()
