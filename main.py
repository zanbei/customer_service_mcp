import uuid
import json
import asyncio
import aioconsole
import boto3
import os
import pyaudio
import wave
import time
import requests
from typing import Optional, Dict, Any
from langchain_aws import ChatBedrock
from langchain_mcp_adapters.client import MultiServerMCPClient
from agents.intent_recognition_agent import IntentRecognitionAgent
from agents.order_issue_agent import OrderIssueAgent
from agents.logistics_issue_agent import LogisticsIssueAgent
from services.order_service import OrderService
from services.sop_service import SOPService
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
import aiofile

# # AWS Configuration
# AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
# AWS_REGION = os.environ.get('AWS_REGION', 'us-west-2')
S3_BUCKET = 'a-web-uw2'

# if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET]):
#     raise ValueError("Missing required AWS environment variables")

# # Initialize AWS session
# boto3.setup_default_session(
#     aws_access_key_id=AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#     region_name=AWS_REGION
# )

# Initialize AWS clients
transcribe_client = boto3.client('transcribe')
polly_client = boto3.client('polly')
s3_client = boto3.client('s3')

class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, transcript_result_stream):
        super().__init__(transcript_result_stream)
        self.final_transcript = ""

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if result.is_partial == False:
                self.final_transcript = result.alternatives[0].transcript

async def stream_audio_to_text():
    client = TranscribeStreamingClient(region="us-west-2")

    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm",
    )

    async def write_chunks():
        CHUNK = 1024  # Reduced chunk size
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        RECORD_SECONDS = 5

        p = pyaudio.PyAudio()
        audio_stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

        print(f"Recording for {RECORD_SECONDS} seconds...")

        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = audio_stream.read(CHUNK)
            await stream.input_stream.send_audio_event(audio_chunk=data)
            await asyncio.sleep(0.01)  # Small delay to prevent overwhelming the service

        print("Recording finished.")
        audio_stream.stop_stream()
        audio_stream.close()
        p.terminate()
        await stream.input_stream.end_stream()

    handler = MyEventHandler(stream.output_stream)
    await asyncio.gather(write_chunks(), handler.handle_events())

    return handler.final_transcript.strip()

def synthesize_speech(text: str) -> bytes:
    """
    Convert text to speech using AWS Polly and return the audio data.
    """
    response = polly_client.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId='Joanna'  # Choose an appropriate voice
    )
    
    return response['AudioStream'].read()

def play_audio(audio_data: bytes) -> None:
    """
    Play the audio data using the default system audio player.
    """
    import tempfile
    import subprocess
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
        temp_file.write(audio_data)
        temp_file_path = temp_file.name
    
    # Use the appropriate command based on the operating system
    if os.name == 'posix':  # macOS or Linux
        subprocess.run(['afplay', temp_file_path])
    elif os.name == 'nt':  # Windows
        subprocess.run(['start', temp_file_path], shell=True)
    else:
        print("Unsupported operating system for audio playback.")
    
    # Clean up the temporary file
    os.unlink(temp_file_path)

