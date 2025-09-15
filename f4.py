
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
aapt_path = adb_path.replace("adb.exe", r"..\build-tools\35.0.0\aapt.exe")

email = "ikataria+test@adobetest.com"
password = "Tester@123"

# Timestamped files
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = apk_folder / f"apk_run_{ts}.log"
csv_file = apk_folder / f"apk_results.csv"

# --- DEVICE CONNECTION ---
d = u2.connect()
def log_msg(msg):
    print(msg)
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(msg + "\n")

log_msg(f"📱 Connected to: {d.device_info}")

# --- CSV SETUP ---
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "APK Name", "Install Status", "Login Status", "SwitchNowFound",
        "Installation Status", "Installed from Play Store", "Paywall After Genuine Install",
        "Version", "Product", "Package Name",
        "icmobile_pkg", "libmyapp_so",
        "PubKeyHash", "CertificateV2", "GoogleHash", "Classes.dex",
        "All Dex Hash", "MD5"
    ])

# --- POPUP HANDLER ---
popup_texts = [
    "OK", "Close", "Cancel", "Allow", "Allow all", "DISMISS", "NO THANKS",
    "Dismiss", "Got it", "No Thanks", "Continue", "Continue to Lightroom"
]

def handle_popups(retries=5):
    for _ in range(retries):
        for text in popup_texts:
            try:
                if d(text=text).exists(timeout=1):
                    log_msg(f"⚠️ Popup: '{text}' found, clicking...")
                    d(text=text).click()
                    time.sleep(1)
            except:
                continue
        time.sleep(0.5)

# --- SWITCH NOW HANDLER ---
def handle_switch_now(app_package="com.adobe.lrmobile"):
    for attempt in range(1, 4):
        if d(textContains="Switch now").exists(timeout=5):
            log_msg(f"✅ 'Switch now' popup detected (Attempt {attempt}/3). Clicking and continuing flow.")
            d(textContains="Switch now").click()
            time.sleep(5)
            handle_popups()

            # Wait until 'Get free app' appears, up to 15 seconds
            for i in range(5):
                if d(textContains="Get free app").exists(timeout=3):
                    log_msg("🕹️ 'Get free app' page loaded.")
                    return True
                else:
                    log_msg("⏳ Waiting for 'Get free app' page to load...")
                    time.sleep(2)

            log_msg("⚠️ 'Get free app' page did not load after 'Switch now'")
            return True  # Even if it didn't appear, we return True to proceed with fallback

        else:
            log_msg(f"❌ 'Switch now' not found (Attempt {attempt}/3). Relaunching app...")
            d.app_stop(app_package)
            time.sleep(1)
            d.app_start(app_package, wait=True)
            time.sleep(3)
            handle_popups()
    return False

def run_genuine_install_flow():
    success = False
    paywall = False

    # Step 1: Get free app
    if d(textContains="Get free app").exists(timeout=10):
        d(textContains="Get free app").click()
        log_msg("✅ Clicked 'Get free app'")
        time.sleep(5)

    # Step 2: Install from Play
    if d(textContains="Install from Play").exists(timeout=10):
        d(textContains="Install from Play").click()
        log_msg("✅ Clicked 'Install from Play'")
        time.sleep(3)

    # Step 3: Confirm small install popup
    if d(text="Install from Play").exists(timeout=5):
        d(text="Install from Play").click()
        log_msg("✅ Confirmed install popup")
        time.sleep(5)

    # Step 4: Install button on Play Store
    if d(text="Install").exists(timeout=10):
        d(text="Install").click()
        log_msg("✅ Clicked 'Install' on Play Store")
        time.sleep(20)

    # Step 5: Open the app
    if d(text="Open").exists(timeout=10):
        d(text="Open").click()
        log_msg("📱 Clicked 'Open' to launch app from Play Store")
        time.sleep(5)

        # Press back twice to exit Play Store
        d.press("back")
        time.sleep(1)
        d.press("back")
        log_msg("🏠 Closed Play Store after genuine install")
        time.sleep(2)

        # Explicitly relaunch Lightroom app
        d.app_start("com.adobe.lrmobile", wait=True)
        log_msg("🚀 Relaunched Lightroom after Play Store install")
        time.sleep(2)

        # Try login again (but skip if already logged in)
        login_success, _ = perform_login()

        if login_success:
            paywall_keywords = ["Try Lightroom Premium", "₹", "Subscribe now", "Annual", "Unlock", "premium"]
            paywall = False

            for i in range(6):
                xml = d.dump_hierarchy(compressed=False)
                if any(keyword.lower() in xml.lower() for keyword in paywall_keywords):
                    log_msg("💰 Paywall detected after genuine install (via XML)")
                    paywall = True
                    break
                time.sleep(2)

            # Fallback using visible text nodes
            if not paywall:
                try:
                    visible_texts = d.xpath("//node[@text]").all()
                    for node in visible_texts:
                        t = node.attrib.get("text", "").lower()
                        if any(keyword.lower() in t for keyword in paywall_keywords):
                            log_msg(f"💰 Paywall detected from screen text: {t}")
                            paywall = True
                            break
                except Exception as e:
                    log_msg(f"⚠️ Fallback paywall check failed: {e}")

            success = True

    return success, paywall


