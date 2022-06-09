"""
cacophony-processing - this is a server side component that runs alongside
the Cacophony Project API, performing post-upload processing tasks.
Copyright (C) 2018, The Cacophony Project

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import json
import os
import requests
import logging
from requests_toolbelt.multipart.encoder import MultipartEncoder
from urllib.parse import urljoin
import hashlib


class API:
    def __init__(self, api_url, user, password):
        # self.file_url = file_url
        self.base_url = api_url
        self.api_url = api_url + "/api/v1"
        self._token = self._get_jwt(user, password)
        self._auth_header = {"Authorization": self._token}

    def tag_recording(self, recording_id, what):
        tag = {}
        tag["what"] = what
        tag["confidence"] = 1.0
        data = {"tag": json.dumps(tag)}
        r = requests.post(
            self.api_url + f"/recordings/{recording_id}/tags",
            data=data,
            headers=self._auth_header,
        )
        r.raise_for_status()

    def _get_jwt(self, user, password):

        url = urljoin(self.base_url, "/authenticate_user")
        r = requests.post(url, {"userName": user, "password": password})
        if r.status_code == 200:
            return r.json().get("token")
        elif r.status_code == 422:
            raise ValueError("Could not log on as '{}'.".format(user))
        elif r.status_code == 401:
            raise ValueError("Could not log on as '{}'".format(user))
        else:
            r.raise_for_status()
