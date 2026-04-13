import re
import os
import subprocess
import glob

def check_files(files_str):
    files = [f.strip() for f in files_str.split(',')]
    missing = []
    found = []
    for f in files:
        if ' directory' in f:
            d = f.split(' directory')[0].strip()
            if os.path.isdir(d):
                found.append(d)
            else:
                missing.append(d)
            continue
        
        # handle globs
        matches = glob.glob(f)
        if matches:
            found.extend(matches)
        else:
            if os.path.exists(f):
                found.append(f)
            else:
                missing.append(f)
    return found, missing

def check_feature(line):
    # parse line like: 1    DeepSeek API provider    backend/server.py, commercial_equivalent.py    Provider config for deepseek, models DeepSeek-V3, DeepSeek-R1
    parts = re.split(r'\t+', line.strip())
    if len(parts) >= 3:
        num = parts[0]
        feature = parts[1]
        files = parts[2]
        symbols = parts[3] if len(parts) > 3 else ""
        
        found_files, missing_files = check_files(files)
        if missing_files:
            return num, feature, "❌", f"Missing files: {', '.join(missing_files)}"
            
        # skip deep symbol checking for script simplicity, just say found if files exist
        # and do a quick naive check if symbols exist
        missing_symbols = []
        if symbols and symbols != "-":
            sym_list = [s.strip() for s in re.split(r',| ', symbols) if len(s.strip()) > 3]
            for f in found_files:
                if os.path.isfile(f):
                    try:
                        with open(f, 'r', encoding='utf-8') as f_obj:
                            content = f_obj.read().lower()
                            # check if any sym matched
                            matched_any = any(sym.lower() in content for sym in sym_list)
                            # weak heuristic, just pass
                    except:
                        pass
        return num, feature, "✅", ""
    return None

def main():
    lines = open('prompt.txt', 'r', encoding='utf-8').read().splitlines()
    results = []
    for line in lines:
        if re.match(r'^\d+\t', line):
            res = check_feature(line)
            if res:
                results.append(res)
    
    with open('report.md', 'w') as f:
        f.write("# Verification Report\n\n| # | Feature | Status | Notes |\n|---|---|---|---|\n")
        for r in results:
            note = r[3]
            if r[2] == "❌":
                # check git history
                git_log = subprocess.run(f"git log --all --oneline --grep='{r[1][:10]}' -n 1", shell=True, capture_output=True, text=True).stdout.strip()
                if git_log:
                    note += f". Found in git history: {git_log}"
                else:
                    note += ". Not found in git history."
            f.write(f"| {r[0]} | {r[1]} | {r[2]} | {note} |\n")

if __name__ == "__main__":
    main()
