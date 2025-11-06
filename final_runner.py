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

apk_folder.mkdir(parents=True, exist_ok=True)

network_logs_folder = apk_folder / "network_logs"
network_logs_folder.mkdir(parents=True, exist_ok=True)

REMOTE_CAPTURE_DIR = "/sdcard/NetworkCaptures"
_TCPDUMP_AVAILABLE = None

email = "ikataria+test@adobetest.com"
password = "Tester@123"

# Timestamped files
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = apk_folder / f"apk_run_{ts}.log"
csv_file = apk_folder / f"apk_results.csv"

log_file.parent.mkdir(parents=True, exist_ok=True)

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
        "Installation Status", "Version", "Product", "Package Name",
        "icmobile_pkg", "libmyapp_so", "PubKeyHash", "CertificateV2",
        "GoogleHash", "Classes.dex", "All Dex Hash", "MD5",
        "Installed from Play Store", "Paywall After Genuine Install",
        "Network Capture File"
    ])


def is_tcpdump_available():
    global _TCPDUMP_AVAILABLE
    if _TCPDUMP_AVAILABLE is not None:
        return _TCPDUMP_AVAILABLE

    try:
        result = subprocess.run(
            [adb_path, "shell", "command", "-v", "tcpdump"],
            capture_output=True,
            text=True,
            timeout=10
        )
        _TCPDUMP_AVAILABLE = result.returncode == 0 and result.stdout.strip() != ""
    except Exception as exc:
        log_msg(f"⚠️ Unable to verify tcpdump availability: {exc}")
        _TCPDUMP_AVAILABLE = False

    if not _TCPDUMP_AVAILABLE:
        log_msg("⚠️ 'tcpdump' binary not found on device. Network traffic capture will be skipped.")

    return _TCPDUMP_AVAILABLE


