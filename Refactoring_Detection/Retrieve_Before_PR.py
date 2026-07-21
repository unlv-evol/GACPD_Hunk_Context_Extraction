import os
import sys
import json
import requests
from pathlib import Path
import subprocess
import difflib
from tree_sitter import Language, Parser, Query, QueryCursor
from difflib import SequenceMatcher
import tree_sitter_java as tsjava
import Making_AST.Extract_Hunk_AST_Util as Util
def get_user_github_token():
    script_dir = Path(__file__).parent
    properties_file_path = script_dir / 'github-oauth.properties'
    try:
        with open(properties_file_path, 'r') as properties_file:
            for line in properties_file:
                line = line.strip()
                if line:
                    if not line.startswith('#'):
                        key, value = line.split('=', 1)
                        if key.strip() == 'OAuthToken':
                            return value.strip()
                        
        print("Error: Could not find a token in the properties file. Please check your formatting.")
        return None
        
    except FileNotFoundError:
        print(f"Error: Could not find github oauth file at {properties_file_path}")
        return None
    
def get_PR_info(project_github_name, PR_number, token):
    pr_url = 'https://api.github.com/repos/' + project_github_name + '/pulls/' + PR_number

    header = {
        'Authorization': f'token {token}'
    }
    response = requests.get(pr_url, headers=header)
    json_response = json.loads(response.content)
    return json_response

def ensure_commit_exists(commit_sha, repo_path, pr_number):
    check_commit_command = [
        'git', 'cat-file', '-e', commit_sha
    ]
    commit_exists = subprocess.run(
        check_commit_command,
        cwd= repo_path,
        capture_output=True
    )
    if commit_exists.returncode == 0:
        return True

def get_divergence_commit(target_branch, PR_head_commit, local_git_path):
    command = [
        'git',
        'merge-base',
        f'origin/{target_branch}',
        PR_head_commit
    ]
    try:
        result = subprocess.run(
                command,
                cwd=local_git_path,         
                capture_output=True,   
                text=True,             
                check=True             
            )
        return result.stdout.strip()
    except subprocess.SubprocessError as error:
        print(f'Error while trying to retrieve divergence commit SHA from Git: {error.returncode}')
        print(f'Git error message:\n{error.stderr.strip()}')
        return None

def get_file_at_commit(local_git_path, file_relative_path: str, commit_sha):
    # Git expects UNIX addressing
    file_relative_path = file_relative_path.replace("\\", "/")
    command = ['git', 'show', f'{commit_sha}:{file_relative_path}']
    try:
        result = subprocess.run(
            command,
            cwd=local_git_path,         
            capture_output=True,   
            text=True,             
            check=True 
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f'Error while trying to retrieve file at commit {commit_sha}: {e.returncode}')
        print(f'Git error message:\n{e.stderr.strip()}')
        return None

def process_git_path(file_path):
    path = Path(file_path).resolve()
    if path.is_file():
        working_dir = path.parent
    else:
        working_dir = path
    
    try:
        git_command = ['git', 'rev-parse', '--show-toplevel']
        output = subprocess.check_output(
            git_command,
            cwd = working_dir,
            stderr=  subprocess.DEVNULL,
            text=True
        )
        local_git_path = Path(output.strip())
        file_relative_path = path.relative_to(local_git_path)

        return str(local_git_path), str(file_relative_path)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print('Error while trying to process the local git path.')
        print(f'Git error: {e.stderr}')
        return "",""


def get_file_before_PR(file_path, PR_info):
    local_git_path, file_relative_path = process_git_path(file_path)
    if local_git_path =="" or file_relative_path == "":
        return None
    token = get_user_github_token()
    if not token:
        print('Did not continue operation because could not retrieve token')
        return None
    if not PR_info:
        print('PR_info is empty, not returning any file')
        return None
    target_branch = PR_info['base']['ref']
    PR_head_commit = PR_info['head']['sha']

    if ensure_commit_exists(PR_head_commit, local_git_path, PR_info['number']):
        divergence_commit_sha = get_divergence_commit(target_branch, PR_head_commit, local_git_path)
    else:
        print(f'Error, head commit {PR_head_commit} does not exist at all (not even in the PR)')
        return None

    file_before_PR = get_file_at_commit(local_git_path, file_relative_path, divergence_commit_sha)
    if not file_before_PR:
        print('Error, could not retrieve file.')
        return None
    
    return file_before_PR

