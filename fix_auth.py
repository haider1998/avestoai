#!/usr/bin/env python3
"""
Authentication Fix Script for AvestoAI
This script helps diagnose and fix Google Cloud authentication issues
"""

import os
import json
import subprocess
import sys
from pathlib import Path

def check_gcloud_auth():
    """Check gcloud authentication status"""
    print("🔍 Checking gcloud authentication...")

    try:
        result = subprocess.run(['gcloud', 'auth', 'list'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Gcloud auth accounts found:")
            print(result.stdout)
            return True
        else:
            print("❌ Gcloud auth check failed:")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("❌ gcloud CLI not found. Please install Google Cloud SDK.")
        return False

def check_application_default_credentials():
    """Check application default credentials"""
    print("\n🔍 Checking application default credentials...")

    # Common locations for application default credentials
    possible_paths = [
        os.path.expanduser("~/.config/gcloud/application_default_credentials.json"),
        os.path.expanduser("~/AppData/Roaming/gcloud/application_default_credentials.json"),
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    ]

    for path in possible_paths:
        if path and os.path.exists(path):
            print(f"✅ Found credentials at: {path}")
            try:
                with open(path, 'r') as f:
                    creds = json.load(f)
                    if creds.get('type') == 'service_account':
                        print("   Type: Service Account")
                        print(f"   Client Email: {creds.get('client_email', 'N/A')}")
                    elif creds.get('type') == 'authorized_user':
                        print("   Type: User Account (from gcloud auth application-default login)")
                        print(f"   Client ID: {creds.get('client_id', 'N/A')}")
                    else:
                        print(f"   Type: {creds.get('type', 'Unknown')}")
                return path
            except Exception as e:
                print(f"❌ Error reading credentials file: {e}")

    print("❌ No application default credentials found")
    return None

def check_service_account_file():
    """Check for service account key file"""
    print("\n🔍 Checking service account key file...")

    service_account_path = "deployment/service-account-key.json"
    if os.path.exists(service_account_path):
        print(f"✅ Service account file found: {service_account_path}")
        try:
            with open(service_account_path, 'r') as f:
                creds = json.load(f)
                print(f"   Project ID: {creds.get('project_id', 'N/A')}")
                print(f"   Client Email: {creds.get('client_email', 'N/A')}")
                return service_account_path
        except Exception as e:
            print(f"❌ Error reading service account file: {e}")
    else:
        print(f"❌ Service account file not found: {service_account_path}")

    return None

def check_project_access():
    """Check if we have access to the Google Cloud project"""
    print("\n🔍 Checking project access...")

    project_id = "avestoai-466417"

    try:
        result = subprocess.run(['gcloud', 'projects', 'describe', project_id],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Can access project: {project_id}")
            return True
        else:
            print(f"❌ Cannot access project {project_id}:")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("❌ gcloud CLI not found")
        return False

def check_iam_permissions():
    """Check required IAM permissions"""
    print("\n🔍 Checking IAM permissions...")

    project_id = "avestoai-466417"
    required_permissions = [
        "firestore.documents.create",
        "firestore.documents.get",
        "firestore.documents.list",
        "firestore.documents.update",
        "aiplatform.predictions.predict"
    ]

    try:
        for permission in required_permissions:
            result = subprocess.run([
                'gcloud', 'projects', 'test-iam-policy', project_id,
                '--permissions', permission
            ], capture_output=True, text=True)

            if "TRUE" in result.stdout:
                print(f"   ✅ {permission}")
            else:
                print(f"   ❌ {permission}")
    except Exception as e:
        print(f"❌ Error checking permissions: {e}")

def fix_authentication():
    """Provide authentication fix recommendations"""
    print("\n🔧 Authentication Fix Recommendations:")
    print("=" * 50)

    # Check if we have application default credentials
    adc_path = check_application_default_credentials()
    service_account_path = check_service_account_file()

    if not adc_path and not service_account_path:
        print("\n❌ CRITICAL: No credentials found!")
        print("\nOption 1 - Use Application Default Credentials (Recommended for development):")
        print("   Run: gcloud auth application-default login")
        print("   This will authenticate using your Google account")

        print("\nOption 2 - Use Service Account (For production):")
        print("   1. Download service account key from Google Cloud Console")
        print("   2. Save it as 'deployment/service-account-key.json'")
        print("   3. Set environment variable: GOOGLE_APPLICATION_CREDENTIALS=deployment/service-account-key.json")

    elif adc_path and not service_account_path:
        print("\n✅ Using Application Default Credentials")
        print("   This is the recommended approach for local development")
        print("   If you're still getting errors, try:")
        print("   1. gcloud config set project avestoai-466417")
        print("   2. gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform")

    elif service_account_path and not adc_path:
        print("\n✅ Using Service Account")
        print(f"   Make sure to set: GOOGLE_APPLICATION_CREDENTIALS={service_account_path}")

    else:
        print("\n⚠️  Both credentials found - Application Default will be used unless GOOGLE_APPLICATION_CREDENTIALS is set")

def main():
    """Main function"""
    print("🔮 AvestoAI Authentication Diagnostic Tool")
    print("=" * 50)

    # Run all checks
    check_gcloud_auth()
    check_application_default_credentials()
    check_service_account_file()
    check_project_access()
    check_iam_permissions()

    # Provide fix recommendations
    fix_authentication()

    print("\n" + "=" * 50)
    print("🚀 After fixing authentication, restart your application")

if __name__ == "__main__":
    main()
