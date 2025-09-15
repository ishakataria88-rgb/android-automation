# ——— Final working script ———
import uiautomator2 as u2
import time
import subprocess
from pathlib import Path
import csv
from datetime import datetime
import shutil
from apk_inspect import get_apk_info

# --- CONFIG ---
apk_folder = Path(r"C:\Users\ikataria\Desktop\APK_final\downloaded_files")
adb_path = r"C:\Users\ikataria\AppData\Local\Android\Sdk\platform-tools\adb.exe"
email = "ikataria+test@adobetest.com"
password = "Tester@123"

# Timestamped files
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = apk_folder / f"apk_run_{ts}.log"
csv_file = apk_folder / f"apk_results.csv"

d = u2.connect()

def log_msg(msg):
    print(msg)
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(msg + "\n")

# CSV Setup
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "APK Name", "Install Status", "Login Status", "SwitchNowFound",
        "Installation Status", "Installed from Play Store", "Paywall After Genuine Install",
        "Version", "Product", "Package Name", "icmobile_pkg", "libmyapp_so",
        "PubKeyHash", "CertificateV2", "GoogleHash", "Classes.dex",
        "All Dex Hash", "MD5"
    ])

# Popup handler
popup_texts = [
    "OK", "Close", "Cancel", "Allow", "Allow all", "DISMISS", "NO THANKS",
    "Dismiss", "Got it", "No Thanks", "Continue", "Continue to Lightroom"
]

def handle_popups(retries=5):
    for _ in range(retries):
        for text in popup_texts:
            try:
                if d(text=text).exists(timeout=1):
                    d(text=text).click()
                    log_msg(f"⚠️ Clicked popup: {text}")
                    time.sleep(1)
            except:
                continue
        time.sleep(0.5)

# Switch Now logic
def handle_switch_now(app_package="com.adobe.lrmobile"):
    for attempt in range(1, 4):
        log_msg(f"🔍 Attempting to detect 'Switch now' popup (Attempt {attempt}/3)")
        for i in range(10):  # Wait up to 10 seconds in smaller steps
            xml = d.dump_hierarchy(compressed=False).lower()
            if "switch now" in xml:
                log_msg(f"✅ 'Switch now' detected in XML (Attempt {attempt})")
                try:
                    if d(textContains="Switch now").exists(timeout=2):
                        d(textContains="Switch now").click()
                    else:
                        d.click(700, 1300)  # fallback tap
                    time.sleep(2)
                    handle_popups()
                    return True
                except Exception as e:
                    log_msg(f"⚠️ Failed to click 'Switch now': {e}")
                    return False
            time.sleep(1)
        log_msg(f"❌ 'Switch now' not found in Attempt {attempt}. Relaunching app...")
        d.app_stop(app_package)
        time.sleep(1)
        d.app_start(app_package, wait=True)
        time.sleep(3)
        handle_popups()
    return False


# Login
def perform_login(force_login=False):
    switch_now_found = False

    if not force_login and (d(textContains="Photos on device").exists(timeout=3) or d(textContains="Gallery").exists(timeout=3)):
        log_msg("✅ Already logged in, skipping login")
        handle_popups()
        return True, False, False, False

    for attempt in range(1, 4):
        log_msg(f"🔁 Login Attempt {attempt}/3")
        if d(descriptionContains="Adobe").exists(timeout=5):
            d(descriptionContains="Adobe").click()
        elif d(textContains="Adobe").exists(timeout=5):
            d(textContains="Adobe").click()
        else:
            log_msg("❌ 'Sign in with Adobe' button not found")
            time.sleep(2)
            continue

        time.sleep(2)

        if d(text="Email address").exists(timeout=10):
            d(text="Email address").click()
            d(className="android.widget.EditText").set_text(email)
            time.sleep(1)
            d.press("back")
            if d(text="Continue").exists:
                d(text="Continue").click()
            else:
                d.click(650, 1100)
            time.sleep(3)

        if d(text="Password").exists(timeout=10):
            d(className="android.widget.EditText").set_text(password)
            time.sleep(1)
            d.press("back")
            if d(text="Continue").exists:
                d(text="Continue").click()
            else:
                d.click(650, 1100)
            time.sleep(5)
            handle_popups()

            if handle_switch_now():
                switch_now_found = True
                time.sleep(5)
                genuine_install_success, paywall_found = run_genuine_install_flow()
                return False, switch_now_found, genuine_install_success, paywall_found

            if d(textContains="Photos on device").exists(timeout=5) or d(textContains="Gallery").exists(timeout=5):
                log_msg("🎉 Login successful")
                handle_popups()
                return True, switch_now_found, False, False
        else:
            log_msg("❌ Password field not found")
            time.sleep(2)
    return False, switch_now_found, False, False

