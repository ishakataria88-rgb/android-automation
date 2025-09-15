import os
import subprocess
from pathlib import Path
import shutil
import hashlib


class APKExtractor:
    def __init__(self):
        self.LIB_SO_NAME = "libmyapp.so"
        self.tools_dir = r"C:\Users\sranjan\Desktop\APK_final\jadx-1.5.2"

    def extract_with_apktool(self, apk_path: str, output_dir: str) -> bool:
        apktool_jar = r"C:\Users\sranjan\Desktop\APK_final\apktool.jar"
        print(f"🔧 Running apktool on: {apk_path}")
        try:
            subprocess.run(
                ["java", "-jar", apktool_jar, "d", apk_path, "-o", output_dir, "-f", "-q"],
                check=True
            )
            return True
        except Exception as e:
            print(f"❌ Error running apktool: {e}")
            return False

    def extract_with_jadx(self, apk_path: str, output_dir: str) -> bool:
        jadx_path = f"{self.tools_dir}\\bin\\jadx.bat"
        print(f"🔧 Running JADX on: {apk_path}")
        try:
            subprocess.run(
                [jadx_path, "--quiet", "-d", output_dir, apk_path],
                check=True
            )
            return True
        except Exception as e:
            print(f"❌ Error running JADX: {e}")
            return False

    def find_icmobile_pkg(self, base_dir: str) -> str:
        target_path = os.path.join("com", "adobe", "mobile", "icmobilelib")
        for root, dirs, _ in os.walk(base_dir):
            for d in dirs:
                if d == "icmobilelib" and target_path in os.path.join(root, d):
                    return "Yes"
        return "No"

    def find_libmyapp_so(self, base_dir: str) -> str:
        for root, _, files in os.walk(base_dir):
            if self.LIB_SO_NAME in files:
                return "Yes"
        return "No"

    def extract_apk(self, apk_path: str, output_dir: str) -> dict:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        if not self.extract_with_apktool(apk_path, output_dir):
            if not self.extract_with_jadx(apk_path, output_dir):
                return {"icmobile_pkg": "No", "libmyapp_so": "No"}

        icmobile_pkg = self.find_icmobile_pkg(output_dir)
        libmyapp_so = self.find_libmyapp_so(output_dir)

        shutil.rmtree(output_dir, ignore_errors=True)

        return {"icmobile_pkg": icmobile_pkg, "libmyapp_so": libmyapp_so}


# --- Hash extraction ---
def calculate_md5(file_path):
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except:
        return "N/A"


def extract_apk_hashes(apk_file: Path):
    """Extract APK hashes using apkExtract.exe (must be in same folder)"""
    exe_path = Path(__file__).parent / "apkExtract.exe"
    if not exe_path.exists():
        return {
            "pub_key_hash": "N/A",
            "certificate_v2": "N/A",
            "google_hash": "N/A",
            "classes_dex_hash": "N/A",
            "all_dex_hash": "N/A",
            "md5": calculate_md5(apk_file)
        }

    try:
        process_extract = subprocess.run(
            [str(exe_path), "-f", str(apk_file)],
            capture_output=True, text=True
        )
        output_extract = process_extract.stdout.splitlines()
        for line in output_extract:
            if "PubKeyHash" in line and "CertificateV2" in line:
                continue
            parts = line.split(",")
            if len(parts) >= 6:
                return {
                    "pub_key_hash": parts[1].strip(),
                    "certificate_v2": parts[2].strip(),
                    "google_hash": parts[3].strip() if parts[3].strip() else "N/A",
                    "classes_dex_hash": parts[4].strip(),
                    "all_dex_hash": parts[5].strip(),
                    "md5": calculate_md5(apk_file)
                }
    except:
        pass

    return {
        "pub_key_hash": "N/A",
        "certificate_v2": "N/A",
        "google_hash": "N/A",
        "classes_dex_hash": "N/A",
        "all_dex_hash": "N/A",
        "md5": calculate_md5(apk_file)
    }


# --- Main APK info ---
def get_apk_info(apk_path: Path):
    try:
        aapt_path = r"C:\Users\sranjan\Desktop\APK_final\Sdk\Sdk\build-tools\35.0.0\aapt.exe"
        command = [aapt_path, "dump", "badging", str(apk_path)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        output = result.stdout

        version = "N/A"
        product = "N/A"

        # Parse package name and version more robustly
        for line in output.splitlines():
            if line.startswith("package:"):
                for part in line.split():
                    if part.startswith("name="):
                        product = part.split("=", 1)[1].strip("'\"")
                    elif part.startswith("versionName="):
                        version = part.split("=", 1)[1].strip("'\"")
                break

        extractor = APKExtractor()
        extract_dir = Path("./tmp_extract")
        extraction = extractor.extract_apk(str(apk_path), str(extract_dir))

        hash_info = extract_apk_hashes(apk_path)

        return version, product, extraction["icmobile_pkg"], extraction["libmyapp_so"], hash_info

    except Exception as e:
        import traceback
        print(f"❌ Failed to extract APK info: {e}")
        print(traceback.format_exc())
        version = product = icmobile_pkg = libmyapp_so = "N/A"
        hash_info = {k: "N/A" for k in
                     ["pub_key_hash", "certificate_v2", "google_hash", "classes_dex_hash", "all_dex_hash", "md5"]}
        return version, product, icmobile_pkg, libmyapp_so, hash_info
