#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Rate Limiter System
Tests all 4 rate limiting algorithms and API endpoints
"""

import requests
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Optional

class RateLimiterAPITester:
    def __init__(self, base_url="https://dev-hiring-portal.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_api_keys = []
        self.created_configs = []
        
    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def make_request(self, method: str, endpoint: str, data: dict = None, params: dict = None) -> tuple[bool, dict, int]:
        """Make HTTP request and return success, response data, status code"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return False, {}, 0
                
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
                
            return response.status_code < 400, response_data, response.status_code
            
        except Exception as e:
            return False, {"error": str(e)}, 0

    def test_api_root(self) -> bool:
        """Test API root endpoint"""
        success, data, status = self.make_request('GET', '')
        return self.log_test(
            "API Root Endpoint", 
            success and status == 200 and "Rate Limiter System API" in str(data),
            f"Status: {status}, Response: {data}"
        )

    def test_create_api_key(self, name: str) -> Optional[str]:
        """Test API key creation and return the API key"""
        success, data, status = self.make_request('POST', 'api-keys', {'name': name})
        
        if success and status == 200 and 'api_key' in data:
            api_key = data['api_key']
            self.created_api_keys.append(api_key)
            self.log_test(f"Create API Key '{name}'", True, f"Key: {api_key[:20]}...")
            return api_key
        else:
            self.log_test(f"Create API Key '{name}'", False, f"Status: {status}, Response: {data}")
            return None

    def test_get_api_keys(self) -> bool:
        """Test getting all API keys"""
        success, data, status = self.make_request('GET', 'api-keys')
        
        if success and status == 200 and isinstance(data, list):
            return self.log_test("Get API Keys", True, f"Found {len(data)} keys")
        else:
            return self.log_test("Get API Keys", False, f"Status: {status}, Response: {data}")

    def test_create_rate_limit_config(self, api_key: str, algorithm: str, max_requests: int, window_seconds: int) -> bool:
        """Test rate limit configuration creation"""
        config_data = {
            'api_key': api_key,
            'algorithm': algorithm,
            'max_requests': max_requests,
            'window_seconds': window_seconds
        }
        
        success, data, status = self.make_request('POST', 'rate-limit-configs', config_data)
        
        if success and status == 200:
            self.created_configs.append(data.get('id'))
            return self.log_test(
                f"Create Rate Limit Config ({algorithm})", 
                True, 
                f"{max_requests} req/{window_seconds}s"
            )
        else:
            return self.log_test(
                f"Create Rate Limit Config ({algorithm})", 
                False, 
                f"Status: {status}, Response: {data}"
            )

    def test_get_rate_limit_configs(self) -> bool:
        """Test getting all rate limit configurations"""
        success, data, status = self.make_request('GET', 'rate-limit-configs')
        
        if success and status == 200 and isinstance(data, list):
            return self.log_test("Get Rate Limit Configs", True, f"Found {len(data)} configs")
        else:
            return self.log_test("Get Rate Limit Configs", False, f"Status: {status}, Response: {data}")

    def test_protected_endpoint_rate_limiting(self, api_key: str, algorithm: str, max_requests: int) -> Dict[str, int]:
        """Test rate limiting on protected endpoint"""
        allowed_count = 0
        blocked_count = 0
        
        print(f"\n🔄 Testing {algorithm} rate limiting with {max_requests} max requests...")
        
        # Make requests up to the limit + extra to test blocking
        test_requests = max_requests + 5
        
        for i in range(test_requests):
            success, data, status = self.make_request('GET', 'protected/test', params={'api_key': api_key})
            
            if status == 200:
                allowed_count += 1
                print(f"  Request {i+1}: ✅ Allowed (remaining: {data.get('remaining_quota', 'N/A')})")
            elif status == 429:
                blocked_count += 1
                print(f"  Request {i+1}: 🚫 Blocked (rate limit exceeded)")
            else:
                print(f"  Request {i+1}: ❓ Unexpected status {status}: {data}")
            
            # Small delay between requests for some algorithms
            time.sleep(0.1)
        
        # Verify rate limiting worked correctly
        expected_allowed = min(max_requests, test_requests)
        expected_blocked = max(0, test_requests - max_requests)
        
        success = (allowed_count >= expected_allowed - 2 and  # Allow some tolerance
                  blocked_count >= expected_blocked - 2)
        
        self.log_test(
            f"Rate Limiting Test ({algorithm})",
            success,
            f"Allowed: {allowed_count}/{expected_allowed}, Blocked: {blocked_count}/{expected_blocked}"
        )
        
        return {"allowed": allowed_count, "blocked": blocked_count}

    def test_analytics_summary(self) -> bool:
        """Test analytics summary endpoint"""
        success, data, status = self.make_request('GET', 'analytics/summary')
        
        if success and status == 200:
            required_fields = ['total_requests', 'allowed_requests', 'blocked_requests', 'success_rate', 'algorithm_stats']
            has_all_fields = all(field in data for field in required_fields)
            return self.log_test("Analytics Summary", has_all_fields, f"Data: {data}")
        else:
            return self.log_test("Analytics Summary", False, f"Status: {status}, Response: {data}")

    def test_recent_logs(self) -> bool:
        """Test recent logs endpoint"""
        success, data, status = self.make_request('GET', 'analytics/recent-logs', params={'limit': 10})
        
        if success and status == 200 and isinstance(data, list):
            return self.log_test("Recent Logs", True, f"Found {len(data)} log entries")
        else:
            return self.log_test("Recent Logs", False, f"Status: {status}, Response: {data}")

    def test_system_status(self) -> bool:
        """Test system status endpoint"""
        success, data, status = self.make_request('GET', 'system-status')
        
        if success and status == 200:
            required_fields = ['status', 'active_api_keys', 'active_configs', 'total_requests_logged']
            has_all_fields = all(field in data for field in required_fields)
            return self.log_test("System Status", has_all_fields, f"Status: {data.get('status')}")
        else:
            return self.log_test("System Status", False, f"Status: {status}, Response: {data}")

    def test_load_test_endpoint(self, api_key: str) -> bool:
        """Test load test functionality"""
        load_test_data = {
            'api_key': api_key,
            'requests_per_second': 5,
            'duration_seconds': 3,
            'endpoint': '/api/protected/test'
        }
        
        print(f"\n🔄 Running load test: {load_test_data['requests_per_second']} RPS for {load_test_data['duration_seconds']}s...")
        
        success, data, status = self.make_request('POST', 'load-test', load_test_data)
        
        if success and status == 200:
            required_fields = ['total_requests', 'allowed', 'blocked', 'success_rate']
            has_all_fields = all(field in data for field in required_fields)
            return self.log_test(
                "Load Test", 
                has_all_fields, 
                f"Total: {data.get('total_requests')}, Success Rate: {data.get('success_rate')}%"
            )
        else:
            return self.log_test("Load Test", False, f"Status: {status}, Response: {data}")

    def test_reset_stats(self) -> bool:
        """Test reset statistics endpoint"""
        success, data, status = self.make_request('DELETE', 'reset-stats')
        
        if success and status == 200:
            return self.log_test("Reset Stats", True, "Statistics reset successfully")
        else:
            return self.log_test("Reset Stats", False, f"Status: {status}, Response: {data}")

    def run_comprehensive_tests(self) -> Dict[str, any]:
        """Run all tests and return results"""
        print("🚀 Starting Comprehensive Rate Limiter API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        results = {
            "backend_issues": {"critical_bugs": [], "flaky_endpoints": []},
            "passed_tests": [],
            "failed_tests": []
        }
        
        # Test 1: Basic API connectivity
        if self.test_api_root():
            results["passed_tests"].append("API root endpoint connectivity")
        else:
            results["backend_issues"]["critical_bugs"].append({
                "endpoint": "/api/",
                "issue": "API root endpoint not responding",
                "impact": "Complete API failure",
                "fix_priority": "CRITICAL"
            })
            return results
        
        # Test 2: API Key Management
        test_key_name = f"test_key_{int(time.time())}"
        api_key = self.test_create_api_key(test_key_name)
        
        if api_key:
            results["passed_tests"].append("API key creation")
        else:
            results["backend_issues"]["critical_bugs"].append({
                "endpoint": "/api/api-keys",
                "issue": "Cannot create API keys",
                "impact": "Blocks all rate limiting functionality",
                "fix_priority": "CRITICAL"
            })
            return results
        
        if self.test_get_api_keys():
            results["passed_tests"].append("API key retrieval")
        
        # Test 3: Rate Limit Configuration
        algorithms = [
            ("token_bucket", 10, 60),
            ("leaky_bucket", 8, 60),
            ("fixed_window", 12, 60),
            ("sliding_window", 15, 60)
        ]
        
        config_success = 0
        for algorithm, max_req, window in algorithms:
            if self.test_create_rate_limit_config(api_key, algorithm, max_req, window):
                config_success += 1
                results["passed_tests"].append(f"Rate limit config creation ({algorithm})")
        
        if config_success == 0:
            results["backend_issues"]["critical_bugs"].append({
                "endpoint": "/api/rate-limit-configs",
                "issue": "Cannot create rate limit configurations",
                "impact": "Rate limiting not functional",
                "fix_priority": "CRITICAL"
            })
        
        if self.test_get_rate_limit_configs():
            results["passed_tests"].append("Rate limit config retrieval")
        
        # Test 4: Rate Limiting Algorithms
        print("\n" + "=" * 60)
        print("🧪 TESTING RATE LIMITING ALGORITHMS")
        print("=" * 60)
        
        algorithm_results = {}
        for algorithm, max_req, window in algorithms:
            # Create fresh API key for each algorithm test
            test_api_key = self.test_create_api_key(f"test_{algorithm}_{int(time.time())}")
            if test_api_key:
                self.test_create_rate_limit_config(test_api_key, algorithm, max_req, window)
                time.sleep(1)  # Allow config to take effect
                
                rate_limit_result = self.test_protected_endpoint_rate_limiting(test_api_key, algorithm, max_req)
                algorithm_results[algorithm] = rate_limit_result
                
                if rate_limit_result["blocked"] > 0:
                    results["passed_tests"].append(f"Rate limiting enforcement ({algorithm})")
                else:
                    results["backend_issues"]["critical_bugs"].append({
                        "endpoint": "/api/protected/test",
                        "issue": f"{algorithm} algorithm not blocking excess requests",
                        "impact": "Rate limiting not working",
                        "fix_priority": "HIGH"
                    })
        
        # Test 5: Analytics and Monitoring
        if self.test_analytics_summary():
            results["passed_tests"].append("Analytics summary")
        
        if self.test_recent_logs():
            results["passed_tests"].append("Recent logs retrieval")
        
        if self.test_system_status():
            results["passed_tests"].append("System status check")
        
        # Test 6: Load Testing
        if api_key and self.test_load_test_endpoint(api_key):
            results["passed_tests"].append("Load test functionality")
        
        # Test 7: Statistics Reset
        if self.test_reset_stats():
            results["passed_tests"].append("Statistics reset")
        
        # Print Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Tests Passed: {self.tests_passed}/{self.tests_run}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}/{self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if algorithm_results:
            print("\n🔬 Rate Limiting Algorithm Results:")
            for algo, result in algorithm_results.items():
                print(f"  {algo}: {result['allowed']} allowed, {result['blocked']} blocked")
        
        results["success_rate"] = f"{(self.tests_passed/self.tests_run*100):.1f}%"
        results["total_tests"] = self.tests_run
        results["passed_count"] = self.tests_passed
        
        return results

def main():
    """Main test execution"""
    tester = RateLimiterAPITester()
    results = tester.run_comprehensive_tests()
    
    # Return appropriate exit code
    if len(results["backend_issues"]["critical_bugs"]) > 0:
        print("\n🚨 CRITICAL ISSUES FOUND - Backend needs fixes before frontend testing")
        return 1
    elif tester.tests_passed == tester.tests_run:
        print("\n🎉 ALL TESTS PASSED - Backend is ready for frontend integration testing")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - Check issues above")
        return 1

if __name__ == "__main__":
    sys.exit(main())