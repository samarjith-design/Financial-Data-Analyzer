import React, { useState, useEffect, useRef, useCallback } from "react";
import "./App.css";
import axios from "axios";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { Progress } from "./components/ui/progress";
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  BarChart3, 
  Brain, 
  Bell, 
  Wifi, 
  WifiOff,
  DollarSign,
  Target,
  LineChart,
  Zap,
  AlertTriangle
} from "lucide-react";
import { toast } from "sonner";
import { Toaster } from "./components/ui/sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace(/^https?:\/\//, 'wss://');

function App() {
  // State management
  const [selectedSymbol, setSelectedSymbol] = useState("AAPL");
  const [symbols, setSymbols] = useState([]);
  const [currentData, setCurrentData] = useState(null);
  const [indicators, setIndicators] = useState({});
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [priceHistory, setPriceHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [alertPrice, setAlertPrice] = useState("");
  const [alertType, setAlertType] = useState("above");
  const [recentAnalyses, setRecentAnalyses] = useState([]);
  
  // WebSocket reference
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Fetch available symbols on component mount
  useEffect(() => {
    fetchSymbols();
    fetchAlerts();
    fetchRecentAnalyses();
  }, []);

  // Connect to WebSocket when symbol changes
  useEffect(() => {
    if (selectedSymbol) {
      connectWebSocket(selectedSymbol);
    }
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [selectedSymbol]);

  const fetchSymbols = async () => {
    try {
      const response = await axios.get(`${API}/symbols`);
      setSymbols(response.data.symbols);
    } catch (error) {
      console.error("Error fetching symbols:", error);
      toast.error("Failed to fetch symbols");
    }
  };

  const fetchAlerts = async () => {
    try {
      const response = await axios.get(`${API}/alerts`);
      setAlerts(response.data.alerts || []);
    } catch (error) {
      console.error("Error fetching alerts:", error);
    }
  };

  const fetchRecentAnalyses = async () => {
    try {
      const response = await axios.get(`${API}/analysis/${selectedSymbol}`);
      setRecentAnalyses(response.data.analyses || []);
    } catch (error) {
      console.error("Error fetching analyses:", error);
    }
  };

  const connectWebSocket = useCallback((symbol) => {
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = `${WS_URL}/api/ws/market/${symbol}`;
    console.log("Connecting to WebSocket:", wsUrl);
    
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`WebSocket connected for ${symbol}`);
        setIsConnected(true);
        toast.success(`Connected to ${symbol} live data`);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };

      ws.onclose = () => {
        console.log(`WebSocket closed for ${symbol}`);
        setIsConnected(false);
        
        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log("Attempting to reconnect...");
          connectWebSocket(symbol);
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setIsConnected(false);
        toast.error("Connection error occurred");
      };

    } catch (error) {
      console.error("Error creating WebSocket:", error);
      setIsConnected(false);
    }
  }, []);

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case "connection":
        console.log("Connection confirmed:", data.message);
        break;
        
      case "market_data":
        setCurrentData(data);
        setIndicators(data.indicators || {});
        
        // Update price history (keep last 50 points for chart)
        setPriceHistory(prev => {
          const newHistory = [...prev, {
            timestamp: data.timestamp,
            price: data.price,
            volume: data.volume
          }];
          return newHistory.slice(-50); // Keep last 50 points
        });
        break;
        
      case "ai_analysis":
        setAiAnalysis(data);
        toast.success("🧠 New AI Analysis Available!");
        fetchRecentAnalyses(); // Refresh analyses list
        break;
        
      default:
        console.log("Unknown message type:", data.type);
    }
  };

  const createPriceAlert = async () => {
    if (!alertPrice || !currentData) {
      toast.error("Please enter a valid price");
      return;
    }

    try {
      const alertData = {
        id: Date.now().toString(),
        symbol: selectedSymbol,
        condition: alertType,
        target_price: parseFloat(alertPrice),
        current_price: currentData.price,
        triggered: false
      };

      await axios.post(`${API}/alerts`, alertData);
      toast.success("Price alert created successfully!");
      setAlertPrice("");
      fetchAlerts();
    } catch (error) {
      console.error("Error creating alert:", error);
      toast.error("Failed to create alert");
    }
  };

  const getTrendIcon = (current, previous) => {
    if (!previous) return <Activity className="w-4 h-4" />;
    return current > previous ? 
      <TrendingUp className="w-4 h-4 text-green-500" /> : 
      <TrendingDown className="w-4 h-4 text-red-500" />;
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(price);
  };

  const formatNumber = (num) => {
    if (num === null || num === undefined) return 'N/A';
    return parseFloat(num).toFixed(2);
  };

  const getRSIColor = (rsi) => {
    if (!rsi) return 'text-gray-500';
    if (rsi > 70) return 'text-red-500';
    if (rsi < 30) return 'text-green-500';
    return 'text-yellow-500';
  };

  const getIndicatorStatus = (indicator, value) => {
    if (!value) return 'neutral';
    
    switch (indicator) {
      case 'rsi':
        if (value > 70) return 'overbought';
        if (value < 30) return 'oversold';
        return 'neutral';
      default:
        return 'neutral';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  FinTech AI
                </h1>
                <p className="text-sm text-slate-400">Real-time Financial Intelligence</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant={isConnected ? "default" : "destructive"} className="flex items-center space-x-1">
                {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
                <span>{isConnected ? "Live" : "Disconnected"}</span>
              </Badge>
              <Badge variant="outline" className="text-blue-400 border-blue-400">
                <Brain className="w-3 h-3 mr-1" />
                AI Powered
              </Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Symbol Selection */}
        <div className="mb-8">
          <div className="flex items-center space-x-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Select Stock Symbol
              </label>
              <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
                <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                  <SelectValue placeholder="Choose a symbol" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-600">
                  {symbols.map((symbol) => (
                    <SelectItem key={symbol.symbol} value={symbol.symbol} className="text-white hover:bg-slate-700">
                      <div className="flex items-center justify-between w-full">
                        <span className="font-medium">{symbol.symbol}</span>
                        <span className="text-sm text-slate-400 ml-2">{symbol.name}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {/* Real-time Dashboard */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Current Price Card */}
          <Card className="bg-slate-800/50 border-slate-600 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-slate-200 flex items-center justify-between">
                <span>Current Price</span>
                {getTrendIcon(currentData?.price, priceHistory[priceHistory.length - 2]?.price)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-white mb-2">
                {currentData ? formatPrice(currentData.price) : '$0.00'}
              </div>
              <div className="text-sm text-slate-400">
                Volume: {currentData ? currentData.volume.toLocaleString() : '0'}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                {currentData ? new Date(currentData.timestamp).toLocaleTimeString() : 'No data'}
              </div>
            </CardContent>
          </Card>

          {/* RSI Indicator */}
          <Card className="bg-slate-800/50 border-slate-600 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-slate-200 flex items-center space-x-2">
                <Target className="w-5 h-5" />
                <span>RSI (14)</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold mb-2 ${getRSIColor(indicators.rsi)}`}>
                {formatNumber(indicators.rsi)}
              </div>
              <Progress 
                value={indicators.rsi || 0} 
                className="mb-2" 
                style={{
                  backgroundColor: 'rgba(148, 163, 184, 0.2)'
                }}
              />
              <div className="text-sm text-slate-400">
                Status: {getIndicatorStatus('rsi', indicators.rsi)}
              </div>
            </CardContent>
          </Card>

          {/* VWAP */}
          <Card className="bg-slate-800/50 border-slate-600 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-slate-200 flex items-center space-x-2">
                <LineChart className="w-5 h-5" />
                <span>VWAP</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-white mb-2">
                {indicators.vwap ? formatPrice(indicators.vwap) : '$0.00'}
              </div>
              <div className="text-sm text-slate-400">
                Volume Weighted Average Price
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Technical Indicators Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card className="bg-slate-800/30 border-slate-600">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">SMA (20)</p>
                  <p className="text-lg font-semibold text-white">
                    {indicators.sma_20 ? formatPrice(indicators.sma_20) : 'N/A'}
                  </p>
                </div>
                <TrendingUp className="w-5 h-5 text-blue-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/30 border-slate-600">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">EMA (20)</p>
                  <p className="text-lg font-semibold text-white">
                    {indicators.ema_20 ? formatPrice(indicators.ema_20) : 'N/A'}
                  </p>
                </div>
                <Activity className="w-5 h-5 text-green-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/30 border-slate-600">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">BB Upper</p>
                  <p className="text-lg font-semibold text-white">
                    {indicators.bollinger_bands?.upper ? formatPrice(indicators.bollinger_bands.upper) : 'N/A'}
                  </p>
                </div>
                <TrendingUp className="w-5 h-5 text-purple-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/30 border-slate-600">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">BB Lower</p>
                  <p className="text-lg font-semibold text-white">
                    {indicators.bollinger_bands?.lower ? formatPrice(indicators.bollinger_bands.lower) : 'N/A'}
                  </p>
                </div>
                <TrendingDown className="w-5 h-5 text-red-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs for different sections */}
        <Tabs defaultValue="analysis" className="w-full">
          <TabsList className="grid w-full grid-cols-3 bg-slate-800 border-slate-600">
            <TabsTrigger value="analysis" className="text-slate-200 data-[state=active]:bg-blue-600">
              <Brain className="w-4 h-4 mr-2" />
              AI Analysis
            </TabsTrigger>
            <TabsTrigger value="alerts" className="text-slate-200 data-[state=active]:bg-blue-600">
              <Bell className="w-4 h-4 mr-2" />
              Price Alerts
            </TabsTrigger>
            <TabsTrigger value="history" className="text-slate-200 data-[state=active]:bg-blue-600">
              <BarChart3 className="w-4 h-4 mr-2" />
              Analysis History
            </TabsTrigger>
          </TabsList>

          <TabsContent value="analysis" className="mt-6">
            <Card className="bg-slate-800/50 border-slate-600">
              <CardHeader>
                <CardTitle className="text-slate-200 flex items-center space-x-2">
                  <Zap className="w-5 h-5 text-yellow-400" />
                  <span>Latest AI Market Analysis</span>
                </CardTitle>
                <CardDescription className="text-slate-400">
                  Real-time pattern recognition and trading insights
                </CardDescription>
              </CardHeader>
              <CardContent>
                {aiAnalysis ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Badge variant="outline" className="text-blue-400 border-blue-400">
                          {aiAnalysis.symbol}
                        </Badge>
                        <span className="text-sm text-slate-400">
                          {new Date(aiAnalysis.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <Badge variant={
                        aiAnalysis.analysis?.confidence > 80 ? "default" :
                        aiAnalysis.analysis?.confidence > 60 ? "secondary" : "destructive"
                      }>
                        {aiAnalysis.analysis?.confidence}% Confidence
                      </Badge>
                    </div>
                    
                    {aiAnalysis.analysis?.pattern && (
                      <div className="bg-slate-700/50 rounded-lg p-4">
                        <h4 className="text-sm font-medium text-slate-200 mb-2">Pattern Detected</h4>
                        <p className="text-lg font-semibold text-yellow-400">
                          {aiAnalysis.analysis.pattern}
                        </p>
                      </div>
                    )}
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-slate-700/50 rounded-lg p-4">
                        <h4 className="text-sm font-medium text-slate-200 mb-2">Market Sentiment</h4>
                        <p className={`text-lg font-semibold ${
                          aiAnalysis.analysis?.sentiment === 'bullish' ? 'text-green-400' :
                          aiAnalysis.analysis?.sentiment === 'bearish' ? 'text-red-400' : 'text-yellow-400'
                        }`}>
                          {aiAnalysis.analysis?.sentiment || 'Neutral'}
                        </p>
                      </div>
                      
                      <div className="bg-slate-700/50 rounded-lg p-4">
                        <h4 className="text-sm font-medium text-slate-200 mb-2">Current Price</h4>
                        <p className="text-lg font-semibold text-white">
                          {formatPrice(aiAnalysis.current_price)}
                        </p>
                      </div>
                    </div>
                    
                    <div className="bg-slate-700/50 rounded-lg p-4">
                      <h4 className="text-sm font-medium text-slate-200 mb-2">AI Recommendation</h4>
                      <p className="text-slate-300">
                        {aiAnalysis.analysis?.recommendation || 'Monitor market conditions'}
                      </p>
                    </div>
                    
                    <div className="bg-slate-700/50 rounded-lg p-4">
                      <h4 className="text-sm font-medium text-slate-200 mb-2">Analysis Reasoning</h4>
                      <p className="text-slate-300">
                        {aiAnalysis.analysis?.reasoning || 'AI-powered technical analysis based on current market indicators'}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Brain className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-slate-300 mb-2">No AI Analysis Yet</h3>
                    <p className="text-slate-500">
                      AI analysis will appear here once enough market data is collected
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="alerts" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Create Alert */}
              <Card className="bg-slate-800/50 border-slate-600">
                <CardHeader>
                  <CardTitle className="text-slate-200">Create Price Alert</CardTitle>
                  <CardDescription className="text-slate-400">
                    Get notified when {selectedSymbol} reaches your target price
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Alert Type
                    </label>
                    <Select value={alertType} onValueChange={setAlertType}>
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-600">
                        <SelectItem value="above" className="text-white">Price Above</SelectItem>
                        <SelectItem value="below" className="text-white">Price Below</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Target Price ($)
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      value={alertPrice}
                      onChange={(e) => setAlertPrice(e.target.value)}
                      placeholder="Enter target price"
                      className="bg-slate-700 border-slate-600 text-white"
                    />
                  </div>
                  
                  <Button 
                    onClick={createPriceAlert}
                    className="w-full bg-blue-600 hover:bg-blue-700"
                    disabled={!alertPrice || !currentData}
                  >
                    <Bell className="w-4 h-4 mr-2" />
                    Create Alert
                  </Button>
                </CardContent>
              </Card>

              {/* Active Alerts */}
              <Card className="bg-slate-800/50 border-slate-600">
                <CardHeader>
                  <CardTitle className="text-slate-200">Active Alerts</CardTitle>
                  <CardDescription className="text-slate-400">
                    Your current price alerts
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {alerts.length > 0 ? (
                    <div className="space-y-3">
                      {alerts.slice(0, 5).map((alert, index) => (
                        <div key={index} className="bg-slate-700/50 rounded-lg p-3 flex items-center justify-between">
                          <div>
                            <div className="flex items-center space-x-2">
                              <Badge variant="outline" className="text-blue-400 border-blue-400">
                                {alert.symbol}
                              </Badge>
                              <span className="text-sm text-slate-300">
                                {alert.condition} {formatPrice(alert.target_price)}
                              </span>
                            </div>
                            <p className="text-xs text-slate-500 mt-1">
                              Created: {new Date(alert.created_at).toLocaleDateString()}
                            </p>
                          </div>
                          <Badge variant={alert.triggered ? "default" : "secondary"}>
                            {alert.triggered ? "Triggered" : "Active"}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6">
                      <AlertTriangle className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                      <p className="text-slate-400">No active alerts</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="history" className="mt-6">
            <Card className="bg-slate-800/50 border-slate-600">
              <CardHeader>
                <CardTitle className="text-slate-200">Analysis History</CardTitle>
                <CardDescription className="text-slate-400">
                  Recent AI analysis for {selectedSymbol}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {recentAnalyses.length > 0 ? (
                  <div className="space-y-4">
                    {recentAnalyses.map((analysis, index) => (
                      <div key={index} className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-2">
                            <Badge variant="outline" className="text-blue-400 border-blue-400">
                              {analysis.symbol}
                            </Badge>
                            <span className="text-sm text-slate-400">
                              {new Date(analysis.timestamp).toLocaleString()}
                            </span>
                          </div>
                          <Badge variant="secondary">
                            {analysis.confidence_score}% Confidence
                          </Badge>
                        </div>
                        
                        {analysis.pattern_detected && (
                          <div className="mb-2">
                            <span className="text-sm font-medium text-yellow-400">
                              Pattern: {analysis.pattern_detected}
                            </span>
                          </div>
                        )}
                        
                        <p className="text-slate-300 text-sm mb-2">
                          {analysis.recommendation}
                        </p>
                        
                        <p className="text-slate-400 text-xs">
                          {analysis.analysis}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <BarChart3 className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-slate-300 mb-2">No Analysis History</h3>
                    <p className="text-slate-500">
                      Analysis history will appear here as data is processed
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
      
      <Toaster />
    </div>
  );
}

export default App;