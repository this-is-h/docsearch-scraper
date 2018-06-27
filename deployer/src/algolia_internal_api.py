import requests
from os import environ
from base64 import b64encode


def get_endpoint(endpoint, params=''):
    base_endpoint = environ.get('BASE_INTERNAL_ENDPOINT')

    return base_endpoint + endpoint + params


def get_headers():
    token = environ.get('INTERNAL_API_AUTH')

    app_id = environ.get('APPLICATION_ID_PROD')
    admin_api_key = environ.get('API_KEY_PROD')
    auth_token = b64encode(app_id + ":" + admin_api_key).replace('=', '').replace("\n", '')

    return {
        'Authorization': 'Basic ' + token,
        'Algolia-Application-Authorization': 'Basic ' + auth_token
    }


def get_application_rights():
    app_id = environ.get('APPLICATION_ID_PROD')
    endpoint = get_endpoint('/applications/' + app_id)  # , '?fields=application_rights')

    r = requests.get(endpoint, headers=get_headers())

    data = r.json()

    return data['application_rights']


def get_right_for_email(email):
    rights = get_application_rights()

    for right in rights:
        if right['user']['email'] == email:
            return right

    print email + " has no rights on the app"
    return None


def get_indices_for_right(right):
    if right is not None:
        return right['indices']
    return []


def add_user_to_index(index_name, user_email):
    """Give a user access to the Analytics on the index

    Args:
        index_name: The name of the index
        user_email: The email address to add

    Returns:
        - True if the user was successfully added
        - None if the user was already given access to this index
        - {url} a string pointing to an invitation link if the user does not
          yet have an Algolia account
    """

    right = get_right_for_email(user_email)
    indices = get_indices_for_right(right)

    # User is already added to this index
    if index_name in indices:
        return None;

    indices.append(index_name)

    payload = {
        'application_right': {
            'application_id': 13240,  # website internal DocSearch app id
            'user_email': user_email,
            'indices': indices,
            'analytics': True
        }
    }
    headers = get_headers();

    # User has already access to some other indices
    if right:
        endpoint = get_endpoint('/application_rights/' + str(right['id']))
        requests.patch(endpoint, json=payload, headers=headers)
        return True
    # Adding user for the first time
    endpoint = get_endpoint('/application_rights/')

    response = requests.post(endpoint, json=payload, headers=headers)
    print response.request
    data = response.json()
    invitation_url = data['user']['invitation_url'] if hasattr(data, 'user') and hasattr(data['user'], 'invitation_url') else None

    # User does not have an Algolia account, they must follow this invitation url
    if invitation_url:
        return invitation_url

    # User has an Algolia account, they have been added to the index
    return True


def remove_user_from_index(config, email):
    right = get_right_for_email(email)
    indices = get_indices_for_right(right)

    if config in indices:
        indices.remove(config)

    if len(indices) > 0:
        requests.patch(get_endpoint('/application_rights/' + str(right['id'])), json={
            'application_right': {
                'application_id': 13240,  # website internal docsearch app id
                'user_email': email,
                'indices': indices,
                'analytics': True
            }
        }, headers=get_headers())
    else:
        requests.delete(get_endpoint('/application_rights/' + str(right['id'])), headers=get_headers())