def get_diff(before_patch_file_content :str, after_patch_file_content: str):
    before_file_lines = before_patch_file_content.splitlines(keepends = True)
    after_file_lines = after_patch_file_content.splitlines(keepends= True)
    diff_result = difflib.unified_diff(
            before_file_lines,
            after_file_lines,
            fromfile= 'file_before_patch.java',
            tofile = 'file_after_patch.java'
        )
    return "".join(diff_result)

def get_function_before_PR(patch, after_patch_method_node, 
                           after_patch_source_code, before_patch_AST, before_patch_source_code):

    diff_lines = {
        'prepatch': [],
        'postpatch': []
    }
    for hunk in patch[0]:
        source_start = hunk.source_start
        source_end = hunk.source_start + hunk.source_length - 1
        target_start = hunk.target_start
        target_end = hunk.target_start + hunk.target_length - 1

        diff_lines['prepatch'].append((source_start, source_end))
        diff_lines['postpatch'].append((target_start, target_end))
    
    # The diff result will have its line indexing start from 1 insead of 0.
    method_after_patch_start_line = after_patch_method_node.start_point[0] + 1
    method_after_patch_end_line = after_patch_method_node.end_point[0] + 1

    possible_postpatch_hunks = []
    for i, patch_line in enumerate(diff_lines['postpatch']):
        if max(method_after_patch_start_line, patch_line[0]) <= min(method_after_patch_end_line, patch_line[1]):
            possible_hunk_detail = {
                'hunk_index': i,
                'hunk_start' : patch_line[0],
                'hunk_end' : patch_line[1]
            }
            possible_postpatch_hunks.append(possible_hunk_detail)

    possible_prepatch_hunks = []
    for possible_postpatch_hunk in possible_postpatch_hunks:
        prepatch_hunk_detail = diff_lines['prepatch'][possible_postpatch_hunk['hunk_index']]
        possible_prepatch_hunks.append(prepatch_hunk_detail)

    prepatch_methods = []
    query_string = """
        (method_declaration) @method
    """
    JAVA_LANGUAGE = Language(tsjava.language())
    query = Query(JAVA_LANGUAGE, query_string)
    query_cursor = QueryCursor(query)
    captures = query_cursor.captures(before_patch_AST.root_node)

    for possible_prepatch_hunk in possible_prepatch_hunks:
        prepatch_methods.extend(get_methods_in_hunk(captures, possible_prepatch_hunk[0], possible_prepatch_hunk[1]))

    prepatch_method_names, prepatch_method_rests = [],[]
    for i, prepatch_method in enumerate(prepatch_methods):
        prepatch_method_names.append('')
        prepatch_method_rests.append('')
        prepatch_method_names[i], prepatch_method_rests[i] = Util.get_method_signature_partitioned(prepatch_method,before_patch_source_code)
    
    postpatch_method_name, postpatch_method_rest = Util.get_method_signature_partitioned(after_patch_method_node, after_patch_source_code)
    
    selected_prepatch_method = None
    highest_fuzzy_score = -1.0
    for i, prepatch_method_name in enumerate(prepatch_method_names):
        prepatch_method_rest = prepatch_method_rests[i]
        fuzzy_score = calculate_weighted_comparison_score(postpatch_method_name, postpatch_method_rest, 
                                                          prepatch_method_name, prepatch_method_rest, 0.8)
        # print('***************')
        # print(f'for function:{prepatch_method_name} Calculated fuzzy score: {fuzzy_score}')
        # print('***************')
        if fuzzy_score > highest_fuzzy_score:
            highest_fuzzy_score = fuzzy_score
            selected_prepatch_method = prepatch_methods[i]

    return selected_prepatch_method

def calculate_weighted_comparison_score(postpatch_method_name, postpatch_method_rest, 
                                        prepatch_method_name, prepatch_method_rest, name_weight: float = 0.8):
    if name_weight < 0.0:
        name_weight = 0.0
    if name_weight > 1.0:
        name_weight = 1.0
    name_score = SequenceMatcher(None, postpatch_method_name, prepatch_method_name).ratio()
    param_score = SequenceMatcher(None, postpatch_method_rest, prepatch_method_rest).ratio()
    final_score = (name_score * name_weight) + (param_score * (1.0 - name_weight))
    return final_score


def get_methods_in_hunk(captures, hunk_start, hunk_end):
    methods_in_hunk = []
    
    for node in captures['method']:
        # TThe inputted hunk numbers should be tree-sitter numbers,
        # which have 0-based indexing, while the diff tool uses 1-based indexing.
        node_start = node.start_point[0] + 1
        node_end = node.end_point[0] + 1

        if max(node_start, hunk_start) <= min(node_end, hunk_end):
            methods_in_hunk.append(node)
    return methods_in_hunk