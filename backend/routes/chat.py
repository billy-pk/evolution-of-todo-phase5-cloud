"""
Chat Endpoint - AI-Powered Conversational Interface

This module implements the chat endpoint for User Story 6 (Conversation History).
It enables users to interact with the AI assistant through natural language,
with full conversation history persistence across sessions.

Endpoint: POST /api/{user_id}/chat
Authentication: Required (JWT Bearer token)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from typing import Optional
from uuid import UUID
from datetime import datetime, UTC
import time

from db import get_session
from schemas import ChatRequest, ChatResponse
from models import Conversation, Message
from services.agent import process_message
from middleware import JWTBearer
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


async def verify_user_access(request: Request, user_id: str) -> str:
    """
    Verify that the JWT token user_id matches the path parameter user_id.

    Args:
        request: FastAPI request object (contains JWT token)
        user_id: user_id from path parameter

    Returns:
        str: Validated user_id

    Raises:
        HTTPException: 403 if user_id mismatch
    """
    # JWT token is already validated by JWTBearer middleware
    # Here we just verify the user_id matches
    token_user_id = request.state.user_id if hasattr(request.state, 'user_id') else user_id

    if token_user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="User ID in token does not match path parameter"
        )

    return token_user_id


@router.post("/{user_id}/chat", response_model=ChatResponse, dependencies=[Depends(JWTBearer())])
async def chat(
    user_id: str,
    chat_request: ChatRequest,
    session: Session = Depends(get_session),
    verified_user: str = Depends(verify_user_access)
):
    """
    Process a chat message from the user with AI assistant.

    This endpoint:
    1. Creates or loads conversation
    2. Saves user message
    3. Calls AI agent with conversation history
    4. Saves assistant response
    5. Returns response with conversation context

    Args:
        user_id: User ID from path parameter
        chat_request: Chat request body (message, optional conversation_id)
        session: Database session
        verified_user: Validated user_id from JWT

    Returns:
        ChatResponse: AI response with conversation_id, messages, and metadata

    Raises:
        HTTPException: 400/404/500 for various errors
    """
    try:
        logger.info(f"=== CHAT ENDPOINT: Received request for user {user_id}")
        logger.info(f"=== CHAT ENDPOINT: Message: {chat_request.message}")
        logger.info(f"=== CHAT ENDPOINT: Conversation ID: {chat_request.conversation_id}")

        # Step 1: Load or create conversation
        conversation = await _get_or_create_conversation(
            session=session,
            user_id=user_id,
            conversation_id=chat_request.conversation_id
        )

        # Step 2: Load conversation history (last 20 messages for context)
        message_history = await _load_conversation_history(
            session=session,
            conversation_id=conversation.id,
            user_id=user_id,
            limit=20  # Only load recent context for better performance
        )

        # Step 3: Save user message
        user_message = Message(
            conversation_id=conversation.id,
            user_id=user_id,
            role="user",
            content=chat_request.message
        )
        session.add(user_message)
        session.commit()

        # Step 4: Call AI agent with history
        logger.info(f"Processing message for user {user_id}, conversation {conversation.id}")

        start_time = time.time()
        agent_result = await process_message(
            user_id=user_id,
            message=chat_request.message,
            conversation_history=message_history
        )
        agent_duration = time.time() - start_time
        logger.info(f"⏱️ Agent processing took {agent_duration:.2f} seconds")

        # Step 5: Save assistant message
        assistant_message = Message(
            conversation_id=conversation.id,
            user_id=user_id,
            role="assistant",
            content=agent_result["response"],
            tool_calls=str(agent_result.get("tool_calls", []))  # JSON string
        )
        session.add(assistant_message)

        # Step 6: Update conversation timestamp
        conversation.updated_at = datetime.now(UTC)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)

        # Step 7: Build response
        # Reload messages to include new ones
        all_messages = await _load_conversation_history(
            session=session,
            conversation_id=conversation.id,
            user_id=user_id
        )

        return ChatResponse(
            conversation_id=conversation.id,
            response=agent_result["response"],
            tool_calls=agent_result.get("tool_calls", []),
            messages=all_messages,
            metadata={
                "model": agent_result.get("model", "gpt-4o"),
                "tokens_used": agent_result.get("tokens_used", 0),
                "conversation_message_count": len(all_messages)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )


async def _get_or_create_conversation(
    session: Session,
    user_id: str,
    conversation_id: Optional[UUID] = None
) -> Conversation:
    """
    Get existing conversation or create new one.

    Args:
        session: Database session
        user_id: User ID
        conversation_id: Optional conversation ID to load

    Returns:
        Conversation: Loaded or newly created conversation

    Raises:
        HTTPException: 404 if conversation not found or doesn't belong to user
    """
    if conversation_id:
        # Load existing conversation
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        conversation = session.exec(statement).first()

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found or access denied"
            )

        return conversation
    else:
        # Create new conversation
        conversation = Conversation(user_id=user_id)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        logger.info(f"Created new conversation {conversation.id} for user {user_id}")
        return conversation


async def _load_conversation_history(
    session: Session,
    conversation_id: UUID,
    user_id: str,
    limit: int = 100
) -> list[dict]:
    """
    Load conversation message history.

    Args:
        session: Database session
        conversation_id: Conversation UUID
        user_id: User ID (for security check)
        limit: Maximum number of messages to load (default 100)

    Returns:
        List of message dicts in format expected by AI agent
    """
    statement = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.user_id == user_id
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )

    messages = session.exec(statement).all()

    # Convert to agent format (newest to oldest, then reverse)
    message_history = [
        {
            "role": msg.role,
            "content": msg.content
        }
        for msg in reversed(messages)  # Reverse to get chronological order
    ]

    return message_history
