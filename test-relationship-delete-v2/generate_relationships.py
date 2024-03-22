import argparse
import json
import os
import logging
import requests
from csv import DictReader
import re
import sys

ERROR_LOG = "relationship_errors.log"
logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')
V1_API_URL = "https://api.dev.ror.org/v1/organizations/"
V2_API_URL = "https://api.dev.ror.org/v2/organizations/"
UPDATED_RECORDS_PATH = "updates/"
INVERSE_TYPES = ('parent', 'child', 'related')
REL_INVERSE = {'parent': 'child', 'child': 'parent', 'related': 'related',
                'successor': 'predecessor', 'predecessor': 'successor'}

def check_file(file):
    filepath = ''
    for root, dirs, files in os.walk(".", topdown=True):
        if file in files:
            filepath = (os.path.join(root, file))
    return filepath

def parse_record_id(id):
    parsed_id = None
    pattern = '^https:\/\/ror.org\/(0[a-z|0-9]{8})$'
    ror_id = re.search(pattern, id)
    if ror_id:
        parsed_id = ror_id.group(1)
    else:
        logging.error(f"ROR ID: {id} does not match format: {pattern}. Record will not be processed")
    return parsed_id

def get_record_status(record_id, version):
    status = ''
    filepath = check_file(record_id + ".json")
    if filepath:
        try:
            with open(filepath, 'r') as f:
                file_data = json.load(f)
                status = file_data['status']
        except Exception as e:
            logging.error(f"Error reading {filepath}: {e}")
    else:
        api_url = V2_API_URL if version == 2 else V1_API_URL
        download_url=api_url + record_id
        try:
            rsp = requests.get(download_url)
            rsp.raise_for_status()
            response = rsp.json()
            status = response['status']
        except requests.exceptions.RequestException as e:
            logging.error(f"Request for {download_url}: {e}")
    return status

def get_record(id, filename, version):
    api_url = V2_API_URL if version == 2 else V1_API_URL
    download_url=api_url + id
    try:
        rsp = requests.get(download_url)
        rsp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Request for {download_url}: {e}")

    try:
        response = rsp.json()
        with open(UPDATED_RECORDS_PATH + filename, "w", encoding='utf8') as f:
            json.dump(response, f,  ensure_ascii=False)
    except Exception as e:
        logging.error(f"Writing {filename}: {e}")

def has_inverse_rel_csv(current_rel, all_rels):
    print("Checking inverse relationship for " + current_rel['short_related_id'])
    has_inverse = False
    for r in all_rels:
        if r['short_record_id'] == current_rel['short_related_id'] and r['record_relationship'] == REL_INVERSE[current_rel['record_relationship']]:
            has_inverse = True
    print("Has inverse is " + str(has_inverse))
    return has_inverse

def download_records(relationships, version):
    print("DOWNLOADING PRODUCTION RECORDS")
    downloaded_records_count = 0
    if not os.path.exists(UPDATED_RECORDS_PATH):
        os.makedirs(UPDATED_RECORDS_PATH)
    # download all records that are labeled as in production
    for r in relationships:
        if r['record_relationship'].lower() == 'delete':
            record_filename = r['short_record_id'] + ".json"
            if not(check_file(record_filename)):
                    get_record(r['short_record_id'], record_filename, version)
                    downloaded_records_count += 1
            related_filename = r['short_related_id'] + ".json"
            if not(check_file(related_filename)):
                    get_record(r['short_related_id'], related_filename, version)
                    downloaded_records_count += 1
        else:
            if r['related_location'].lower() == "production" and (r['record_relationship'] in INVERSE_TYPES or has_inverse_rel_csv(r, relationships)):
                filename = r['short_related_id'] + ".json"
                if not(check_file(filename)):
                    get_record(r['short_related_id'], filename, version)
                    downloaded_records_count += 1
    print(str(downloaded_records_count) + " records downloaded")

def remove_missing_files(relationships, missing_files):
    updated_relationships = [r for r in relationships if not(r['short_record_id'] in missing_files or r['short_related_id'] in missing_files)]
    print (str(len(missing_files)) + " missing records removed")
    return updated_relationships

def check_missing_files(relationships):
    print ("CHECKING FOR MISSING RECORDS")
    missing_files = []
    for r in relationships:
        filename = r['short_record_id'] + ".json"
        if not check_file(filename):
            missing_files.append(r['short_record_id'])
            logging.error(f"Record: {r['record_id']} will not be processed because {filename} does not exist.")

    for i in range(len(relationships)):
        if relationships[i]['short_related_id'] in missing_files:
            logging.error(f"Record {relationships[i]['short_record_id']} will not contain a relationship for {relationships[i]['short_related_id']} because {relationships[i]['short_related_id']}.json does not exist")

    if len(missing_files) > 0:
        #remove dupes
        missing_files = list(dict.fromkeys(missing_files))
        relationships = remove_missing_files(relationships, missing_files)
    return relationships

def check_relationship(former_relationship, current_relationship_id, current_relationship_type, version):
    if not version >= 2:
        current_relationship_type = current_relationship_type.title()
    if current_relationship_type.lower() == 'delete':
        return [r for r in former_relationship if not r['id'] == current_relationship_id]
    else:
        return [r for r in former_relationship if ((not r['id'] == current_relationship_id) or (r['id'] == current_relationship_id and (not r['type'] == current_relationship_type)))]


def get_record_name(record, version):
    record_name = None
    if version == 2:
        ror_display  = [name for name in record['names'] if 'ror_display' in name['types']]
        record_name = ror_display[0]['value']
    if version == 1:
        record_name = record['name']
    return record_name


