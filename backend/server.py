from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class MeetingSummary(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    original_content: str
    summary: str
    action_items: List[str]
    key_points: List[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MeetingSummaryCreate(BaseModel):
    title: str
    content: str

class MeetingSummaryResponse(BaseModel):
    id: str
    title: str
    summary: str
    action_items: List[str]
    key_points: List[str]
    created_at: datetime

# Helper function to prepare data for MongoDB
def prepare_for_mongo(data):
    """Convert datetime objects to ISO strings for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

# Helper function to parse data from MongoDB
def parse_from_mongo(item):
    """Convert ISO strings back to datetime objects"""
    if isinstance(item, dict):
        for key, value in item.items():
            if key.endswith('_at') or key == 'timestamp':
                if isinstance(value, str):
                    try:
                        item[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except:
                        pass
    return item

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "AI Meeting Summarizer API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    prepared_data = prepare_for_mongo(status_obj.dict())
    _ = await db.status_checks.insert_one(prepared_data)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    parsed_checks = [parse_from_mongo(check) for check in status_checks]
    return [StatusCheck(**status_check) for status_check in parsed_checks]

@api_router.post("/summarize-text", response_model=MeetingSummaryResponse)
async def summarize_meeting_text(input: MeetingSummaryCreate):
    """Summarize meeting content from text input"""
    # Validate input
    if not input.title.strip():
        raise HTTPException(status_code=422, detail="Meeting title is required")
    if not input.content.strip():
        raise HTTPException(status_code=422, detail="Meeting content is required")
    
    try:
        # Initialize LLM Chat with emergent key
        chat = LlmChat(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            session_id=f"meeting_summary_{uuid.uuid4()}",
            system_message="""You are an AI assistant specialized in meeting summarization and action item extraction. 
            
Your task is to analyze meeting transcripts and provide:
1. A concise, well-structured summary of the main discussion points
2. Clear, actionable items with specific owners when mentioned
3. Key decisions and important points discussed

Format your response as JSON with this exact structure:
{
  "summary": "A comprehensive summary of the meeting",
  "action_items": ["Action item 1 - Owner: Name", "Action item 2 - Owner: Name"],
  "key_points": ["Key point 1", "Key point 2", "Key point 3"]
}

Be thorough but concise. Extract all action items even if no owner is specified."""
        ).with_model("openai", "gpt-4o")

        # Create user message with meeting content
        user_message = UserMessage(
            text=f"Please analyze this meeting content and provide a summary with action items and key points:\n\n{input.content}"
        )

        # Get AI response
        response = await chat.send_message(user_message)
        
        # Parse the JSON response
        import json
        try:
            ai_data = json.loads(response)
        except json.JSONDecodeError:
            # Fallback parsing if AI doesn't return valid JSON
            lines = response.split('\n')
            ai_data = {
                "summary": "Meeting summary generated",
                "action_items": [line.strip('- ') for line in lines if 'action' in line.lower() or 'todo' in line.lower()][:5],
                "key_points": [line.strip('- ') for line in lines if line.strip() and not ('action' in line.lower() or 'todo' in line.lower())][:5]
            }

        # Create meeting summary object
        meeting_summary = MeetingSummary(
            title=input.title,
            original_content=input.content,
            summary=ai_data.get("summary", "Summary generated"),
            action_items=ai_data.get("action_items", []),
            key_points=ai_data.get("key_points", [])
        )

        # Save to database
        prepared_data = prepare_for_mongo(meeting_summary.dict())
        await db.meeting_summaries.insert_one(prepared_data)

        # Return response
        return MeetingSummaryResponse(
            id=meeting_summary.id,
            title=meeting_summary.title,
            summary=meeting_summary.summary,
            action_items=meeting_summary.action_items,
            key_points=meeting_summary.key_points,
            created_at=meeting_summary.created_at
        )

    except Exception as e:
        logging.error(f"Error in summarize_meeting_text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process meeting: {str(e)}")

@api_router.post("/summarize-file", response_model=MeetingSummaryResponse)
async def summarize_meeting_file(
    title: str = Form(...),
    file: UploadFile = File(...)
):
    """Summarize meeting content from uploaded file"""
    try:
        # Check file type
        if not file.filename.endswith(('.txt', '.docx')):
            raise HTTPException(status_code=400, detail="Only .txt and .docx files are supported")

        # Read file content
        content = ""
        if file.filename.endswith('.txt'):
            content_bytes = await file.read()
            content = content_bytes.decode('utf-8')
        elif file.filename.endswith('.docx'):
            # For simplicity, we'll treat docx as text for now
            # In production, you'd use python-docx library
            content_bytes = await file.read()
            content = content_bytes.decode('utf-8', errors='ignore')

        if len(content.strip()) == 0:
            raise HTTPException(status_code=400, detail="File appears to be empty")

        # Create meeting summary request
        meeting_request = MeetingSummaryCreate(title=title, content=content)
        
        # Use the existing text summarization logic
        return await summarize_meeting_text(meeting_request)

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in summarize_meeting_file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@api_router.get("/meetings", response_model=List[MeetingSummaryResponse])
async def get_meeting_summaries():
    """Get all meeting summaries"""
    try:
        meetings = await db.meeting_summaries.find().sort("created_at", -1).to_list(100)
        parsed_meetings = [parse_from_mongo(meeting) for meeting in meetings]
        
        return [
            MeetingSummaryResponse(
                id=meeting["id"],
                title=meeting["title"],
                summary=meeting["summary"],
                action_items=meeting["action_items"],
                key_points=meeting["key_points"],
                created_at=meeting["created_at"]
            ) for meeting in parsed_meetings
        ]
    except Exception as e:
        logging.error(f"Error in get_meeting_summaries: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch meetings")

@api_router.get("/meetings/{meeting_id}", response_model=MeetingSummaryResponse)
async def get_meeting_summary(meeting_id: str):
    """Get a specific meeting summary"""
    try:
        meeting = await db.meeting_summaries.find_one({"id": meeting_id})
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        parsed_meeting = parse_from_mongo(meeting)
        return MeetingSummaryResponse(
            id=parsed_meeting["id"],
            title=parsed_meeting["title"],
            summary=parsed_meeting["summary"],
            action_items=parsed_meeting["action_items"],
            key_points=parsed_meeting["key_points"],
            created_at=parsed_meeting["created_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in get_meeting_summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch meeting")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()