def start_network_capture(package_name: str):
    if not package_name or package_name == "N/A":
        return None

    if not is_tcpdump_available():
        return None

    capture_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    remote_path = f"{REMOTE_CAPTURE_DIR}/{package_name}_{capture_ts}.pcap"
    local_path = network_logs_folder / f"{package_name}_{capture_ts}.pcap"

    subprocess.run([adb_path, "shell", "mkdir", "-p", REMOTE_CAPTURE_DIR], check=False)

    capture_cmd = f"mkdir -p {REMOTE_CAPTURE_DIR} && tcpdump -i any -s 0 -n -w {remote_path}"
    try:
        process = subprocess.Popen(
            [adb_path, "exec-out", "sh", "-c", capture_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
    except Exception as exc:
        log_msg(f"⚠️ Failed to start network capture: {exc}")
        return None

    time.sleep(2)
    if process.poll() is not None:
        stderr_output = ""
        if process.stderr:
            try:
                stderr_output = process.stderr.read().decode("utf-8", errors="replace").strip()
            except Exception:
                stderr_output = ""
            finally:
                try:
                    process.stderr.close()
                except Exception:
                    pass
        log_msg(f"⚠️ tcpdump exited immediately: {stderr_output or 'Unknown error'}")
        return None

    log_msg(f"📡 Started network capture for {package_name} -> {local_path}")
    return process, remote_path, local_path


def stop_network_capture(handle):
    if not handle:
        return ""

    process, remote_path, local_path = handle

    if process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception as exc:
            log_msg(f"⚠️ Error while stopping tcpdump: {exc}")

    stderr_output = ""
    if process.stderr:
        try:
            stderr_output = process.stderr.read().decode("utf-8", errors="replace").strip()
        except Exception:
            stderr_output = ""
        finally:
            try:
                process.stderr.close()
            except Exception:
                pass

    if stderr_output:
        log_msg(f"ℹ️ tcpdump output: {stderr_output}")

    time.sleep(1)

    try:
        pull_result = subprocess.run(
            [adb_path, "pull", remote_path, str(local_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        if pull_result.returncode == 0:
            log_msg(f"💾 Network capture saved to {local_path}")
            subprocess.run([adb_path, "shell", "rm", "-f", remote_path], check=False)
            return str(local_path)
        else:
            error_text = pull_result.stderr.strip() or pull_result.stdout.strip()
            log_msg(f"⚠️ Failed to pull network capture: {error_text}")
            return ""
    except Exception as exc:
        log_msg(f"⚠️ Error while pulling network capture: {exc}")
        return ""


class NetworkCaptureSession:
    def __init__(self):
        self.handle = None
        self.local_path = ""

    def start(self, package_name: str):
        if self.handle is not None:
            return
        handle = start_network_capture(package_name)
        if handle:
            self.handle = handle
            self.local_path = str(handle[2])

    def stop(self):
        if not self.handle:
            return self.local_path
        captured_path = stop_network_capture(self.handle)
        self.handle = None
        if captured_path:
            self.local_path = captured_path
        else:
            self.local_path = ""
        return self.local_path

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
        d.app_start(app_package, wait=True)
        time.sleep(5)
        handle_popups()
        if d(textContains="Switch now").exists(timeout=6):
            log_msg(f"✅ 'Switch now' popup detected (Attempt {attempt}/3). Clicking and continuing flow.")
            d(textContains="Switch now").click()
            time.sleep(2)
            handle_popups()
            return True
        else:
            log_msg(f"❌ 'Switch now' not found (Attempt {attempt}/3). Retrying...")
            d.app_stop(app_package)
            time.sleep(2)
    return False

# --- GENUINE INSTALL FLOW ---
def run_genuine_install_flow():
    installed = False
    paywall_found = False

    if d(textContains="Get").exists(timeout=10):
        d(textContains="Get").click()
        log_msg("🛒 Clicked 'Get' or 'Get app' on Adobe page")
        time.sleep(3)

    if d(textContains="Install from Play").exists(timeout=10):
        d(textContains="Install from Play").click()
        log_msg("▶️ Clicked 'Install from Play' on Play Store page")
        time.sleep(3)

        if d(textContains="Install from Play").exists(timeout=6):
            d(textContains="Install from Play").click()
            log_msg("📥 Confirmed install from Play popup")
            time.sleep(3)

    if d(text="Install").exists(timeout=15):
        d(text="Install").click()
        log_msg("⬇️ Clicked 'Install' in Play Store")
        time.sleep(10)

    log_msg("⏳ Waiting for 'Open' button in Play Store...")
    for _ in range(30):
        if d(text="Open").exists:
            d(text="Open").click()
            installed = True
            log_msg("📱 Clicked 'Open' to launch app from Play Store")
            break
        time.sleep(2)

    d.press("home")
    log_msg("🏠 Closed Play Store after genuine install")

    d.app_start("com.adobe.lrmobile", wait=True)
    time.sleep(5)
    d.press("back")
    log_msg("↩️ Pressed back after launch to dismiss overlays")
    handle_popups()

    # Always try login again
    if d(text="Email address").exists(timeout=8):
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

    # Check for paywall
    log_msg("🔎 Checking for paywall after genuine install...")
    screen_texts = d.dump_hierarchy(compressed=True)
    paywall_keywords = ["Subscribe now", "₹", "premium", "upgrade", "year"]

    for keyword in paywall_keywords:
        if keyword.lower() in screen_texts.lower():
            paywall_found = True
            log_msg("💰 Paywall detected after genuine install")
            break

    return installed, paywall_found

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
                return True, switch_now_found

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
    paywall_detected = "No"
    network_capture = NetworkCaptureSession()

    try:
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
            hash_info = {k:"N/A" for k in ["pub_key_hash","certificate_v2","google_hash","classes_dex_hash","all_dex_hash","md5"]}

        # --- INSTALL APK ---
        try:
            log_msg(f"Running install command: {adb_path} install -r {apk_file}")
            subprocess.run([adb_path, "install", "-r", str(apk_file)], check=True)
            install_status = "Success"
            log_msg("🚀 APK installed successfully")
        except subprocess.CalledProcessError:
            log_msg("❌ Installation failed")
            continue

        network_capture.start(package_name)

        # --- LAUNCH APP ---
        try:
            d.app_start(package_name, wait=True)
            time.sleep(6)
            handle_popups()
        except Exception as e:
            log_msg(f"❌ Failed to launch app: {e}")
            continue

        # --- LOGIN ---
        login_success, switch_now_found = perform_login()
        login_status = "Success" if login_success else "Fail"

        # --- INSTALLATION STATUS ---
        if install_status == "Success" and login_status == "Success":
            final_status = "Installed, working properly"
        elif install_status == "Success" and login_status == "Fail":
            final_status = "Failed to login"
        else:
            final_status = "Failed to install"

        # --- GENUINE INSTALL FLOW ---
        if switch_now_found:
            d.press("home")
            d.app_start("com.adobe.lrmobile", wait=True)
            installed_from_play, paywall_found = run_genuine_install_flow()
            installed_from_play = "Yes" if installed_from_play else "No"
            paywall_detected = "Yes" if paywall_found else "No"

        network_capture.stop()

        # --- WRITE TO CSV ---
        with open(csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                apk_file.name, install_status, login_status, str(switch_now_found),
                final_status, version, product, package_name,
                icmobile_pkg, libmyapp_so,
                hash_info["pub_key_hash"], hash_info["certificate_v2"], hash_info["google_hash"],
                hash_info["classes_dex_hash"], hash_info["all_dex_hash"], hash_info["md5"],
                installed_from_play, paywall_detected,
                network_capture.local_path
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
    finally:
        network_capture.stop()

log_msg("\n🎉 All APKs processed.")
