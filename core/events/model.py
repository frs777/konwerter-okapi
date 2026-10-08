from dataclasses import dataclass
from enum import Enum
from core.document.model import Skeleton
class EventType(str,Enum):
 START_DOCUMENT='START_DOCUMENT'; TEXT_UNIT='TEXT_UNIT'; DOCUMENT_PART='DOCUMENT_PART'; END_DOCUMENT='END_DOCUMENT'; START_GROUP='START_GROUP'; END_GROUP='END_GROUP'; START_SUBDOCUMENT='START_SUBDOCUMENT'; END_SUBDOCUMENT='END_SUBDOCUMENT'; START_SUBFILTER='START_SUBFILTER'; END_SUBFILTER='END_SUBFILTER'
@dataclass(frozen=True,slots=True)
class StartDocument:
    name: str
    source_path: str | None = None
@dataclass(frozen=True,slots=True)
class DocumentPart:content:str
@dataclass(frozen=True,slots=True)
class Ending:id:str|None=None
@dataclass(frozen=True,slots=True)
class StartGroup:parent_id:str|None; id:str; common_tag_type:str; skeleton:Skeleton
@dataclass(frozen=True,slots=True)
class StartSubDocument:id:str; parent_id:str|None=None; filter_id:str|None=None
@dataclass(frozen=True,slots=True)
class StartSubfilter:id:str; filter_name:str; parent_group_id:str|None; skeleton:Skeleton
@dataclass(frozen=True,slots=True)
class EndSubfilter:id:str
@dataclass(frozen=True,slots=True)
class Event:type:EventType; resource:object; skeleton:Skeleton|None=None
