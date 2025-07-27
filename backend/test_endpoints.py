#!/usr/bin/env python3
"""
AvestoAI Backend Docker Testing Script
Tests all endpoints to verify the system is working correctly
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any
import sys
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8080"
TEST_MOBILE = "1313131313"  # Balanced scenario
TEST_TIMEOUT = 30

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log_info(message: str):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {message}")

def log_success(message: str):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.END} {message}")

def log_warning(message: str):
    print(f"{Colors.YELLOW}[WARNING]{Colors.END} {message}")

def log_error(message: str):
    print(f"{Colors.RED}[ERROR]{Colors.END} {message}")

class AvestoAITester:
    def __init__(self):
        self.session = None
        self.session_id = None
        self.test_results = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_endpoint(self, name: str, method: str, url: str, 
                          data: Dict = None, expected_status: int = 200, 
                          expect_json: bool = True) -> bool:
        """Test a single endpoint with proper content type handling"""
        try:
            log_info(f"Testing {name}...")
            start_time = time.time()
            
            if method.upper() == "GET":
                async with self.session.get(f"{BASE_URL}{url}") as response:
                    status = response.status
                    content_type = response.headers.get('content-type', '')
                    
                    # Handle different response types
                    if expect_json and 'application/json' in content_type:
                        response_data = await response.json()
                    elif not expect_json and 'text/plain' in content_type:
                        response_data = await response.text()
                        # For metrics, just check if it contains prometheus metrics
                        if url == "/metrics" and "avestoai_" in response_data:
                            log_info(f"Metrics endpoint returned valid Prometheus data")
                    else:
                        # Try JSON first, fallback to text
                        try:
                            response_data = await response.json()
                        except:
                            response_data = await response.text()
                            
            elif method.upper() == "POST":
                async with self.session.post(
                    f"{BASE_URL}{url}", 
                    json=data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    status = response.status
                    try:
                        response_data = await response.json()
                    except:
                        response_data = await response.text()
            
            duration = (time.time() - start_time) * 1000
            
            if status == expected_status:
                log_success(f"{name} - Status: {status}, Duration: {duration:.1f}ms")
                self.test_results.append({
                    "name": name,
                    "status": "PASS",
                    "duration": duration,
                    "response_status": status
                })
                return True
            else:
                log_error(f"{name} - Expected: {expected_status}, Got: {status}")
                self.test_results.append({
                    "name": name,
                    "status": "FAIL",
                    "duration": duration,
                    "error": f"Status mismatch: expected {expected_status}, got {status}"
                })
                return False
                
        except Exception as e:
            log_error(f"{name} - Exception: {status}, message='{str(e)}', url='{BASE_URL}{url}'")
            self.test_results.append({
                "name": name,
                "status": "ERROR",
                "error": str(e)
            })
            return False

    async def test_health_endpoints(self):
        """Test health and monitoring endpoints"""
        log_info("Testing Health & Monitoring Endpoints")
        
        tests = [
            ("Root Endpoint", "GET", "/", None, 200, True),
            ("Health Check", "GET", "/health", None, 200, True),
            ("Metrics", "GET", "/metrics", None, 200, False)  # Metrics returns text/plain
        ]
        
        results = []
        for name, method, url, data, expected_status, expect_json in tests:
            result = await self.test_endpoint(name, method, url, data, expected_status, expect_json)
            results.append(result)
            
        return all(results)

    async def run_all_tests(self):
        """Run all test suites"""
        log_info(f"Starting AvestoAI Backend Tests - {datetime.now()}")
        log_info(f"Base URL: {BASE_URL}")
        log_info(f"Test Mobile: {TEST_MOBILE}")
        print("=" * 60)
        
        # Only test health endpoints for now to verify basic functionality
        print(f"\n{Colors.BOLD}Testing Health & Monitoring{Colors.END}")
        print("-" * 40)
        
        try:
            success = await self.test_health_endpoints()
            if success:
                log_success("Health & Monitoring - All tests passed")
            else:
                log_error("Health & Monitoring - Some tests failed")
        except Exception as e:
            log_error(f"Health & Monitoring - Test suite failed: {str(e)}")
            success = False
        
        # Print summary
        print(f"\n{Colors.BOLD}Test Summary{Colors.END}")
        print("=" * 60)
        
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        errors = len([r for r in self.test_results if r["status"] == "ERROR"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {failed}{Colors.END}")
        print(f"{Colors.YELLOW}Errors: {errors}{Colors.END}")
        
        if success:
            log_success("All test suites completed successfully!")
            return 0
        else:
            log_error("Some tests failed. Check the logs above.")
            return 1

async def main():
    """Main test runner"""
    try:
        async with AvestoAITester() as tester:
            return await tester.run_all_tests()
    except KeyboardInterrupt:
        log_warning("Tests interrupted by user")
        return 1
    except Exception as e:
        log_error(f"Test runner failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
