"""
File class
"""

from __future__ import annotations

import os.path

from dataclasses import dataclass
from datetime import datetime
from typing_extensions import Self, Optional

from . import session
from . import user as _user


@dataclass
class File:
    """
    Class representing both files and directories in kegsnet
    """

    _session: session.Session

    name: Optional[str] = None
    path: Optional[str] = None

    size: Optional[int] = None
    author: Optional[str] = None
    license: Optional[str] = None

    mime: Optional[str] = None
    type: Optional[str] = None

    url: Optional[str] = None
    icon_url: Optional[str] = None

    datemodified: Optional[datetime] = None
    datecreated: Optional[datetime] = None

    user: Optional[_user.User] = None
    is_external: bool = False

    def __repr__(self):
        assert (
            self.path is not None
            and self.name is not None
            and self.type is not None
            and self.type.title is not None
        )
        return f"<{self.type.title()}: {os.path.join(self.path, self.name)}>"

    @property
    async def contents(self) -> list[File] | bytes:
        """
        Retrieve contents of the file or directory
        :return: list of files for directories, or file content as bytes
        """
        if self.is_dir:
            # Get the folder contents
            assert self.path is not None
            return await self._session.files_in_dir(self.path)
        else:
            assert self.url is not None
            return (await self._session.rq.get(self.url)).content

    async def delete(self):
        """
        Deletes the file from the session's file manager
        """
        await self._session.rq.post(
            "https://vle.kegs.org.uk/repository/draftfiles_ajax.php",
            params={"action": "delete"},
            data={
                "sesskey": await self._session.sesskey,
                "clientid": await self._session.file_client_id,
                "itemid": await self._session.file_item_id,
                "filename": self.name,
                "filepath": self.path,
            },
        )
        await self._session.file_save_changes()

    @classmethod
    async def from_json(cls, data: dict, _session: session.Session) -> Self:
        """Load a file from JSON data"""
        return cls(
            name=data.get("filename"),
            path=data.get("filepath"),
            size=data.get("size"),
            author=data.get("author"),
            license=data.get("license"),
            mime=data.get("mimetype"),
            type=data.get("type"),
            url=data.get("url"),
            icon_url=data.get("icon"),
            datemodified=datetime.fromtimestamp(data["datemodified"]),
            datecreated=datetime.fromtimestamp(data["datecreated"]),
            user=await _session.connected_user,
            _session=_session,
        )

    @classmethod
    def from_json2(cls, data: dict, _sess: session.Session) -> Self:
        """Load a file from JSON data in a slightly different format"""
        return cls(
            name=data.get("filename"),
            path=data.get("filepath"),
            size=data.get("filesize"),
            url=data.get("fileurl"),
            is_external=data["isexternalfile"],
            mime=data.get("mimetype"),
            type="file",
            datemodified=datetime.fromtimestamp(data["timemodified"]),
            _session=_sess,
        )

    @property
    def is_dir(self):
        """Check if the file is actually a directory"""
        return self.type == "folder"
