"""
Setup script to help configure the Groq API key
"""
import os
from pathlib import Path

def setup_groq_api_key():
    print("🎤 VoiceAgent Setup - Groq API Key Configuration")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env file not found!")
        return
    
    # Read current .env content
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Check current API key
    if "GROQ_API_KEY=your-groq-api-key-here" in content:
        print("⚠️  Placeholder API key detected")
        print("\nTo get your Groq API key:")
        print("1. Go to https://console.groq.com")
        print("2. Sign up for a free account")
        print("3. Create an API key")
        print("4. Copy the API key")
        
        api_key = input("\nEnter your Groq API key: ").strip()
        
        if api_key and api_key.startswith("gsk_"):
            # Update .env file
            new_content = content.replace(
                "GROQ_API_KEY=your-groq-api-key-here",
                f"GROQ_API_KEY={api_key}"
            )
            
            with open(env_file, 'w') as f:
                f.write(new_content)
            
            print("✅ API key configured successfully!")
            print("🚀 You can now run: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        else:
            print("❌ Invalid API key format. Groq API keys start with 'gsk_'")
    else:
        print("✅ API key appears to be already configured")

if __name__ == "__main__":
    setup_groq_api_key()