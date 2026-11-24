import enum


class UserRole(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    EDITOR = "editor"
    ADMIN = "admin"


class StoryType(str, enum.Enum):
    VERIFIED_BIOGRAPHY = "verified_biography"
    COMMUNITY_STORY = "community_story"


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class PublicationStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SourceType(str, enum.Enum):
    BOOK = "book"
    ARTICLE = "article"
    INTERVIEW = "interview"
    DOCUMENT = "document"
    VIDEO = "video"
    ARCHIVE = "archive"
    OTHER = "other"
