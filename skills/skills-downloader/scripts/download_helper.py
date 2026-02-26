#!/usr/bin/env python3
import subprocess
import os
import sys

def download_skill(skill_query):
    print(f"🔍 Searching for: {skill_query}")
    
    # 1. Search
    search_cmd = ["npx", "-y", "skills", "find", skill_query]
    subprocess.run(search_cmd)
    
    # Selection logic would go here in an interactive script, 
    # but for automation we expect the user to confirm the repo.
    print("\n[!] Please provide the owner/repo@skill identifier to continue installation.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        download_skill(sys.argv[1])
    else:
        print("Usage: python download_helper.py <query>")
