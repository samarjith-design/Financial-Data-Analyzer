import requests
import sys
import json
import time
import websocket
import threading
from datetime import datetime

class FinTechAPITester:
    def __init__(self, base_url="https://meetsum-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.ws_url = base_url.replace('https://', 'wss://').replace('http://', 'ws://')
        self.tests_run = 0
        self.tests_passed = 0
        self.ws_messages = []
        self.ws_connected = False

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Non-dict response'}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        
        if success and response:
            expected_fields = ['message', 'version']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
            else:
                print(f"   ✅ Root endpoint working correctly")
                print(f"   Message: {response.get('message')}")
                print(f"   Version: {response.get('version')}")
        
        return success

    def test_health_check(self):
        """Test the health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        
        if success and response:
            expected_fields = ['status', 'timestamp', 'active_symbols', 'active_connections']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
            else:
                print(f"   ✅ Health check working correctly")
                print(f"   Status: {response.get('status')}")
                print(f"   Active symbols: {response.get('active_symbols')}")
                print(f"   Active connections: {response.get('active_connections')}")
        
        return success

    def test_get_symbols(self):
        """Test getting available symbols"""
        success, response = self.run_test(
            "Get Available Symbols",
            "GET",
            "symbols",
            200
        )
        
        if success and response:
            symbols = response.get('symbols', [])
            if symbols:
                print(f"   ✅ Found {len(symbols)} symbols")
                print(f"   First symbol: {symbols[0].get('symbol')} - {symbols[0].get('name')}")
                
                # Validate symbol structure
                required_symbol_fields = ['symbol', 'name', 'price']
                for symbol in symbols[:3]:  # Check first 3 symbols
                    missing = [field for field in required_symbol_fields if field not in symbol]
                    if missing:
                        print(f"   ⚠️  Symbol {symbol.get('symbol')} missing fields: {missing}")
            else:
                print(f"   ⚠️  No symbols returned")
        
        return success

    def test_get_indicators(self):
        """Test getting technical indicators for a symbol"""
        # First try to get indicators for AAPL (might not have data initially)
        success, response = self.run_test(
            "Get Technical Indicators (AAPL)",
            "GET",
            "indicators/AAPL",
            404  # Expected 404 if no data yet
        )
        
        if not success:
            # Try with expected 404 status
            success, response = self.run_test(
                "Get Technical Indicators (AAPL) - Expected 404",
                "GET", 
                "indicators/AAPL",
                404
            )
            if success:
                print(f"   ✅ Correctly returns 404 when no data available")
                return True
        else:
            # If we got 200, validate the response structure
            if response:
                expected_fields = ['symbol', 'timestamp', 'price', 'volume', 'indicators']
                missing_fields = [field for field in expected_fields if field not in response]
                if missing_fields:
                    print(f"   ⚠️  Missing fields: {missing_fields}")
                else:
                    print(f"   ✅ Indicators response structure correct")
                    indicators = response.get('indicators', {})
                    print(f"   Available indicators: {list(indicators.keys())}")
        
        return success

    def test_get_analysis(self):
        """Test getting AI analysis for a symbol"""
        success, response = self.run_test(
            "Get AI Analysis (AAPL)",
            "GET",
            "analysis/AAPL",
            200
        )
        
        if success and response:
            expected_fields = ['symbol', 'analyses']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
            else:
                analyses = response.get('analyses', [])
                print(f"   ✅ Found {len(analyses)} analyses for AAPL")
                if analyses:
                    first_analysis = analyses[0]
                    print(f"   First analysis keys: {list(first_analysis.keys())}")
        
        return success

    def test_create_price_alert(self):
        """Test creating a price alert"""
        alert_data = {
            "id": f"test_alert_{int(time.time())}",
            "symbol": "AAPL",
            "condition": "above",
            "target_price": 200.0,
            "current_price": 180.0,
            "triggered": False
        }
        
        success, response = self.run_test(
            "Create Price Alert",
            "POST",
            "alerts",
            200,
            data=alert_data
        )
        
        if success and response:
            expected_fields = ['message', 'alert_id']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
            else:
                print(f"   ✅ Alert created successfully")
                print(f"   Alert ID: {response.get('alert_id')}")
        
        return success

    def test_get_price_alerts(self):
        """Test getting price alerts"""
        success, response = self.run_test(
            "Get Price Alerts",
            "GET",
            "alerts",
            200
        )
        
        if success and response:
            alerts = response.get('alerts', [])
            print(f"   ✅ Found {len(alerts)} alerts")
            if alerts:
                first_alert = alerts[0]
                print(f"   First alert keys: {list(first_alert.keys())}")
                print(f"   First alert symbol: {first_alert.get('symbol')}")
        
        return success

    def test_websocket_connection(self):
        """Test WebSocket connection for real-time data"""
        print(f"\n🔍 Testing WebSocket Connection...")
        
        ws_url = f"{self.ws_url}/api/ws/market/AAPL"
        print(f"   WebSocket URL: {ws_url}")
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self.ws_messages.append(data)
                print(f"   📨 Received: {data.get('type', 'unknown')} message")
                if data.get('type') == 'market_data':
                    print(f"      Price: ${data.get('price', 0):.2f}")
                    print(f"      Volume: {data.get('volume', 0):,}")
                elif data.get('type') == 'ai_analysis':
                    print(f"      AI Analysis received for {data.get('symbol')}")
            except Exception as e:
                print(f"   ❌ Error parsing message: {e}")

        def on_error(ws, error):
            print(f"   ❌ WebSocket error: {error}")

        def on_close(ws, close_status_code, close_msg):
            print(f"   🔌 WebSocket closed")
            self.ws_connected = False

        def on_open(ws):
            print(f"   ✅ WebSocket connected successfully")
            self.ws_connected = True
            # Send a ping message
            ws.send(json.dumps({"type": "ping"}))

        try:
            ws = websocket.WebSocketApp(ws_url,
                                      on_open=on_open,
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_close=on_close)
            
            # Run WebSocket in a separate thread
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for connection and some messages
            time.sleep(10)  # Wait 10 seconds for messages
            
            ws.close()
            
            if self.ws_connected or len(self.ws_messages) > 0:
                print(f"   ✅ WebSocket test successful")
                print(f"   📊 Received {len(self.ws_messages)} messages")
                
                # Analyze message types
                message_types = {}
                for msg in self.ws_messages:
                    msg_type = msg.get('type', 'unknown')
                    message_types[msg_type] = message_types.get(msg_type, 0) + 1
                
                print(f"   📈 Message types: {message_types}")
                return True
            else:
                print(f"   ❌ WebSocket connection failed")
                return False
                
        except Exception as e:
            print(f"   ❌ WebSocket test failed: {e}")
            return False

    def test_invalid_endpoints(self):
        """Test error handling for invalid requests"""
        print(f"\n🔍 Testing Error Handling...")
        
        # Test invalid symbol
        success1, _ = self.run_test(
            "Invalid Symbol Indicators",
            "GET",
            "indicators/INVALID",
            404
        )
        
        # Test invalid alert data
        success2, _ = self.run_test(
            "Invalid Alert Data",
            "POST",
            "alerts",
            422,  # Validation error expected
            data={"invalid": "data"}
        )
        
        return success1 and success2

def main():
    print("🚀 Starting FinTech AI Platform API Tests")
    print("=" * 60)
    
    # Setup
    tester = FinTechAPITester()
    
    # Run all tests
    print(f"\n📡 Testing API at: {tester.api_url}")
    
    # Basic connectivity tests
    if not tester.test_root_endpoint():
        print("❌ Root endpoint failed, stopping tests")
        return 1
    
    if not tester.test_health_check():
        print("❌ Health check failed, stopping tests")
        return 1
    
    # Core functionality tests
    tester.test_get_symbols()
    tester.test_get_indicators()
    tester.test_get_analysis()
    
    # Alert system tests
    tester.test_create_price_alert()
    time.sleep(1)  # Brief pause
    tester.test_get_price_alerts()
    
    # WebSocket test (most important for real-time features)
    tester.test_websocket_connection()
    
    # Error handling tests
    tester.test_invalid_endpoints()
    
    # Print results
    print(f"\n📊 Test Results:")
    print(f"   Tests run: {tester.tests_run}")
    print(f"   Tests passed: {tester.tests_passed}")
    print(f"   Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed >= tester.tests_run * 0.8:  # 80% pass rate acceptable
        print("🎉 Most tests passed - Backend appears functional!")
        return 0
    else:
        print("⚠️  Many tests failed - Backend needs attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())