"""
File class
"""
from __future__ import annotations

import os.path

from dataclasses import dataclass
from datetime import datetime
from typing import Self

from . import session
from . import user as _user


@dataclass
class File:
    """
    Class representing both files and directories in kegsnet
    """
    name: str = None
    path: str = None

    size: int = None
    author: str = None
    license: str = None

    mime: str = None
    type: str = None

    url: str = None
    icon_url: str = None

    datemodified: datetime = None
    datecreated: datetime = None

    user: _user.User = None
    is_external: bool = False

    _session: session.Session = None

    def __repr__(self):
        return f"<{self.type.title()}: {os.path.join(self.path, self.name)}>"

    @property
    def contents(self) -> list[File] | bytes:
        """
        Retrieve contents of the file or directory
        :return: list of files for directories, or file content as bytes
        """
        if self.is_dir:
            # Get the folder contents
            return self._session.files_in_dir(self.path)
        else:
            return self._session.rq.get(self.url).content

    def delete(self):
        """
        Deletes the file from the session's file manager
        """
        self._session.rq.post("https://vle.kegs.org.uk/repository/draftfiles_ajax.php",
                              params={"action": "delete"},
                              data={
                                  "sesskey": self._session.sesskey,

                                  "clientid": self._session.file_client_id,
                                  "itemid": self._session.file_item_id,
                                  "filename": self.name,
                                  "filepath": self.path
                              })
        self._session.file_save_changes()

    @classmethod
    def from_json(cls, data: dict, _session: session.Session = None) -> Self:
        """Load a file from JSON data"""
        return cls(name=data.get("filename"),
                   path=data.get("filepath"),
                   size=data.get("size"),
                   author=data.get("author"),
                   license=data.get("license"),
                   mime=data.get("mimetype"),
                   type=data.get("type"),
                   url=data.get("url"),
                   icon_url=data.get("icon"),
                   datemodified=datetime.fromtimestamp(data.get("datemodified")),
                   datecreated=datetime.fromtimestamp(data.get("datecreated")),
                   user=_session.connected_user,
                   _session=_session)

    @classmethod
    def from_json2(cls, data: dict, _sess: session.Session) -> Self:
        """Load a file from JSON data in a slightly different format"""
        return cls(
            name=data.get("filename"),
            path=data.get("filepath"),
            size=data.get("filesize"),
            url=data.get("fileurl"),
            is_external=data.get("isexternalfile"),
            mime=data.get("mimetype"),
            type="file",
            datemodified=datetime.fromtimestamp(data.get("timemodified")),
            _session=_sess
        )

    @property
    def is_dir(self):
        """Check if the file is actually a directory"""
        return self.type == "folder"
