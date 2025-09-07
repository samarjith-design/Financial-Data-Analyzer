from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import asyncio
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from collections import deque
import pandas as pd
import numpy as np
from emergentintegrations.llm.chat import LlmChat, UserMessage
import time

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(
    title="FinTech AI - Real-time Financial Data Platform",
    description="AI-powered financial data streaming with pattern recognition",
    version="1.0.0"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# In-memory data structures for real-time processing
class TechnicalIndicators:
    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.prices = deque(maxlen=window_size)
        self.volumes = deque(maxlen=window_size)
        self.timestamps = deque(maxlen=window_size)
        
    def add_data_point(self, price: float, volume: int, timestamp: datetime):
        self.prices.append(price)
        self.volumes.append(volume)
        self.timestamps.append(timestamp)
    
    def calculate_sma(self, period: int = 20) -> Optional[float]:
        if len(self.prices) < period:
            return None
        recent_prices = list(self.prices)[-period:]
        return sum(recent_prices) / len(recent_prices)
    
    def calculate_ema(self, period: int = 20) -> Optional[float]:
        if len(self.prices) < period:
            return None
        prices_list = list(self.prices)
        multiplier = 2 / (period + 1)
        ema = prices_list[0]
        for price in prices_list[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema
    
    def calculate_rsi(self, period: int = 14) -> Optional[float]:
        if len(self.prices) < period + 1:
            return None
        
        prices_list = list(self.prices)
        deltas = [prices_list[i] - prices_list[i-1] for i in range(1, len(prices_list))]
        
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_vwap(self) -> Optional[float]:
        if len(self.prices) < 1:
            return None
        
        prices_list = list(self.prices)
        volumes_list = list(self.volumes)
        
        total_pv = sum(p * v for p, v in zip(prices_list, volumes_list))
        total_volume = sum(volumes_list)
        
        return total_pv / total_volume if total_volume > 0 else None
    
    def calculate_bollinger_bands(self, period: int = 20, std_dev: int = 2) -> Dict[str, Optional[float]]:
        if len(self.prices) < period:
            return {"upper": None, "middle": None, "lower": None}
        
        recent_prices = list(self.prices)[-period:]
        sma = sum(recent_prices) / len(recent_prices)
        variance = sum((x - sma) ** 2 for x in recent_prices) / len(recent_prices)
        std = variance ** 0.5
        
        return {
            "upper": sma + (std * std_dev),
            "middle": sma,
            "lower": sma - (std * std_dev)
        }

# Global variables for data management
active_symbols: Dict[str, TechnicalIndicators] = {}
websocket_connections: Dict[str, WebSocket] = {}
mock_data_tasks: Dict[str, asyncio.Task] = {}

# Pydantic models
class SymbolRequest(BaseModel):
    symbol: str
    timeframe: str = "1Min"

class TechnicalIndicatorData(BaseModel):
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_20: Optional[float] = None
    rsi: Optional[float] = None
    vwap: Optional[float] = None
    bollinger_bands: Dict[str, Optional[float]] = {}

class MarketAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    analysis: str
    pattern_detected: Optional[str] = None
    confidence_score: float
    recommendation: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PriceAlert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    condition: str  # "above", "below"
    target_price: float
    current_price: float
    triggered: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Mock data generator for demo purposes
async def generate_mock_market_data(symbol: str, websocket: WebSocket):
    """Generate realistic mock market data for demo purposes"""
    base_price = {"AAPL": 180.0, "GOOGL": 2800.0, "TSLA": 250.0, "MSFT": 420.0, "NVDA": 800.0}.get(symbol, 100.0)
    current_price = base_price
    
    while True:
        try:
            # Generate realistic price movement
            volatility = 0.02  # 2% volatility
            price_change = np.random.normal(0, volatility)
            current_price *= (1 + price_change)
            
            # Generate volume
            volume = np.random.randint(1000, 10000)
            
            # Create timestamp
            timestamp = datetime.now(timezone.utc)
            
            # Update technical indicators
            if symbol not in active_symbols:
                active_symbols[symbol] = TechnicalIndicators()
            
            indicators = active_symbols[symbol]
            indicators.add_data_point(current_price, volume, timestamp)
            
            # Calculate technical indicators
            sma_20 = indicators.calculate_sma(20)
            sma_50 = indicators.calculate_sma(50)
            ema_20 = indicators.calculate_ema(20)
            rsi = indicators.calculate_rsi(14)
            vwap = indicators.calculate_vwap()
            bollinger = indicators.calculate_bollinger_bands()
            
            # Create data packet
            data = {
                "type": "market_data",
                "symbol": symbol,
                "timestamp": timestamp.isoformat(),
                "price": round(current_price, 2),
                "volume": volume,
                "indicators": {
                    "sma_20": round(sma_20, 2) if sma_20 else None,
                    "sma_50": round(sma_50, 2) if sma_50 else None,
                    "ema_20": round(ema_20, 2) if ema_20 else None,
                    "rsi": round(rsi, 2) if rsi else None,
                    "vwap": round(vwap, 2) if vwap else None,
                    "bollinger_bands": {k: round(v, 2) if v else None for k, v in bollinger.items()}
                }
            }
            
            # Send data via WebSocket
            await websocket.send_text(json.dumps(data))
            
            # Check for patterns and generate AI analysis periodically
            if len(indicators.prices) >= 20 and len(indicators.prices) % 10 == 0:
                await generate_ai_analysis(symbol, indicators, websocket)
            
            # Wait before next data point
            await asyncio.sleep(2)  # 2 seconds between updates
            
        except WebSocketDisconnect:
            break
        except Exception as e:
            logging.error(f"Error in mock data generation for {symbol}: {str(e)}")
            break

async def generate_ai_analysis(symbol: str, indicators: TechnicalIndicators, websocket: WebSocket):
    """Generate AI-powered pattern recognition and analysis"""
    try:
        # Prepare market data context for AI analysis
        recent_prices = list(indicators.prices)[-20:]  # Last 20 data points
        price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100
        
        rsi = indicators.calculate_rsi()
        sma_20 = indicators.calculate_sma(20)
        current_price = recent_prices[-1]
        
        # Create context for AI analysis
        market_context = f"""
Symbol: {symbol}
Current Price: ${current_price:.2f}
20-period Price Change: {price_change:.2f}%
RSI: {rsi:.2f if rsi else 'N/A'}
SMA(20): ${sma_20:.2f if sma_20 else 'N/A'}
Recent Price Trend: {', '.join([f'${p:.2f}' for p in recent_prices[-5:]])}

Please analyze this market data and provide:
1. Pattern identification (if any)
2. Market sentiment assessment
3. Brief trading recommendation
4. Confidence score (0-100)

Format your response as JSON:
{{
  "pattern": "pattern name or null",
  "sentiment": "bullish/bearish/neutral",
  "recommendation": "brief recommendation",
  "confidence": "confidence score",
  "reasoning": "brief explanation"
}}
"""

        # Initialize LLM Chat for pattern analysis
        chat = LlmChat(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            session_id=f"market_analysis_{symbol}_{uuid.uuid4()}",
            system_message="You are an AI financial analyst specialized in technical analysis and pattern recognition. Provide concise, data-driven insights based on market indicators."
        ).with_model("openai", "gpt-4o")

        # Get AI analysis
        user_message = UserMessage(text=market_context)
        response = await chat.send_message(user_message)
        
        # Parse AI response
        try:
            ai_analysis = json.loads(response)
        except json.JSONDecodeError:
            # Fallback analysis
            ai_analysis = {
                "pattern": None,
                "sentiment": "neutral",
                "recommendation": "Hold position, monitor market conditions",
                "confidence": 60,
                "reasoning": "Technical analysis based on current indicators"
            }
        
        # Create analysis data packet
        analysis_data = {
            "type": "ai_analysis",
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analysis": ai_analysis,
            "current_price": current_price
        }
        
        # Send AI analysis via WebSocket
        await websocket.send_text(json.dumps(analysis_data))
        
        # Store analysis in database
        analysis_record = MarketAnalysis(
            symbol=symbol,
            analysis=ai_analysis.get("reasoning", "AI-powered market analysis"),
            pattern_detected=ai_analysis.get("pattern"),
            confidence_score=float(ai_analysis.get("confidence", 60)),
            recommendation=ai_analysis.get("recommendation", "Monitor market conditions")
        )
        
        prepared_data = prepare_for_mongo(analysis_record.dict())
        await db.market_analysis.insert_one(prepared_data)
        
    except Exception as e:
        logging.error(f"Error in AI analysis for {symbol}: {str(e)}")

# Helper functions
def prepare_for_mongo(data):
    """Convert datetime objects to ISO strings for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    """Convert ISO strings back to datetime objects"""
    if isinstance(item, dict):
        for key, value in item.items():
            if key.endswith('_at') or key == 'timestamp' or key == 'created_at':
                if isinstance(value, str):
                    try:
                        item[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except:
                        pass
    return item

# API Routes
@api_router.get("/")
async def root():
    return {"message": "FinTech AI - Real-time Financial Data Platform", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_symbols": list(active_symbols.keys()),
        "active_connections": len(websocket_connections)
    }

@api_router.get("/symbols")
async def get_available_symbols():
    """Get list of available symbols for tracking"""
    symbols = [
        {"symbol": "AAPL", "name": "Apple Inc.", "price": "180.00"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "price": "2800.00"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "price": "250.00"},
        {"symbol": "MSFT", "name": "Microsoft Corp.", "price": "420.00"},
        {"symbol": "NVDA", "name": "NVIDIA Corp.", "price": "800.00"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "price": "3200.00"},
        {"symbol": "META", "name": "Meta Platforms Inc.", "price": "330.00"},
        {"symbol": "NFLX", "name": "Netflix Inc.", "price": "450.00"}
    ]
    return {"symbols": symbols}

@api_router.get("/indicators/{symbol}")
async def get_current_indicators(symbol: str):
    """Get current technical indicators for a symbol"""
    if symbol not in active_symbols:
        raise HTTPException(status_code=404, detail="Symbol not found or not being tracked")
    
    indicators = active_symbols[symbol]
    
    if len(indicators.prices) == 0:
        raise HTTPException(status_code=404, detail="No data available for symbol")
    
    current_price = list(indicators.prices)[-1]
    current_volume = list(indicators.volumes)[-1]
    timestamp = list(indicators.timestamps)[-1]
    
    return {
        "symbol": symbol,
        "timestamp": timestamp.isoformat(),
        "price": current_price,
        "volume": current_volume,
        "indicators": {
            "sma_20": indicators.calculate_sma(20),
            "sma_50": indicators.calculate_sma(50),
            "ema_20": indicators.calculate_ema(20),
            "rsi": indicators.calculate_rsi(14),
            "vwap": indicators.calculate_vwap(),
            "bollinger_bands": indicators.calculate_bollinger_bands()
        }
    }

@api_router.get("/analysis/{symbol}")
async def get_market_analysis(symbol: str, limit: int = 10):
    """Get recent AI analysis for a symbol"""
    try:
        analyses = await db.market_analysis.find(
            {"symbol": symbol}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        parsed_analyses = [parse_from_mongo(analysis) for analysis in analyses]
        return {"symbol": symbol, "analyses": parsed_analyses}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analysis: {str(e)}")

@api_router.post("/alerts")
async def create_price_alert(alert: PriceAlert):
    """Create a price alert for a symbol"""
    try:
        prepared_data = prepare_for_mongo(alert.dict())
        result = await db.price_alerts.insert_one(prepared_data)
        return {"message": "Alert created successfully", "alert_id": str(result.inserted_id)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}")

@api_router.get("/alerts")
async def get_price_alerts():
    """Get all price alerts"""
    try:
        alerts = await db.price_alerts.find().sort("created_at", -1).to_list(100)
        parsed_alerts = [parse_from_mongo(alert) for alert in alerts]
        return {"alerts": parsed_alerts}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch alerts: {str(e)}")

# WebSocket endpoint for real-time data streaming
@api_router.websocket("/ws/market/{symbol}")
async def websocket_market_data(websocket: WebSocket, symbol: str):
    """WebSocket endpoint for real-time market data streaming"""
    await websocket.accept()
    connection_id = f"{symbol}_{id(websocket)}"
    websocket_connections[connection_id] = websocket
    
    logging.info(f"WebSocket connection established for {symbol}")
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": f"Connected to {symbol} market data stream",
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }))
        
        # Start mock data generation for the symbol
        data_task = asyncio.create_task(generate_mock_market_data(symbol, websocket))
        mock_data_tasks[connection_id] = data_task
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (can be used for commands)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logging.error(f"WebSocket message error: {str(e)}")
                continue
                
    except Exception as e:
        logging.error(f"WebSocket error for {symbol}: {str(e)}")
    
    finally:
        # Clean up connection
        if connection_id in websocket_connections:
            del websocket_connections[connection_id]
        
        if connection_id in mock_data_tasks:
            mock_data_tasks[connection_id].cancel()
            del mock_data_tasks[connection_id]
        
        logging.info(f"WebSocket connection closed for {symbol}")

# Include the router in the main app
app.include_router(api_router)

# Add CORS middleware
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

@app.on_event("startup")
async def startup_event():
    logger.info("FinTech AI Platform starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    # Clean up connections and tasks
    for task in mock_data_tasks.values():
        task.cancel()
    
    for ws in websocket_connections.values():
        await ws.close()
    
    client.close()
    logger.info("FinTech AI Platform shutting down...")