# --- LOGIN FUNCTION ---
def perform_login():
    if d(textContains="Photos on device").exists(timeout=3) or d(textContains="Gallery").exists(timeout=3):
        log_msg("✅ Already logged in, skipping login")
        handle_popups()
        return True, False

    switch_now_found = False

    for attempt in range(1, 4):
        log_msg(f"🔁 Login Attempt {attempt}/3")
        if d(descriptionContains="Adobe").exists(timeout=4):
            d(descriptionContains="Adobe").click()
        elif d(textContains="Adobe").exists(timeout=4):
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
            time.sleep(1)
            if d(text="Continue").exists:
                d(text="Continue").click()
            else:
                d.click(650, 1100)
            time.sleep(3)

        if d(text="Password").exists(timeout=10):
            d(className="android.widget.EditText").set_text(password)
            time.sleep(1)
            d.press("back")
            time.sleep(1)
            if d(text="Continue").exists:
                d(text="Continue").click()
            else:
                d.click(650, 1100)
            time.sleep(5)
            handle_popups()

            if handle_switch_now():
                switch_now_found = True
                return False, switch_now_found  # Don’t continue login, trigger Play Store flow

            if d(textContains="Photos on device").exists(timeout=5) or d(textContains="Gallery").exists(timeout=5):
                log_msg("🎉 Login successful")
                handle_popups()
                return True, switch_now_found
        else:
            log_msg("❌ Password field not found")
            time.sleep(2)
    return False, switch_now_found

# --- PROCESS APKs ---
for apk_file in apk_folder.glob("*.apk"):
    log_msg(f"\n📦 Processing: {apk_file.name}")
    install_status = "Fail"
    login_status = "Fail"
    switch_now_found = False
    final_status = "Failed to install"
    installed_from_play = "No"
    paywall_after_play = "No"

    # --- APK INFO ---
    try:
        version, product, icmobile_pkg, libmyapp_so, hash_info = get_apk_info(apk_file)
        package_name = product
        if product == "com.adobe.lrmobile":
            product = "Lightroom"
        log_msg(f"✅ APK info extracted: Version={version}, Product={product}")
    except Exception as e:
        log_msg(f"❌ Failed to extract APK info: {e}")
        version = product = icmobile_pkg = libmyapp_so = "N/A"
        package_name = "N/A"
        hash_info = {k: "N/A" for k in ["pub_key_hash", "certificate_v2", "google_hash", "classes_dex_hash", "all_dex_hash", "md5"]}

    # --- INSTALL APK ---
    try:
        log_msg(f"Running install command: {adb_path} install -r {apk_file}")
        subprocess.run([adb_path, "install", "-r", str(apk_file)], check=True)
        install_status = "Success"
        log_msg("🚀 APK installed successfully")
    except subprocess.CalledProcessError:
        log_msg("❌ Installation failed")
        final_status = "Failed to install"
        continue

    # --- LAUNCH APP ---
    try:
        d.app_start(package_name, wait=True)
        time.sleep(6)
        handle_popups()
    except Exception as e:
        log_msg(f"❌ Failed to launch app: {e}")
        final_status = "Failed to install"
        continue

    # --- LOGIN ---
    login_success, switch_now_found = perform_login()

    if switch_now_found:
        login_status = "Skipped"
        genuine_install_success, paywall_found = run_genuine_install_flow()
        installed_from_play = "Yes" if genuine_install_success else "No"
        paywall_after_play = "Yes" if paywall_found else "No"
    else:
        login_status = "Success" if login_success else "Fail"

    # --- INSTALLATION STATUS ---
    if install_status == "Success" and login_status == "Success":
        final_status = "Installed, working properly"
    elif install_status == "Success" and login_status == "Fail":
        final_status = "Failed to login"
    elif installed_from_play == "Yes":
        final_status = "Installed from Play Store"
    else:
        final_status = "Failed to install"

    # --- WRITE TO CSV ---
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

    # --- UNINSTALL APK ---
    subprocess.run([adb_path, "uninstall", package_name])
    log_msg(f"🗑 Uninstalled {apk_file.name}")

    # --- DELETE Dumps_* folders ---
    for dump_folder in apk_folder.glob("Dumps_*"):
        if dump_folder.is_dir():
            try:
                shutil.rmtree(dump_folder)
                log_msg(f"🗑 Deleted folder: {dump_folder}")
            except Exception as e:
                log_msg(f"⚠️ Could not delete folder {dump_folder}: {e}")

log_msg("\n🎉 All APKs processed.")
