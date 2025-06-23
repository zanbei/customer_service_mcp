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
import pygame
import tempfile
import subprocess
import platform
import threading
import sys
import select
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

# AWS Configuration
S3_BUCKET = 'a-web-uw2'

# Initialize AWS clients
transcribe_client = boto3.client('transcribe')
polly_client = boto3.client('polly')
s3_client = boto3.client('s3')

# 全局变量控制播放状态
audio_playing = False
audio_interrupted = False

class DynamicEventHandler(TranscriptResultStreamHandler):
    """改进的事件处理器，支持动态语音结束检测"""
    
    def __init__(self, transcript_result_stream):
        super().__init__(transcript_result_stream)
        self.final_transcript = ""
        self.partial_transcript = ""
        self.speech_ended = False
        self.last_partial_time = time.time()
        self.silence_threshold = 1.5  # 2秒静音阈值
        self.min_speech_duration = 0.5  # 最小语音时长
        self.speech_start_time = None
        self.has_speech = False

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        """处理转录事件，实现动态结束检测"""
        results = transcript_event.transcript.results
        current_time = time.time()
        
        for result in results:
            if result.alternatives:
                transcript_text = result.alternatives[0].transcript.strip()
                
                if result.is_partial:
                    # 处理部分结果
                    if transcript_text:
                        self.partial_transcript = transcript_text
                        self.last_partial_time = current_time
                        if not self.has_speech:
                            self.has_speech = True
                            self.speech_start_time = current_time
                        print(f"🎤 正在识别: {transcript_text}")
                else:
                    # 处理完整结果
                    if transcript_text:
                        self.final_transcript = transcript_text
                        print(f"✅ 识别完成: {transcript_text}")
                        
                        # 检查是否满足最小语音时长
                        if (self.speech_start_time and 
                            current_time - self.speech_start_time >= self.min_speech_duration):
                            self.speech_ended = True
                            return
        
        # 检查静音超时
        if (self.has_speech and 
            current_time - self.last_partial_time > self.silence_threshold):
            print("🔇 检测到静音，结束录制")
            self.speech_ended = True

async def stream_audio_to_text_dynamic():
    """动态语音转文本，基于Amazon Transcribe内置端点检测"""
    client = TranscribeStreamingClient(region="us-west-2")

    # 启用部分结果稳定化和端点检测
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm",
        enable_partial_results_stabilization=True,
        partial_results_stability="high"
    )

    async def write_chunks():
        CHUNK = 320  # 20ms音频块，适合VAD检测
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        MAX_RECORD_SECONDS = 30  # 最大录制时长保护

        p = pyaudio.PyAudio()
        audio_stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

        print("🎤 开始录音，请说话...")
        print("💡 系统会自动检测语音结束")
        
        start_time = time.time()
        
        try:
            while not handler.speech_ended:
                # 检查最大录制时长
                if time.time() - start_time > MAX_RECORD_SECONDS:
                    print("⏰ 达到最大录制时长，自动结束")
                    break
                
                try:
                    data = audio_stream.read(CHUNK, exception_on_overflow=False)
                    await stream.input_stream.send_audio_event(audio_chunk=data)
                    await asyncio.sleep(0.02)  # 20ms间隔
                except Exception as e:
                    print(f"录音错误: {e}")
                    break
                    
        finally:
            print("🔚 录音结束")
            audio_stream.stop_stream()
            audio_stream.close()
            p.terminate()
            await stream.input_stream.end_stream()

    handler = DynamicEventHandler(stream.output_stream)
    
    # 并行执行音频写入和事件处理
    await asyncio.gather(write_chunks(), handler.handle_events())
    
    # 返回最终或部分转录结果
    final_result = handler.final_transcript if handler.final_transcript else handler.partial_transcript
    return final_result.strip()

def synthesize_speech(text: str) -> bytes:
    """
    Convert text to speech using AWS Polly and return the audio data.
    """
    response = polly_client.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId='Joanna'
    )
    
    return response['AudioStream'].read()

def init_audio_system():
    """
    初始化音频系统
    """
    try:
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        print("✅ 音频系统初始化完成")
        return True
    except Exception as e:
        print(f"⚠️ 音频系统初始化失败: {e}")
        return False

