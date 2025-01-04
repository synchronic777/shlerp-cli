###############################################################
# This file features the main functions that are used by the 
# rule detection system to scan the project and find out the
# language/framework context that is used in a particular project

from tools.state import state
from tools.piputils import print_term
import tools.utils as utils
from os.path import exists
import glob

def frameworks_processing(rules, proj_fld):
    """Process the project folder to detect frameworks based on the provided rules.
    :param rules: object list containing framework rules
    :param proj_fld: text, the folder we want to process
    :return: a list of matched framework rules
    """
    _fw_leads = []
    for _rule in rules['frameworks']:
        if state('debug'): print_term('scan:fram', 'D', f'Processing rule: {_rule["name"]}')
        total = 0

        # Check for files defined in the rule
        for file in _rule['detect']['files']:
            names = file['names']
            pattern = file.get('pattern', None)
            for name in names:
                if exists(f'{proj_fld}/{name}'):
                    if pattern:
                        with open(f'{proj_fld}/{name}', 'r') as file_content:
                            if pattern in file_content.read():
                                total += 1
                                if state('debug'): print_term('scan:fram', 'D', f'Matched pattern in file: {name}, updated total: {total}')
                    else:
                        total += 1
                        if state('debug'): print_term('scan:fram', 'D', f'Matched file: {name}, updated total: {total}')

        # Check for folders defined in the rule
        for folder in _rule['detect']['folders']:
            name = folder['name']
            if exists(f'{proj_fld}/{name}/'):
                if not folder['files']:
                    total += 1
                    if state('debug'): print_term('scan:fram', 'D', f'Matched folder: {name}, updated total: {total}')
                else:
                    match = True
                    for file in folder['files']:
                        if not exists(f'{proj_fld}/{folder["name"]}/{file}'):
                            match = False
                    if match:
                        total += 1
                        if state('debug'): print_term('scan:fram', 'D', f'Matched all files in folder: {name}, updated total: {total}')

        _rule["total"] = total
        if state('debug'): print_term('scan:fram', 'D', f'Total score for rule {_rule["name"]}: {total}')

        rule_threshold = 0
        def get_dyn_threshold(type):
            rule_threshold = 0
            excl_obj = _rule['actions']['exclude']
            exclusions = excl_obj[type]
            dep_folders = excl_obj.get('dep_folders', []) or []
            name_key = 'name' if type == 'folders' else 'names'
            
            for criteria in _rule['detect'][type]:
                criteria_names = criteria[name_key] if type == 'files' else [criteria['name']]
                add = True
                for file_name in criteria_names:
                    if type == 'folders' and file_name in dep_folders:
                        add = False
                    if file_name in exclusions:
                        add = False
                if add:
                    rule_threshold += 1
            return rule_threshold

        rule_threshold += get_dyn_threshold('files')
        rule_threshold += get_dyn_threshold('folders')
        
        if state('debug'): print_term('scan:fram', 'D', f'Score threshold for {_rule["name"]}: {rule_threshold}')

        # Add the rule to the leads array if all of its criteria matched
        if _rule['total'] >= rule_threshold:
            _fw_leads.append(_rule)
            if state('debug'): print_term('scan:fram', 'D', f'Rule {_rule["name"]} added to leads')

    return utils.elect(_fw_leads)


def vanilla_processing(_rules, proj_fld, uid):
    """This function is scanning the project folder to backup and compares its content with the rules
    defined in the vanilla section of the rules file.
    :return: A list containing the "vanilla" rule that matches the most with the project, can return
    several ones if there are multiple rules having the same score ("weight")
    """
    print_term('scan', 'I', 'Running deep scan...', uid)
    if state('debug'): print_term('scan:vani', 'D', f'Starting vanilla processing for project folder: {proj_fld}')
    leads = deep_scan(proj_fld, _rules['vanilla'])
    for l in leads:
        if state('debug'): print_term('scan:vani', 'D', f'Lead found: {l["name"]} with total: {l["total"]}')
    # If the weight of the rule that has the heaviest score is lighter than the threshold,
    # We empty the leads list
    _elected_rule = utils.elect(leads)
    if not _elected_rule:
        leads = list([])
    else:
        leads = list([_elected_rule[0]])
    return leads


def deep_scan(proj_fld, rules):
    """Crawl the project to find files matching the extensions we provide to this function
    :param proj_fld: text, the folder we want to process
    :param rules: object list containing languages names, extensions to crawl and weights
    :return: an updated list with some more weight (hopefully)
    """
    for rule in rules:
        exclusions = rule['actions']['exclude']
        excl_flds = exclusions['folders']
        excl_files = exclusions['files']
        dep_folders = exclusions.get('dep_folders', []) or []

        def excluded(file_path):
            for excl_fld in excl_flds:
                if excl_fld in file_path:
                    return True
            for excl_file in excl_files:
                if excl_file in file_path:
                    return True
            for dep_folder in dep_folders:
                if dep_folder in file_path:
                    return True

        if 'total' not in rule.keys():
            rule['total'] = 0
        for ext_elem in rule['detect']['extensions']:
            for ext in ext_elem['names']:
                if state('debug'): print_term('iglob', 'D', f'Processing extension: {ext} for rule: {rule["name"]}')
                for file_path in glob.iglob(f'{proj_fld}/**/*{ext}', recursive=True):
                    if not excluded(file_path):
                        rule['total'] += ext_elem['weight']
                        if state('debug'): print_term('iglob', 'D', f'Matched: {file_path} for rule: {rule["name"]}, updated total: {rule["total"]}')
                    else:
                        if state('debug'): print_term('iglob', 'D', f'Excluded: {file_path} for rule: {rule["name"]}')
        if state('debug'): print_term('iglob', 'D', f'Total for rule {rule["name"]}: {rule["total"]}')
    return rules


def prune_tried_rules(_rules, _tmp_file, history_type):
    """This function is responsible for removing the rules that have already
    been tried from the list of rules that are left to be tested.
    :return: A list of rules that have not been tried yet
    """
    _remaining_rules = _rules[history_type].copy()
    for _rule_name in _tmp_file[history_type]:
        for _rule in _rules[history_type]:
            if _rule['name'] == _rule_name:
                _remaining_rules.remove(_rule)
    return _remaining_rules
