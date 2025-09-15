import subprocess
import os

def run_script(script_name):
    print(f"\n🚀 Running: {script_name}")
    result = subprocess.run(["python", script_name])
    if result.returncode != 0:
        print(f"❌ Script {script_name} failed.")
        exit(result.returncode)
    print(f"✅ Completed: {script_name}")

if __name__ == "__main__":
    # Step 1: Download APKs
    run_script(r"C:\Users\sranjan\Desktop\APK_final\download_apk.py")

    # Step 2: Ask user to connect phone
    input("\n📱 Please connect the phone via USB and press Enter to continue...")

    # Step 3: Run automation on device
    run_script(r"C:\Users\sranjan\Desktop\APK_final\f5.py")

    # Step 4: Send Slack message
    #run_script(r"C:\Users\sranjan\Desktop\APK_final\slack_msg.py")

    print("\n🎉 All tasks completed successfully.")
