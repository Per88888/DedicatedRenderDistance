import os
import glob
import json
import subprocess
import sys
import shutil



# How to use:#
# 1. Place this script in the same folder as UAssetGUI.exe.
# 2. Set TARGET_DIR to the folder containing the .uasset files you want to modify.
# 3. Adjust NEW_NET_CULL to your desired render distance.

# --- CONFIGURATION ---------------------------------------------------------
# Render distance.
NEW_NET_CULL = 10000000000

TARGET_DIR = r"C:\Users\perno\Skrivbord\Astroneer modding\Game Files server\Nuttcull test full auto\Content"

# UAssetGUI Settings
UASSET_EXE = "UAssetGUI.exe"
ENGINE_VERSION_ARG = "VER_UE4_27"
def check_requirements():
    if not os.path.exists(UASSET_EXE):
        print(f"[ERROR] Could not find {UASSET_EXE} in this folder.")
        sys.exit()
    has_assets = False
    for root, dirs, files in os.walk(TARGET_DIR):
        for file in files:
            if file.endswith(".uasset"):
                has_assets = True
                break
        if has_assets:
            break
    if not has_assets:
        print(f"[ERROR] No .uasset files found in {TARGET_DIR} or its subfolders.")
        sys.exit()
    if os.path.exists("Modded_Build"):
        try:
            shutil.rmtree("Modded_Build")
        except OSError as e:
            print(f"[WARNING] Could not clean 'Modded_Build' folder: {e}")
            print("          Proceeding anyway (files will be overwritten)...")
    os.makedirs("Modded_Build", exist_ok=True)
def run_uasset_gui(args):
    """Runs UAssetGUI and handles crashes gracefully."""
    try:
        result = subprocess.run([UASSET_EXE] + args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[DEBUG] UAssetGUI Failed with return code {e.returncode}")
        print(f"[DEBUG] STDOUT: {e.stdout}")
        print(f"[DEBUG] STDERR: {e.stderr}")
        return False
def process_files():
    print(f"\n--- Scanning for assets in {TARGET_DIR} ---")
    for root, dirs, files in os.walk(TARGET_DIR):
        if "Modded_Build" in root:
            continue
        for file in files:
            if not file.endswith(".uasset"):
                continue
            uasset_path = os.path.join(root, file)
            rel_path = os.path.relpath(root, TARGET_DIR)
            output_dir = os.path.join("Modded_Build", rel_path)
            os.makedirs(output_dir, exist_ok=True)
            json_name = uasset_path.replace(".uasset", ".json")
            uexp_path = uasset_path.replace(".uasset", ".uexp")
            if not os.path.exists(uexp_path):
                print(f"[SKIP] {uasset_path} missing .uexp file")
                continue
            print(f"> Processing {uasset_path}...")
            if not run_uasset_gui(["tojson", uasset_path, json_name, ENGINE_VERSION_ARG]):
                print(f"  [ERROR] Failed to Extract (tojson) {uasset_path}")
                continue
            try:
                with open(json_name, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                modified = False
                if "NameMap" in data and isinstance(data["NameMap"], list):
                    existing_names = [n.lower() for n in data["NameMap"]]
                    if "netculldistancesquared" not in existing_names:
                        data["NameMap"].append("NetCullDistanceSquared")
                        modified = True    
                if "floatproperty" not in existing_names:
                    data["NameMap"].append("FloatProperty")
                    modified = True
                asset_base_name = os.path.splitext(os.path.basename(uasset_path))[0]
                float_template = None
                for export in data.get("Exports", []):
                    if not isinstance(export, dict): continue
                    for prop in export.get("Data", []):
                        if not isinstance(prop, dict): continue
                        if "FloatPropertyData" in prop.get("$type", ""):
                            float_template = prop
                            break
                    if float_template: break
                
                if not float_template:
                    print("  [WARNING] No FloatProperty found to use as template. Using fallback.")
                    float_template = {
                            "$type": "UAssetAPI.PropertyTypes.Objects.FloatPropertyData, UAssetAPI",
                            "Name": "NetCullDistanceSquared",
                            "Value": NEW_NET_CULL,
                            "ArrayIndex": 0,
                            "IsZero": False,
                            "PropertyTagFlags": "None",
                            "PropertyTagExtensions": "NoExtension"
                        }

                for i, export in enumerate(data.get("Exports", [])):
                    obj_name = export.get("ObjectName", "")
                    if obj_name.startswith("Default__") and (asset_base_name in obj_name):
                        found_net = False
                        
                        for prop in export.get("Data", []):
                            if prop["Name"] == "NetCullDistanceSquared":
                                prop["Value"] = NEW_NET_CULL
                                found_net = True
                                modified = True
                        if not found_net:
                            new_prop = float_template.copy()
                            new_prop["Name"] = "NetCullDistanceSquared" 
                            new_prop["Value"] = NEW_NET_CULL
                            new_prop["ArrayIndex"] = 0
                            new_prop["IsZero"] = False
                            new_prop["DuplicationIndex"] = 0
                            export["Data"].insert(0, new_prop)
                            modified = True
                if modified:
                    with open(json_name, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                else:
                    print("  [INFO] No changes needed (Already modded?)")

            except Exception as e:
                print(f"  [ERROR] JSON Error: {e}")
                continue
            output_path = os.path.join(output_dir, file)
            
            if run_uasset_gui(["fromjson", json_name, output_path]):
                print(f"  [SUCCESS] Built {output_path}")
            else:
                print(f"  [CRITICAL FAIL] UAssetGUI crashed on 'fromjson'.")
                print(f"  Try using a .usmap file if this persists.")
def cleanup():
    print("\n--- Cleaning up temporary and source files ---")
    extensions = ["*.json"]
    for root, dirs, files in os.walk(TARGET_DIR):
        if "Modded_Build" in root:
            continue   
        for file in files:
            if file.endswith(".json"):
                try:
                    os.remove(os.path.join(root, file))
                except Exception as e:
                    print(f"[WARNING] Failed to delete {file}: {e}")
            elif file.endswith(".uasset") or file.endswith(".uexp"):
                 try:
                    os.remove(os.path.join(root, file))
                 except Exception as e:
                    print(f"[WARNING] Failed to delete {file}: {e}")

if __name__ == "__main__":
    check_requirements()
    process_files()
    cleanup()
    print("\n---------------------------------------------------")
    print("Check the 'Modded_Build' folder for results.")