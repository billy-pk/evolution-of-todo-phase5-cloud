"""
ChatKit Integration Routes

This module provides endpoints to integrate OpenAI ChatKit with our custom
conversation database. It acts as a bridge between ChatKit's expected API
and our conversation/message storage.

Endpoints:
- POST /chatkit - Main ChatKit protocol endpoint (no /api prefix)
- POST /api/chatkit/session - Create a ChatKit session
- POST /api/chatkit/refresh - Refresh a ChatKit session
- POST /api/chatkit/threads - Manage threads (conversations)
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse, Response
from sqlmodel import Session, select
from datetime import datetime, UTC, timedelta
import json
import logging
import jwt
from typing import Optional, AsyncIterator
import asyncio

from db import get_session
from config import settings
from models import Conversation, Message
from middleware import JWTBearer, verify_token
from schemas import ChatRequest, ChatResponse
from services.chatkit_server import TaskManagerChatKitServer, SimpleMemoryStore
from chatkit.server import StreamingResult, NonStreamingResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chatkit", tags=["chatkit"])
# ChatKit protocol endpoint (no /api prefix)
chatkit_router = APIRouter(tags=["chatkit-protocol"])

# Initialize ChatKit server instance
data_store = SimpleMemoryStore()
chatkit_server = TaskManagerChatKitServer(data_store)


class ChatKitSessionManager:
    """Manages ChatKit sessions and token generation."""

    @staticmethod
    def create_session_token(user_id: str, duration_minutes: int = 30) -> tuple[str, str]:
        """
        Create a ChatKit-compatible session token.

        Returns:
            Tuple of (client_secret, refresh_token)
        """
        now = datetime.now(UTC)

        # Create session payload
        payload = {
            "user_id": user_id,
            "type": "chatkit_session",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=duration_minutes)).timestamp()),
        }

        # Sign with Better Auth secret (same as JWT validation)
        client_secret = jwt.encode(
            payload,
            settings.BETTER_AUTH_SECRET,
            algorithm="HS256"
        )

        return client_secret, user_id

    @staticmethod
    def verify_session_token(token: str) -> Optional[str]:
        """
        Verify a ChatKit session token and extract user_id.

        Returns:
            User ID if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                settings.BETTER_AUTH_SECRET,
                algorithms=["HS256"]
            )
            if payload.get("type") != "chatkit_session":
                return None
            return payload.get("user_id")
        except jwt.InvalidTokenError:
            return None


@router.post("/session")
async def create_chatkit_session(request: Request):
    """
    Create a new ChatKit session.

    This endpoint:
    1. Validates the JWT token from Better Auth
    2. Creates a ChatKit-compatible session token
    3. Returns the client_secret for use with ChatKit component

    Returns:
        {
            "client_secret": "jwt_token",
            "user_id": "user_uuid"
        }

    Raises:
        HTTPException: 401 if not authenticated
    """
    try:
        # Extract and validate JWT token from Authorization header
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header"
            )

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate JWT using JWKS (EdDSA) validation from middleware
        user_id = verify_token(token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Create ChatKit session
        client_secret, _ = ChatKitSessionManager.create_session_token(user_id)

        logger.info(f"Created ChatKit session for user {user_id}")

        return {
            "client_secret": client_secret,
            "user_id": user_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ChatKit session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create ChatKit session"
        )


@router.post("/refresh")
async def refresh_chatkit_session(request: Request):
    """
    Refresh an expired ChatKit session token.

    Body:
        {
            "token": "expired_client_secret"
        }

    Returns:
        {
            "client_secret": "new_jwt_token",
            "user_id": "user_uuid"
        }

    Raises:
        HTTPException: 401 if token is invalid
    """
    try:
        body = await request.json()
        token = body.get("token")

        if not token:
            raise HTTPException(status_code=400, detail="Missing token in request body")

        # Verify and extract user_id from token (even if expired)
        try:
            payload = jwt.decode(
                token,
                settings.BETTER_AUTH_SECRET,
                algorithms=["HS256"],
                options={"verify_exp": False}  # Allow expired tokens for refresh
            )
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = payload.get("user_id")
        if not user_id or payload.get("type") != "chatkit_session":
            raise HTTPException(status_code=401, detail="Invalid session token")

        # Create new session token
        client_secret, _ = ChatKitSessionManager.create_session_token(user_id)

        logger.info(f"Refreshed ChatKit session for user {user_id}")

        return {
            "client_secret": client_secret,
            "user_id": user_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing ChatKit session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to refresh ChatKit session"
        )


@router.get("/threads")
async def list_threads(
    request: Request,
    session: Session = Depends(get_session)
):
    """
    List all conversation threads (conversations) for the authenticated user.

    Returns:
        {
            "threads": [
                {
                    "id": "conversation_uuid",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "message_count": 5
                }
            ]
        }
    """
    try:
        # Extract user_id from session token
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        token = auth_header[7:]
        user_id = ChatKitSessionManager.verify_session_token(token)

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session token")

        # Get user's conversations
        statement = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        conversations = session.exec(statement).all()

        threads = [
            {
                "id": str(conv.id),
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": len(conv.messages) if hasattr(conv, 'messages') else 0
            }
            for conv in conversations
        ]

        return {"threads": threads}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing threads: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to list threads"
        )


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Get a specific thread (conversation) with its messages.

    Returns:
        {
            "id": "conversation_uuid",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "messages": [
                {
                    "id": "message_uuid",
                    "role": "user",
                    "content": "Hello",
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ]
        }
    """
    try:
        # Validate user ownership
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        token = auth_header[7:]
        user_id = ChatKitSessionManager.verify_session_token(token)

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session token")

        # Get conversation
        statement = select(Conversation).where(
            Conversation.id == thread_id,
            Conversation.user_id == user_id
        )
        conversation = session.exec(statement).first()

        if not conversation:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Get messages
        msg_statement = (
            select(Message)
            .where(Message.conversation_id == thread_id)
            .order_by(Message.created_at.asc())
        )
        messages = session.exec(msg_statement).all()

        return {
            "id": str(conversation.id),
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "messages": [
                {
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thread: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get thread"
        )


@router.post("/threads")
async def create_thread(
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Create a new thread (conversation).

    Returns:
        {
            "id": "new_conversation_uuid",
            "created_at": "2024-01-01T00:00:00Z"
        }
    """
    try:
        # Validate user
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        token = auth_header[7:]
        user_id = ChatKitSessionManager.verify_session_token(token)

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session token")

        # Create new conversation
        conversation = Conversation(user_id=user_id)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)

        logger.info(f"Created new thread {conversation.id} for user {user_id}")

        return {
            "id": str(conversation.id),
            "created_at": conversation.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating thread: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create thread"
        )