def create_interrupt_detector():
    """
    创建跨平台的输入检测器
    """
    if os.name == 'posix':  # Unix/Linux/macOS
        def unix_input_detector(stop_event, playback_finished):
            """Unix系统的非阻塞输入检测"""
            while not playback_finished.is_set():
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    sys.stdin.readline()
                    stop_event.set()
                    return True
            return False
        return unix_input_detector
    else:  # Windows
        def windows_input_detector(stop_event, playback_finished):
            """Windows系统的输入检测"""
            try:
                input()  # 阻塞等待Enter
                if not playback_finished.is_set():
                    stop_event.set()
                    return True
            except:
                pass
            return False
        return windows_input_detector

def play_audio_with_interrupt(audio_data: bytes) -> bool:
    """
    播放音频，支持实时打断功能
    返回True表示播放完成，False表示被打断
    """
    global audio_playing, audio_interrupted
    
    audio_playing = True
    audio_interrupted = False
    
    # 使用更可靠的线程通信机制
    stop_event = threading.Event()
    playback_finished = threading.Event()
    
    def audio_playback():
        """音频播放线程"""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
                pygame.mixer.init()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            pygame.mixer.music.load(temp_file_path)
            pygame.mixer.music.play()
            
            # 更频繁地检查停止信号
            while pygame.mixer.music.get_busy():
                if stop_event.is_set():
                    pygame.mixer.music.stop()  # 立即停止播放
                    break
                time.sleep(0.05)  # 减少检查间隔
            
            playback_finished.set()
            
        except Exception as e:
            print(f"❌ 音频播放错误: {e}")
            playback_finished.set()
        finally:
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    def interrupt_listener():
        """改进的输入监听线程"""
        try:
            print("🔊 正在播放语音回复... (按Enter键可打断播放)")
            
            # 使用跨平台输入检测
            input_detector = create_interrupt_detector()
            if input_detector(stop_event, playback_finished):
                global audio_interrupted
                audio_interrupted = True
                
        except Exception as e:
            print(f"输入监听错误: {e}")
    
    # 启动线程
    playback_thread = threading.Thread(target=audio_playback, daemon=True)
    interrupt_thread = threading.Thread(target=interrupt_listener, daemon=True)
    
    playback_thread.start()
    interrupt_thread.start()
    
    # 等待播放完成或被打断
    playback_finished.wait()
    
    audio_playing = False
    
    if audio_interrupted:
        print("⏹️ 播放已被打断")
        return False
    else:
        print("✅ 语音播放完成")
        return True

def play_audio(audio_data: bytes) -> None:
    """
    跨平台音频播放函数 - 支持打断功能
    """
    try:
        completed = play_audio_with_interrupt(audio_data)
        if not completed:
            print("💡 您可以重新输入问题")
    except Exception as e:
        print(f"❌ 音频播放错误: {e}")
        # 降级到原始播放方案
        fallback_play_audio(audio_data)

def fallback_play_audio(audio_data: bytes) -> None:
    """
    降级音频播放方案（不支持打断）
    """
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        pygame.mixer.music.load(temp_file_path)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        print(f"✅ 音频播放完成 ({platform.system()})")
        
    except Exception as e:
        print(f"❌ 降级播放失败: {e}")
        system_play_audio(audio_data)
    finally:
        try:
            time.sleep(0.5)
            os.unlink(temp_file_path)
        except:
            pass

