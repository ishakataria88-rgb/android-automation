import pandas as pd
import requests
import json
from tabulate import tabulate

def format_unicode_table(title, series):
    table = [[status, count] for status, count in series.items()]
    return f"\n{title}\n" + tabulate(table, headers=["Status", "Count"], tablefmt="fancy_grid")

def generate_slack_tabular_report(csv_path):
    df = pd.read_csv(csv_path)

    total_apks = df["APK Name"].nunique()
    products = df["Product"].dropna().unique().tolist()
    versions = df["Version"].dropna().unique().tolist()

    # Value counts
    install_status = df["Install Status"].value_counts()
    login_status = df["Login Status"].value_counts()
    working_status = df["Working Status"].value_counts()
    installed_from_play = df["Installed from Play Store"].value_counts()
    paywall_status = df["Paywall After Genuine Install"].value_counts()
    switch_now = df["SwitchNowFound"].astype(str).value_counts()

    # Start message block
    message = f"""```
📊 APK Automation Summary

General Info
────────────
Total APKs   : {total_apks}
Products     : {', '.join(products)}
Versions     : {', '.join(versions)}
"""

    # Add summary tables
    message += format_unicode_table("📥 Install Status", install_status)
    message += format_unicode_table("🔐 Login Status", login_status)
    message += format_unicode_table("⚙️ Working Status", working_status)
    message += format_unicode_table("🧪 SwitchNow Found", switch_now)
    message += format_unicode_table("📦 Installed from Play Store", installed_from_play)
    message += format_unicode_table("💰 Paywall After Genuine Install", paywall_status)
    

    # Failures — Paywall is no longer considered a failure
    failed_df = df[
        (df["Install Status"].str.lower() != "success") |
        (df["Login Status"].str.lower() != "success") |
        (df["Working Status"].str.lower() != "installed, working properly") |
        (df["Installed from Play Store"].str.lower() != "yes")
    ]

    if failed_df.empty:
        message += "\n\n✅ All APKs passed validation."
    else:
        message += "\n\n🚨 Detected Failures:\n───────────────"
        for _, row in failed_df.iterrows():
            message += (
                f"\n• {row['APK Name'][:30]:<30} → "
                f"Install: {row['Install Status']}, "
                f"Login: {row['Login Status']}, "
                f"Working: {row['Working Status']}, "
                f"Play Store: {row['Installed from Play Store']}"
            )

    message += "\n\n✅ End of Report```"
    return message

def send_to_slack(message, webhook_url):
    payload = {"text": message}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
    if response.status_code == 200:
        print("✅ Slack message sent successfully!")
    else:
        print(f"❌ Failed to send message: {response.status_code} - {response.text}")

# === RUN SCRIPT ===
if __name__ == "__main__":
    csv_path = r"C:\Users\ikataria\Desktop\APK_final\downloaded_files\apk_results.csv"  # ✅ Update this path
    webhook_url = "https://hooks.slack.com/services/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"   # ✅ Replace with your actual Slack webhook URL
    #webhook_url = "https://hooks.slack.com/services/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" # hack build installation

    message = generate_slack_tabular_report(csv_path)
    send_to_slack(message, webhook_url)
