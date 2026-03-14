"""
Conversation memory management for multi-turn dialogues.
Maintains context, history, and session state.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from collections import OrderedDict
from threading import Lock

from common.models.schemas import ConversationContext, ChatMessage, Intent, ExtractedEntities


class ConversationMemory:
    """
    In-memory conversation storage with LRU eviction.
    For production, replace with Redis-backed implementation.
    """
    
    def __init__(self, max_sessions: int = 1000, session_ttl_hours: int = 1):
        """
        Initialize conversation memory.
        
        Args:
            max_sessions: Maximum number of sessions to keep in memory
            session_ttl_hours: Session expiry time in hours
        """
        self.sessions: OrderedDict[str, ConversationContext] = OrderedDict()
        self.max_sessions = max_sessions
        self.session_ttl = timedelta(hours=session_ttl_hours)
        self._lock = Lock()
    
    def create_session(self, session_id: Optional[str] = None) -> ConversationContext:
        """
        Create a new conversation session.
        
        Args:
            session_id: Optional custom session ID
            
        Returns:
            New ConversationContext
        """
        with self._lock:
            if session_id is None:
                session_id = str(uuid.uuid4())
            
            context = ConversationContext(session_id=session_id)
            self.sessions[session_id] = context
            
            # Evict old sessions if needed
            self._evict_if_needed()
            
            return context
    
    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """
        Get an existing session by ID.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            ConversationContext if found and valid, None otherwise
        """
        with self._lock:
            context = self.sessions.get(session_id)
            
            if context is None:
                return None
            
            # Check if session has expired
            if datetime.now() - context.last_activity > self.session_ttl:
                del self.sessions[session_id]
                return None
            
            # Move to end (LRU)
            self.sessions.move_to_end(session_id)
            return context
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> ConversationContext:
        """
        Get existing session or create a new one.
        
        Args:
            session_id: Optional session ID
            
        Returns:
            ConversationContext (existing or new)
        """
        if session_id:
            context = self.get_session(session_id)
            if context:
                return context
        
        return self.create_session(session_id)
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a message to a session.
        
        Args:
            session_id: Session to add message to
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata
            
        Returns:
            True if successful, False if session not found
        """
        context = self.get_session(session_id)
        if context is None:
            return False
        
        context.add_message(role, content, metadata)
        return True
    
    def update_context(
        self,
        session_id: str,
        intent: Optional[Intent] = None,
        entities: Optional[ExtractedEntities] = None,
        last_stock: Optional[str] = None
    ) -> bool:
        """
        Update session context with new information.
        
        Args:
            session_id: Session to update
            intent: Last detected intent
            entities: Last extracted entities
            last_stock: Last mentioned stock symbol
            
        Returns:
            True if successful, False if session not found
        """
        context = self.get_session(session_id)
        if context is None:
            return False
        
        if intent:
            context.last_intent = intent
        if entities:
            context.last_entities = entities
        if last_stock:
            context.last_stock_mentioned = last_stock
        
        return True
    
    def get_chat_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[tuple]:
        """
        Get chat history for LLM context.
        
        Args:
            session_id: Session ID
            limit: Maximum messages to return
            
        Returns:
            List of (role, content) tuples
        """
        context = self.get_session(session_id)
        if context is None:
            return []
        
        messages = context.get_recent_messages(limit)
        return [(msg.role, msg.content) for msg in messages]
    
    def get_last_stock(self, session_id: str) -> Optional[str]:
        """
        Get the last mentioned stock in a session.
        Useful for follow-up questions like "What about its PE ratio?"
        """
        context = self.get_session(session_id)
        if context:
            return context.last_stock_mentioned
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False
    
    def _evict_if_needed(self):
        """Evict oldest sessions if over capacity."""
        while len(self.sessions) > self.max_sessions:
            # Remove oldest (first) item
            self.sessions.popitem(last=False)
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions removed
        """
        with self._lock:
            now = datetime.now()
            expired = [
                sid for sid, ctx in self.sessions.items()
                if now - ctx.last_activity > self.session_ttl
            ]
            
            for sid in expired:
                del self.sessions[sid]
            
            return len(expired)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "active_sessions": len(self.sessions),
            "max_sessions": self.max_sessions,
            "session_ttl_hours": self.session_ttl.total_seconds() / 3600,
        }


# Singleton instance
_memory = None

def get_conversation_memory() -> ConversationMemory:
    """Get or create the conversation memory singleton."""
    global _memory
    if _memory is None:
        _memory = ConversationMemory()
    return _memory