def system_play_audio(audio_data: bytes) -> None:
    """
    系统命令播放方案
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
        temp_file.write(audio_data)
        temp_file_path = temp_file.name
    
    try:
        system = platform.system().lower()
        if system == 'linux':
            subprocess.run(['mpg123', temp_file_path], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif system == 'darwin':
            subprocess.run(['afplay', temp_file_path])
        elif system == 'windows':
            subprocess.run(['start', '', temp_file_path], shell=True)
    except Exception as e:
        print(f"❌ 系统播放也失败: {e}")
    finally:
        try:
            os.unlink(temp_file_path)
        except:
            pass

class CustomerServiceSystem:
    """Main customer service system that coordinates agents and services."""
    
    def __init__(self, model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0", region: str = "us-west-2"):
        """Initialize the customer service system with its agents and services."""
        self.intent_agent = IntentRecognitionAgent(model_id=model_id, region=region)
        self.order_agent = OrderIssueAgent(model_id=model_id, region=region)
        self.logistics_agent = LogisticsIssueAgent(model_id=model_id, region=region)
        
        self.order_service = OrderService()
        self.sop_service = SOPService()
        
        self.conversations: Dict[str, Dict[str, Any]] = {}
    
    def process_question(self, user_question: str, conversation_id: Optional[str] = None) -> tuple[str, str]:
        """Process a customer question through the multi-agent system."""
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            self.conversations[conversation_id] = {"order_id": None, "history": []}
        
        self.conversations[conversation_id]["history"].append({"role": "user", "content": user_question})
        
        intent, _ = self.intent_agent.process(
            user_question,
            conversation_id,
            history=self.conversations[conversation_id]["history"]
        )
        print(f"Intent recognized: {intent}")
        
        import re
        order_id_match = re.search(r'order\s+(?:id\s+)?(?:number\s+)?(?:#\s*)?(\d+)', 
                                 user_question, re.IGNORECASE)
        if order_id_match:
            self.conversations[conversation_id]["order_id"] = order_id_match.group(1)
        
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
        
        self.conversations[conversation_id]["history"].append({"role": "assistant", "content": response})
        
        return response, conversation_id

async def interactive_session():
    """运行交互会话，支持动态语音输入和文本输入"""
    # 初始化音频系统
    audio_available = init_audio_system()
    if not audio_available:
        print("💡 音频播放可能受限，建议安装: pip install pygame")

    system = CustomerServiceSystem()
    conversation_id = None
    
    print("Welcome to Fashion E-commerce Customer Service!")
    print("You can ask questions about your orders or logistics using voice or text.")
    print("🎤 Press Enter for SMART voice recording (auto-detects speech end)")
    print("✏️  Type your question directly for text input")
    print("During voice playback, press Enter to interrupt and ask a new question.")
    print("Type 'exit' to end the conversation.")
    print("\nAvailable test orders: 123, 456, 789")
    print("Note: Make sure you have set up your AWS credentials for voice interaction.")
    print("-" * 50)
    
    client = MultiServerMCPClient({
        "customer_service": {
            "url": "http://localhost:8000/sse",
            "transport": "sse",
        }
    })

    tools = await client.get_tools()
    process_question_tool = next(tool for tool in tools if tool.name == "process_question")

    while True:
        # 确保不在播放状态时才接受输入
        if audio_playing:
            await asyncio.sleep(0.1)
            continue
            
        # 提供智能语音和文本输入选择
        user_input = await aioconsole.ainput("\nCustomer (🎤 Enter=Smart Voice | ✏️ Type=Text): ")
        
        if user_input.lower() == 'exit':
            print("Thank you for using our customer service. Goodbye!")
            break
        
        # 如果用户按了Enter（空输入），启动智能语音录制
        if not user_input:
            try:
                print("🎤 智能语音录制启动...")
                user_input = await stream_audio_to_text_dynamic()
                print(f"📝 最终转录结果: {user_input}")
            except Exception as e:
                print(f"❌ 语音录制或转录错误: {str(e)}")
                continue
        
        # 检查输入是否有效
        if not user_input.strip():
            print("⚠️ 未检测到有效输入，请重试")
            continue
        
        # 处理用户输入（无论是语音转换的还是直接输入的文本）
        try:
            result = await process_question_tool.arun({
                "question": user_input,
                "conversation_id": conversation_id
            })
            response_data = json.loads(result)
            response_text = response_data['response']
            print(f"\nAgent: {response_text}")
            
            # 转换为语音并播放（支持打断）
            audio_data = synthesize_speech(response_text)
            play_audio(audio_data)
            
            conversation_id = response_data['conversation_id']
            
        except Exception as e:
            print(f"\n❌ 处理问题时出错: {str(e)}")

if __name__ == "__main__":
    asyncio.run(interactive_session())