@router.post("/messages")
async def add_message(
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Add a message to a thread and get AI response.

    This endpoint bridges ChatKit with our existing chat system.
    It processes messages through our AI agent and returns the response.

    Body:
        {
            "thread_id": "conversation_uuid",
            "message": "User message text"
        }

    Returns:
        {
            "message_id": "message_uuid",
            "response_id": "response_message_uuid",
            "response": "AI response text",
            "thread_id": "conversation_uuid"
        }
    """
    try:
        # Validate user
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        token = auth_header[7:]
        user_id = ChatKitSessionManager.verify_session_token(token)

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session token")

        # Parse request body
        body = await request.json()
        thread_id = body.get("thread_id")
        message_text = body.get("message")

        if not thread_id or not message_text:
            raise HTTPException(
                status_code=400,
                detail="Missing thread_id or message"
            )

        # Verify conversation ownership
        statement = select(Conversation).where(
            Conversation.id == thread_id,
            Conversation.user_id == user_id
        )
        conversation = session.exec(statement).first()

        if not conversation:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Import here to avoid circular imports
        from services.agent import process_message

        # Load conversation history
        msg_statement = (
            select(Message)
            .where(Message.conversation_id == thread_id)
            .order_by(Message.created_at.asc())
        )
        existing_messages = session.exec(msg_statement).all()

        message_history = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in existing_messages
        ]

        # Save user message
        user_message = Message(
            conversation_id=thread_id,
            user_id=user_id,
            role="user",
            content=message_text
        )
        session.add(user_message)
        session.commit()
        session.refresh(user_message)

        # Process through AI agent
        try:
            agent_result = await process_message(
                user_id=user_id,
                message=message_text,
                conversation_history=message_history
            )

            # Save assistant response
            assistant_message = Message(
                conversation_id=thread_id,
                user_id=user_id,
                role="assistant",
                content=agent_result["response"],
                tool_calls=str(agent_result.get("tool_calls", []))
            )
            session.add(assistant_message)

            # Update conversation timestamp
            conversation.updated_at = datetime.now(UTC)
            session.add(conversation)
            session.commit()
            session.refresh(assistant_message)

            logger.info(
                f"Added message to thread {thread_id} for user {user_id}"
            )

            return {
                "message_id": str(user_message.id),
                "response_id": str(assistant_message.id),
                "response": agent_result["response"],
                "thread_id": str(thread_id)
            }

        except Exception as agent_error:
            logger.error(
                f"Error processing message through agent: {str(agent_error)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process message: {str(agent_error)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to add message"
        )


# ============================================================================
# ChatKit Protocol Endpoint (for ChatKit.js client)
# ============================================================================

@chatkit_router.post("/chatkit")
async def chatkit_endpoint(request: Request):
    """
    Main ChatKit protocol endpoint.

    This endpoint receives requests from the ChatKit.js client and forwards
    them to the ChatKitServer for processing.

    All communication happens through a single POST endpoint that returns
    either JSON directly or streams SSE JSON events.

    Note: Duplicate prevention is handled at the MCP tool level, not here.
    """
    try:
        logger.info("=== ChatKit endpoint received request ===")

        # Get JWT token from headers (Better Auth JWT, not ChatKit session)
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("Missing Authorization header in ChatKit request")
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate using JWKS (EdDSA) - same as other endpoints
        user_id = verify_token(token)

        if not user_id:
            logger.warning("Invalid JWT token in ChatKit request")
            raise HTTPException(status_code=401, detail="Invalid token")

        logger.info(f"ChatKit request authenticated for user {user_id}")

        # Get request body
        body = await request.body()

        # Create context with user_id for authorization
        context = {"user_id": user_id}

        # Process request through ChatKit server
        logger.info("Processing request through ChatKit server")
        result = await chatkit_server.process(body, context)

        # Return streaming or JSON response
        if isinstance(result, StreamingResult):
            logger.info("Returning streaming response")
            return StreamingResponse(result, media_type="text/event-stream")
        elif isinstance(result, NonStreamingResult):
            logger.info("Returning JSON response")
            return Response(content=result.json, media_type="application/json")
        else:
            # Fallback for any other response type
            logger.info(f"Returning response of type {type(result)}")
            response_content = str(result)
            return Response(content=response_content, media_type="application/json")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ChatKit endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"ChatKit endpoint error: {str(e)}"
        )