# Genuine install flow
def run_genuine_install_flow():
    success = False
    paywall = False

    if d(textContains="Get free app").exists(timeout=5):
        d(textContains="Get free app").click()
        log_msg("✅ Clicked 'Get free app'")
        time.sleep(5)

    if d(textContains="Install from Play").exists(timeout=10):
        d(textContains="Install from Play").click()
        log_msg("✅ Clicked 'Install from Play'")
        time.sleep(3)

    if d(text="Install from Play").exists(timeout=5):
        d(text="Install from Play").click()
        log_msg("✅ Confirmed popup")
        time.sleep(5)

    if d(text="Install").exists(timeout=10):
        d(text="Install").click()
        log_msg("📥 Clicked install on Play Store")
        time.sleep(20)

    if d(text="Open").exists(timeout=10):
        d(text="Open").click()
        log_msg("📱 Clicked 'Open' to launch app")
        time.sleep(4)

        # Press back to close overlays
        d.press("back")
        time.sleep(1)
        d.press("back")
        log_msg("🏠 Closed Play Store after genuine install")

        # Relaunch app
        d.app_start("com.adobe.lrmobile", wait=True)
        log_msg("🚀 Relaunched Lightroom after Play Store install")
        time.sleep(3)

        # Ensure login is performed again
        login_success, _, _, _ = perform_login(force_login=True)

        if login_success:
            d.press("back")
            time.sleep(2)

            paywall_keywords = ["Try Lightroom Premium", "₹", "Subscribe now", "Unlock", "premium", "Annual"]
            for i in range(6):
                xml = d.dump_hierarchy(compressed=False)
                if any(k.lower() in xml.lower() for k in paywall_keywords):
                    log_msg("💰 Paywall detected after genuine install (via XML)")
                    paywall = True
                    break
                time.sleep(2)

            if not paywall:
                try:
                    nodes = d.xpath("//node[@text]").all()
                    for node in nodes:
                        text = node.attrib.get("text", "").lower()
                        if any(k.lower() in text for k in paywall_keywords):
                            log_msg(f"💰 Paywall detected from screen text: {text}")
                            paywall = True
                            break
                except Exception as e:
                    log_msg(f"⚠️ Fallback paywall check failed: {e}")

            success = True
    return success, paywall

# APK Loop
for apk_file in apk_folder.glob("*.apk"):
    log_msg(f"\n📦 Processing: {apk_file.name}")
    install_status = "Fail"
    login_status = "Fail"
    switch_now_found = False
    final_status = "Failed to install"
    installed_from_play = "No"
    paywall_after_play = "No"

    try:
        version, product, icmobile_pkg, libmyapp_so, hash_info = get_apk_info(apk_file)
        package_name = product
        if product == "com.adobe.lrmobile":
            product = "Lightroom"
        log_msg(f"✅ APK info: Version={version}, Product={product}")
    except:
        version = product = icmobile_pkg = libmyapp_so = "N/A"
        package_name = "N/A"
        hash_info = {k: "N/A" for k in ["pub_key_hash", "certificate_v2", "google_hash", "classes_dex_hash", "all_dex_hash", "md5"]}

    try:
        subprocess.run([adb_path, "install", "-r", str(apk_file)], check=True)
        install_status = "Success"
        log_msg("🚀 APK installed")
    except:
        log_msg("❌ Install failed")
        continue

    try:
        d.app_start(package_name, wait=True)
        time.sleep(5)
        handle_popups()
    except:
        continue

    login_success, switch_now_found, genuine_success, paywall_found = perform_login()

    if switch_now_found:
        login_status = "Skipped"
        installed_from_play = "Yes" if genuine_success else "No"
        paywall_after_play = "Yes" if paywall_found else "No"
        final_status = "Installed from Play Store" if genuine_success else "Failed to install"
    else:
        login_status = "Success" if login_success else "Fail"
        final_status = "Installed, working properly" if login_success else "Failed to login"

    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            apk_file.name, install_status, login_status, str(switch_now_found),
            final_status, installed_from_play, paywall_after_play,
            version, product, package_name,
            icmobile_pkg, libmyapp_so,
            hash_info["pub_key_hash"], hash_info["certificate_v2"], hash_info["google_hash"],
            hash_info["classes_dex_hash"], hash_info["all_dex_hash"], hash_info["md5"]
        ])

    subprocess.run([adb_path, "uninstall", package_name])
    log_msg(f"🗑 Uninstalled {apk_file.name}")

    for f in apk_folder.glob("Dumps_*"):
        if f.is_dir():
            shutil.rmtree(f, ignore_errors=True)

log_msg("🎉 All APKs processed.")
