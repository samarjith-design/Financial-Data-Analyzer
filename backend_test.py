import requests
import sys
import json
import time
from datetime import datetime

class MeetingSummarizerAPITester:
    def __init__(self, base_url="https://meetsum-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_meeting_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'} if not files else {}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, data=data, files=files, timeout=60)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=60)

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
        return success

    def test_text_summarization(self):
        """Test text summarization endpoint"""
        sample_meeting_content = """
Team Meeting - January 15, 2024

Attendees: Sarah (PM), Mike (Dev), Lisa (Designer), Tom (QA)

Agenda:
- Q1 Planning review
- New feature priorities  
- Bug fix timeline

Discussion:
Sarah opened by reviewing Q1 goals. Mike presented the new user dashboard feature - estimated 3 weeks development. Lisa needs to finalize mockups by Friday. Tom identified 5 critical bugs that need fixing before release.

Action Items:
- Sarah: Schedule client demo for next Thursday
- Mike: Start dashboard feature development Monday
- Lisa: Complete mockups by end of week
- Tom: Fix critical bugs by next Tuesday

Next meeting: January 22, 2024
"""
        
        success, response = self.run_test(
            "Text Summarization",
            "POST",
            "summarize-text",
            200,
            data={
                "title": "Test Team Meeting - Backend API Test",
                "content": sample_meeting_content
            }
        )
        
        if success and response:
            # Store the meeting ID for later tests
            self.created_meeting_id = response.get('id')
            print(f"   Created meeting ID: {self.created_meeting_id}")
            
            # Validate response structure
            required_fields = ['id', 'title', 'summary', 'action_items', 'key_points', 'created_at']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"   ⚠️  Missing fields in response: {missing_fields}")
            else:
                print(f"   ✅ All required fields present")
                print(f"   Summary length: {len(response.get('summary', ''))}")
                print(f"   Action items count: {len(response.get('action_items', []))}")
                print(f"   Key points count: {len(response.get('key_points', []))}")
        
        return success

    def test_file_upload_summarization(self):
        """Test file upload summarization endpoint"""
        # Create a test file content
        test_content = """Project Kickoff Meeting - February 1, 2024

Attendees: John (Lead), Alice (Dev), Bob (Designer)

Discussion:
- Project timeline: 8 weeks
- Budget approved: $50k
- Technology stack: React + Node.js
- First milestone: February 15

Action Items:
- John: Set up project repository
- Alice: Create initial project structure
- Bob: Design wireframes

Next Steps:
- Weekly standup meetings every Monday
- Code review process to be established
"""
        
        # Create a temporary file-like object
        files = {
            'file': ('test_meeting.txt', test_content, 'text/plain')
        }
        
        data = {
            'title': 'Test File Upload Meeting - Backend API Test'
        }
        
        success, response = self.run_test(
            "File Upload Summarization",
            "POST",
            "summarize-file",
            200,
            data=data,
            files=files
        )
        
        if success and response:
            print(f"   File processing successful")
            print(f"   Summary length: {len(response.get('summary', ''))}")
            print(f"   Action items count: {len(response.get('action_items', []))}")
        
        return success

    def test_get_all_meetings(self):
        """Test getting all meetings"""
        success, response = self.run_test(
            "Get All Meetings",
            "GET",
            "meetings",
            200
        )
        
        if success and response:
            if isinstance(response, list):
                print(f"   Found {len(response)} meetings")
                if len(response) > 0:
                    print(f"   First meeting title: {response[0].get('title', 'N/A')}")
            else:
                print(f"   ⚠️  Expected list, got {type(response)}")
        
        return success

    def test_get_specific_meeting(self):
        """Test getting a specific meeting by ID"""
        if not self.created_meeting_id:
            print("   ⚠️  Skipping - No meeting ID available from previous tests")
            return True
        
        success, response = self.run_test(
            "Get Specific Meeting",
            "GET",
            f"meetings/{self.created_meeting_id}",
            200
        )
        
        if success and response:
            print(f"   Retrieved meeting: {response.get('title', 'N/A')}")
        
        return success

    def test_invalid_endpoints(self):
        """Test error handling for invalid requests"""
        print(f"\n🔍 Testing Error Handling...")
        
        # Test empty text summarization
        success, _ = self.run_test(
            "Empty Text Summarization",
            "POST",
            "summarize-text",
            422,  # Validation error expected
            data={"title": "", "content": ""}
        )
        
        # Test non-existent meeting
        success2, _ = self.run_test(
            "Non-existent Meeting",
            "GET",
            "meetings/non-existent-id",
            404
        )
        
        return success and success2

def main():
    print("🚀 Starting AI Meeting Summarizer API Tests")
    print("=" * 50)
    
    # Setup
    tester = MeetingSummarizerAPITester()
    
    # Run all tests
    print(f"\n📡 Testing API at: {tester.api_url}")
    
    # Basic connectivity
    if not tester.test_root_endpoint():
        print("❌ Root endpoint failed, stopping tests")
        return 1
    
    # Core functionality tests
    tester.test_text_summarization()
    time.sleep(2)  # Give AI processing time
    
    tester.test_file_upload_summarization()
    time.sleep(2)  # Give AI processing time
    
    tester.test_get_all_meetings()
    tester.test_get_specific_meeting()
    
    # Error handling tests
    tester.test_invalid_endpoints()
    
    # Print results
    print(f"\n📊 Test Results:")
    print(f"   Tests run: {tester.tests_run}")
    print(f"   Tests passed: {tester.tests_passed}")
    print(f"   Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed - check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())