def get_related_name_api(related_id, version):
    name = None
    api_url = V2_API_URL if version == 2 else V1_API_URL
    download_url=api_url + related_id
    try:
        rsp = requests.get(download_url)
        rsp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Request for {download_url}: {e}")

    try:
        response = rsp.json()
        name = get_record_name(response, version)
    except Exception as e:
        logging.error(f"Getting name for {related_id}: {e}")
    return name

def get_related_name(related_id, version):
    filename = related_id + ".json"
    filepath = check_file(filename)
    name = None
    if filepath:
        try:
            with open(filepath, 'r') as f:
                file_data = json.load(f)
                name = get_record_name(file_data, version)
        except Exception as e:
            logging.error(f"Reading {filepath}: {e}")
    else:
        name = get_related_name_api(related_id, version)
    return name

def process_one_relationship(relationship, version):
    filename = relationship['short_record_id'] + ".json"
    filepath = check_file(filename)
    relationship_data = {
        "label": get_related_name(relationship['short_related_id'], version),
        "type": relationship['record_relationship'] if version==2 else relationship['record_relationship'].title(),
        "id": relationship['related_id']
    }
    try:
        with open(filepath, 'r+') as f:
            file_data = json.load(f)
            file_data['relationships'] = check_relationship(file_data['relationships'], relationship['related_id'], relationship['record_relationship'], version)
            f.seek(0)
            json.dump(file_data, f, ensure_ascii=False, indent=2)
            f.truncate()
    except Exception as e:
        logging.error(f"Writing {filepath}: {e}")

def delete_one_relationship(relationship, version):
    record_filename = relationship['short_record_id'] + ".json"
    record_filepath = check_file(record_filename)
    try:
        with open(record_filepath, 'r+') as f:
            file_data = json.load(f)
            file_data['relationships'] = check_relationship(file_data['relationships'], relationship['related_id'], relationship['record_relationship'], version)
            f.seek(0)
            json.dump(file_data, f, ensure_ascii=False, indent=2)
            f.truncate()
    except Exception as e:
        logging.error(f"Writing {record_filepath}: {e}")

    related_filename = relationship['short_related_id'] + ".json"
    related_filepath = check_file(related_filename)
    try:
        with open(related_filepath, 'r+') as f:
            file_data = json.load(f)
            file_data['relationships'] = check_relationship(file_data['relationships'], relationship['record_id'], relationship['record_relationship'], version)
            f.seek(0)
            json.dump(file_data, f, ensure_ascii=False, indent=2)
            f.truncate()
    except Exception as e:
        logging.error(f"Writing {related_filepath}: {e}")



def process_add_relationships(add_relationships, version):
    print("ADDING RELATIONSHIPS")
    added_relationships_count = 0
    for r in add_relationships:
        process_one_relationship(r, version)
        added_relationships_count += 1
    print(str(added_relationships_count) + " relationships added")


def process_delete_relationships(delete_relationships, version):
    print("DELETING RELATIONSHIPS")
    deleted_relationships_count = 0
    for r in delete_relationships:
        delete_one_relationship(r, version)
        deleted_relationships_count += 1
    print(str(deleted_relationships_count) + " relationships deleted")


def get_relationships_from_file(file, version):
    print("PROCESSING CSV")
    relationships = []
    rel_dict = {}
    row_count = 0
    relationship_count = 0
    try:
        with open(file, 'r') as rel:
            rel_file_rows = DictReader(rel)
            for row in rel_file_rows:

                row_count += 1
                check_record_id = parse_record_id(row['Record ID'])
                check_related_id = parse_record_id(row['Related ID'])
                # check that related ID is an active record
                check_related_id_status = get_record_status(check_related_id, version)
                if (check_record_id and check_related_id):
                    if check_related_id_status == 'active' or row['Relationship of Related ID to Record ID'].lower() == 'predecessor':
                        rel_dict['short_record_id'] = check_record_id
                        rel_dict['short_related_id'] = check_related_id
                        rel_dict['record_name'] = row['Name of org in Record ID']
                        rel_dict['record_id'] = row['Record ID']
                        rel_dict['related_id'] = row['Related ID']
                        rel_dict['related_name'] = row['Name of org in Related ID']
                        rel_dict['record_relationship'] = row['Relationship of Related ID to Record ID'].lower()
                        rel_dict['related_location'] = row['Current location of Related ID'].title()
                        relationships.append(rel_dict.copy())
                        relationship_count += 1
                    else:
                        logging.error(f"Related ID from CSV: {check_related_id} has a status other than active and a relationship type other than Predecessor. Relationship row {row_count} cannot be processed")
        print(str(row_count)+ " rows found")
        print(str(relationship_count)+ " valid relationships found")
    except IOError as e:
        logging.error(f"Reading file {file}: {e}")
    return relationships

def generate_relationships(file, version):
    if check_file(file):
        relationships = get_relationships_from_file(file, version)
        if relationships:
            download_records(relationships, version)
            relationships_missing_files_removed = check_missing_files(relationships)
            delete_rels = [r for r in relationships_missing_files_removed if r['record_relationship'].lower() == 'delete']
            add_rels = [r for r in relationships_missing_files_removed if r not in delete_rels]
            process_delete_relationships(delete_rels, version)
            process_add_relationships(add_rels, version)
        else:
            logging.error(f"No valid relationships found in {file}")
    else:
        logging.error(f"{file} must exist to process relationship records")

def main(file, version):
    generate_relationships(file, version)
    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        print("ERRORS RECORDED IN relationship_errors.log")
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script to generate relationships in new/udpated records")
    parser.add_argument('-v', '--schemaversion', choices=[1, 2], type=int, required=True, help='Schema version (1 or 2)')
    parser.add_argument('file')
    args = parser.parse_args()
    main(args.file, args.schemaversion)
