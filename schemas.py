"""
Database Schema Models for EasyRef Literature Review Assistant.

This module defines the data models that correspond to the database tables
defined in init_tables.sql. These classes can be used for type checking,
data validation, serialization/deserialization, and documentation purposes.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class UserProfile:
    """User profile information and membership details."""
    username: Optional[str]
    nickname: Optional[str]
    avatar_url: Optional[str]
    id: Optional[UUID] = None
    membership_type: str = "free"
    membership_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Paper:
    """Core metadata for academic papers retrieved from scholarly sources."""
    id: str
    title: str
    authors: Optional[str] = None
    pub_year: Optional[int] = None
    num_citations: int = 0
    bib: Optional[str] = None
    pub_url: Optional[str] = None
    bib_url: Optional[str] = None
    citedby_url: Optional[str] = None
    abstract: Optional[str] = None
    keywords: Optional[str] = None
    doi: Optional[str] = None
    pdf_url: Optional[str] = None
    file_size: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class SearchTask:
    """Search task information for tracking progress and status."""
    session_id: str
    user_id: str
    keyword: str
    year_low: Optional[int] = None
    year_high: Optional[int] = None
    limit_num: int = 20
    status: str = "pending"
    created_at: Optional[datetime] = None


@dataclass
class SearchResult:
    """Search result for tracking the relationship between users, search sessions, and papers."""
    id: str
    session_id: str
    paper_id: str
    result_index: int
    created_at: Optional[datetime] = None