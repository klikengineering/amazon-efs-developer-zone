######################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

import os
from os import walk
import base64
import math
# File manager operation events:
# list: {"operation": "list", "path": "$dir"}
# upload: {"operation": "upload", "path": "$dir", "form_data": "$form_data"}


def modify(event):
    return None


def delete(event):
    print(event)
    path = event['path']
    name = event['name']

    file = f'{path}/{name}'

    try:
        os.remove(file)
    except OSError:
        return {"message": "couldn't delete the file", "statusCode": 500}
    else:
        return {"message": "file deletion successful", "statusCode": 200}


def make_dir(event):
    print(event)
    path = event['path']
    name = event['name']

    new_dir = f'{path}/{name}'

    try:
        os.mkdir(new_dir)
    except OSError:
        return {"message": "couldn't create the directory", "statusCode": 500}
    else:
        return {"message": "directory creation successful", "statusCode": 200}


def upload(event):
    print(event)
    "{'operation': 'upload', 'path': '/mnt/efs', 'chunk_data': {'dzuuid': '10f726ea-ae1d-4363-9a97-4bf6772cd4df', 'dzchunkindex': '0', 'dzchunksize': '1000000', 'dztotalchunkcount': '1', 'dzchunkbyteoffset': '0', 'filename': 'Log at 2020-08-11 12-17-21 PM.txt', 'content': '(Emitted value instead of an instance of Error)'}}"
    path = event['path']
    filename = event['chunk_data']['filename']
    file_content_decoded = base64.b64decode(event['chunk_data']['content'])
    current_chunk = int(event['chunk_data']['dzchunkindex'])
    save_path = os.path.join(path, filename)

    if os.path.exists(save_path) and current_chunk == 0:
        return {"message": "File already exists", "statusCode": 400}

    try:
        with open(save_path, 'ab') as f:
            f.seek(int(event['chunk_data']['dzchunkbyteoffset']))
            f.write(file_content_decoded)
    except OSError as error:
        print('Could not write to file: {error}'.format(error=error))
        return {"message": "couldn't write the file to disk", "statusCode": 500}

    total_chunks = int(event['chunk_data']['dztotalchunkcount'])

    if current_chunk + 1 == total_chunks:
        if int(os.path.getsize(save_path)) != int(event['chunk_data']['dztotalfilesize']):
            print("File {filename} was completed, but there is a size mismatch. Was {size} but expected {total}".format(filename=filename, size=os.path.getsize(save_path), total=event['chunk_data']['dztotalfilesize']))
            return {"message": "Size mismatch", "statusCode": 500}
        else:
            print("file {filename} has been uploaded successfully".format(filename=filename))
            return {"message": "File uploaded successfuly", "statusCode": 200}
    else:
        print("Chunk {current_chunk} of {total_chunks} for file {filename} complete".format(current_chunk=current_chunk + 1 , total_chunks=total_chunks, filename=filename))
        return {"message": "Chunk upload successful", "statusCode": 200}


def download(event):
    # first call {"path": "./", "filename": "test.txt"}
    # successive calls
    # {"path": "./", "filename": "test_video.mp4", "chunk_data": {'dzchunkindex': chunk['dzchunkindex'],
    # 'dzchunkbyteoffset': chunk['dzchunkbyteoffset']}}
    path = event['path']
    filename = event['filename']
    file_path = os.path.join(path, filename)
    chunk_size = 2000000  # bytes
    file_size = os.path.getsize(file_path)
    chunks = math.ceil(file_size / chunk_size)

    if "chunk_data" in event:
        start_index = event['chunk_data']['dzchunkbyteoffset']
        current_chunk = event['chunk_data']['dzchunkindex']
        try:
            with open(file_path, 'rb') as f:
                f.seek(start_index)
                file_content = f.read(chunk_size)
                encoded_chunk_content = str(base64.b64encode(file_content), 'utf-8')
                chunk_offset = start_index + chunk_size
                chunk_number = current_chunk + 1

                return {"dzchunkindex": chunk_number, "dztotalchunkcount": chunks, "dzchunkbyteoffset": chunk_offset,
                        "chunk_data": encoded_chunk_content, "dztotalfilesize": file_size}
        except OSError as error:
            print('Could not read file: {error}'.format(error=error))
            return {"message": "couldn't read the file from disk", "statusCode": 500}

    else:
        start_index = 0
        try:
            with open(file_path, 'rb') as f:
                f.seek(start_index)
                file_content = f.read(chunk_size)
                encoded_chunk_content = str(base64.b64encode(file_content), 'utf-8')
                chunk_number = 0
                chunk_offset = chunk_size

                return {"dzchunkindex": chunk_number, "dztotalchunkcount": chunks, "dzchunkbyteoffset": chunk_offset,
                        "chunk_data": encoded_chunk_content, "dztotalfilesize": file_size}

        except OSError as error:
            print('Could not read file: {error}'.format(error=error))
            return {"message": "couldn't read the file from disk", "statusCode": 500}


def list(event):
    # get path to list
    try:
        path = event['path']
    except KeyError:
        raise Exception('Missing required parameter in event: "path"')

    try:
        # TODO: Mucchhhh better thinking around listing directories
        dir_items = []
        file_items = []
        for (dirpath, dirnames, filenames) in walk(path):
            dir_items.extend(dirnames)
            file_items.extend(filenames)
            break
    # TODO: narrower exception scope and proper debug output
    except Exception as error:
        print(error)
        raise Exception(error)
    else:
        return {"path": path, "directiories": dir_items, "files": file_items, "statusCode": 200}


def lambda_handler(event, context):
    # get operation type
    try:
        operation_type = event['operation']
    except KeyError:
        raise Exception('Missing required parameter in event: "operation"')
    else:
        if operation_type == 'upload':
            return upload(event)
        if operation_type == 'list':
            return list(event)
        if operation_type == 'delete':
            return delete(event)
        elif operation_type == 'download':
            return download(event)
        elif operation_type == 'make_dir':
            return make_dir(event)
        elif operation_type == 'modify':
            modify(event)
