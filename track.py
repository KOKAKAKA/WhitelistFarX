import os
import time
import requests

WEBHOOK_URL = 'https://discord.com/api/webhooks/1269259791146946640/yIfvuZUio3jSUqpEd-yAI0urQUtXxhYtO3eKxmnOUuQqY1Fc0MjOYiGjOM-A5lcFhqrd'

def send_webhook(message):
    data = {
        "content": message
    }
    response = requests.post(WEBHOOK_URL, json=data)
    if response.status_code == 204:
        print("Message sent successfully")
    else:
        print(f"Failed to send message: {response.status_code}")

def get_battery_status():
    output = os.popen('adb shell dumpsys battery').read()
    if "status: 2" in output:
        status = "Plugged in"
    else:
        status = "Unplugged"
    # Extract battery percentage
    percentage = next((line for line in output.splitlines() if "level:" in line), "level: 0").split(":")[1].strip()
    return status, percentage

def check_youtube_activity():
    last_activity = None
    last_battery_status = None
    while True:
        # Check YouTube activity
        output = os.popen('adb shell dumpsys activity activities').read()
        if "com.google.android.youtube" in output:
            if last_activity != "YouTube":
                send_webhook("Kia Ainsleyy Has Opened YouTube")
                last_activity = "YouTube"
        else:
            last_activity = None
        
        # Check Termux activity
        if "com.termux" in output:
            if last_activity != "Termux":
                send_webhook("Kia Ainsleyy Has Opened Termux")
                last_activity = "Termux"
        
        # Check battery status
        battery_status, percentage = get_battery_status()
        if battery_status != last_battery_status:
            send_webhook(f"Battery {battery_status} at {percentage}%")
            last_battery_status = battery_status
        
        time.sleep(1)  # Check every second

if __name__ == "__main__":
    check_youtube_activity()