class CustomerServiceSystem:
    """Main customer service system that coordinates agents and services."""
    
    def __init__(self, model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0", region: str = "us-west-2"):
        """Initialize the customer service system with its agents and services."""
        # Initialize LLM
        # self.llm = ChatBedrock(model_id=model_id, region_name=region)
        
        # Initialize agents
        self.intent_agent = IntentRecognitionAgent(model_id=model_id, region=region)
        self.order_agent = OrderIssueAgent(model_id=model_id, region=region)
        self.logistics_agent = LogisticsIssueAgent(model_id=model_id, region=region)
        
        # Initialize services
        self.order_service = OrderService()
        self.sop_service = SOPService()
        
        # Store active conversations
        self.conversations: Dict[str, Dict[str, Any]] = {}
    
    def process_question(self, user_question: str, conversation_id: Optional[str] = None) -> tuple[str, str]:
        """Process a customer question through the multi-agent system.
        
        Args:
            user_question: The user's question
            conversation_id: Optional conversation ID for maintaining context
            
        Returns:
            tuple[str, str]: (response message, conversation_id)
        """
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            self.conversations[conversation_id] = {"order_id": None, "history": []}
        
        # Add user question to conversation history
        self.conversations[conversation_id]["history"].append({"role": "user", "content": user_question})
        
        # First layer: Intent recognition
        intent, _ = self.intent_agent.process(
            user_question,
            conversation_id,
            history=self.conversations[conversation_id]["history"]
        )
        print(f"Intent recognized: {intent}")
        # Extract order ID if present in the question
        import re
        order_id_match = re.search(r'order\s+(?:id\s+)?(?:number\s+)?(?:#\s*)?(\d+)', 
                                 user_question, re.IGNORECASE)
        if order_id_match:
            self.conversations[conversation_id]["order_id"] = order_id_match.group(1)
        
        # Second layer: Process based on intent
        if intent == "ORDER":
            response, _ = self.order_agent.process(
                user_question, 
                conversation_id,
                order_id=self.conversations[conversation_id].get("order_id"),
                history=self.conversations[conversation_id]["history"]
            )
        elif intent == "LOGISTICS":
            response, _ = self.logistics_agent.process(
                user_question,
                conversation_id,
                order_id=self.conversations[conversation_id].get("order_id"),
                history=self.conversations[conversation_id]["history"]
            )
        else:
            response = "I'm not sure if your question is about an order or logistics issue. Could you please provide more details?"
        
        # Add agent response to conversation history
        self.conversations[conversation_id]["history"].append({"role": "assistant", "content": response})
        
        return response, conversation_id

async def interactive_session():
    # """Run an interactive session with the customer service system."""
    # if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION]):
    #     print("Error: Required environment variables are not set. Please set the following:")
    #     print("AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION")
    #     return

    system = CustomerServiceSystem()
    conversation_id = None
    
    print("Welcome to Fashion E-commerce Customer Service!")
    print("You can ask questions about your orders or logistics using voice or text.")
    print("Type 'voice' to use voice input, 'record' to record audio, or type your question directly.")
    print("Type 'exit' to end the conversation.")
    print("\nAvailable test orders: 123, 456, 789")
    print("\nNote: Make sure you have set up your AWS credentials for voice interaction.")
    print("-" * 50)
    
    client = MultiServerMCPClient(
        {
            "customer_service": {
                "url": "http://localhost:8000/sse",
                "transport": "sse",
            }
        }
    )

    tools = await client.get_tools()
    process_question_tool = next(tool for tool in tools if tool.name == "process_question")

    while True:
        user_input = await aioconsole.ainput("\nCustomer (press Enter to start recording, or type your question): ")
        if user_input.lower() == 'exit':
            print("Thank you for using our customer service. Goodbye!")
            break
        
        if not user_input:  # If the user just pressed Enter, start recording
            try:
                user_input = await stream_audio_to_text()
                print(f"Transcribed text: {user_input}")
            except Exception as e:
                print(f"Error recording or transcribing audio: {str(e)}")
                continue
        
        if not user_input.strip():
            print("No input detected. Please try again.")
            continue
        
        # Process the user input (whether typed or transcribed)
        try:
            result = await process_question_tool.arun({
                "question": user_input,
                "conversation_id": conversation_id
            })
            response_data = json.loads(result)
            response_text = response_data['response']
            print(f"\nAgent: {response_text}")
            
            # Convert response to speech and play it
            audio_data = synthesize_speech(response_text)
            play_audio(audio_data)
            print("Voice response played.")
            
            conversation_id = response_data['conversation_id']
        except Exception as e:
            print(f"\nError processing question: {str(e)}")

if __name__ == "__main__":
    asyncio.run(interactive_session())
