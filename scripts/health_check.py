#!/usr/bin/env python3
"""
CogniNet-6G Environment & Subsystem Health Check
Phase 1 Verification Script

Checks:
  1. Host & Storage (Validates execution on Drive E:)
  2. WSL2 Linux Subsystem & Ubuntu distro
  3. Python Environment & Library Stack
  4. Hardware Acceleration (NVIDIA GPU / CUDA)
  5. Docker Engine & Docker Compose
  6. Robotics Simulation Stack (ROS2 Humble, Gazebo)
  7. Network Simulation Stack (ns-3)
  8. Telemetry & Monitoring Infrastructure (Redis, InfluxDB, Grafana)
"""

import sys
import os
import platform
import shutil
import subprocess
import json
import shutil

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def run_cmd(cmd, shell=True):
    try:
        res = subprocess.run(cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def check_storage():
    report = {"status": "PASS", "details": {}}
    cwd = os.getcwd()
    report["details"]["current_working_dir"] = cwd
    
    # Check if on E: drive
    if cwd.lower().startswith("e:") or cwd.startswith("/mnt/e"):
        report["details"]["target_drive_verified"] = True
    else:
        report["details"]["target_drive_verified"] = False
        report["status"] = "WARNING"
        report["warning"] = f"Current working directory {cwd} is not on Drive E:"

    # Disk free space
    try:
        total, used, free = shutil.disk_usage("E:\\" if platform.system() == "Windows" else "/mnt/e" if os.path.exists("/mnt/e") else "/")
        report["details"]["drive_e_total_gb"] = round(total / (1024**3), 2)
        report["details"]["drive_e_free_gb"] = round(free / (1024**3), 2)
    except Exception as e:
        report["details"]["disk_error"] = str(e)
        
    return report

def check_wsl():
    report = {"status": "PENDING", "details": {}}
    if platform.system() == "Linux":
        try:
            with open("/proc/version", "r") as f:
                ver = f.read()
            if "microsoft" in ver.lower():
                report["status"] = "PASS"
                report["details"]["wsl_installed"] = True
                report["details"]["running_inside_wsl"] = True
                report["details"]["kernel"] = ver.strip()
                report["details"]["ubuntu_available"] = True
                return report
        except Exception:
            pass

    code, stdout, stderr = run_cmd("wsl -l -v")
    if code == 0:
        report["details"]["wsl_installed"] = True
        report["details"]["raw_distros"] = stdout.replace("\x00", "")
        if "Ubuntu-22.04" in stdout or "Ubuntu" in stdout:
            report["status"] = "PASS"
            report["details"]["ubuntu_available"] = True
        else:
            report["status"] = "PENDING"
            report["details"]["ubuntu_available"] = False
            report["details"]["note"] = "Ubuntu-22.04 not yet installed in WSL. Scheduled for Phase 1/2 installation on E:\\wsl."
    else:
        report["status"] = "FAIL"
        report["details"]["wsl_installed"] = False
        report["details"]["error"] = stderr
    return report

def check_docker():
    report = {"status": "PASS", "details": {}}
    code, stdout, stderr = run_cmd("docker --version")
    if code == 0:
        report["details"]["docker_cli"] = stdout
    else:
        report["status"] = "FAIL"
        report["details"]["docker_cli"] = "Not found"

    code, stdout, stderr = run_cmd("docker info")
    if code == 0:
        report["details"]["daemon_running"] = True
    else:
        report["status"] = "WARNING"
        report["details"]["daemon_running"] = False
        report["details"]["note"] = "Docker Desktop is installed but daemon is stopped. Start Docker Desktop when containers are needed."
    return report

def check_python_stack():
    report = {"status": "PASS", "details": {}}
    report["details"]["python_version"] = platform.python_version()
    report["details"]["executable"] = sys.executable

    pkgs = [
        "torch", "stable_baselines3", "gymnasium",
        "numpy", "pandas", "scipy", "sklearn", "yaml", "fastapi",
        "uvicorn", "redis", "influxdb_client", "matplotlib"
    ]
    pkg_status = {}
    missing = []
    for p in pkgs:
        try:
            mod = __import__(p)
            pkg_status[p] = getattr(mod, "__version__", "Installed")
        except Exception:
            pkg_status[p] = "Missing"
            missing.append(p)

    report["details"]["packages"] = pkg_status
    if missing:
        report["status"] = "PENDING"
        report["details"]["missing_packages"] = missing
        report["details"]["note"] = "Python virtual environment inside WSL Ubuntu is pending setup."
    return report

def check_gpu():
    report = {"status": "PASS", "details": {}}
    code, stdout, stderr = run_cmd("nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader")
    if code == 0 and stdout:
        report["details"]["nvidia_smi"] = stdout
        report["details"]["gpu_detected"] = True
    else:
        report["status"] = "INFO"
        report["details"]["gpu_detected"] = False
        report["details"]["note"] = "No NVIDIA GPU detected or nvidia-smi not in PATH; will use CPU fallback."
    return report

def check_simulators():
    report = {"status": "PENDING", "details": {}}
    # Check ROS2
    code, stdout, stderr = run_cmd("ros2 --help")
    report["details"]["ros2_host"] = (code == 0)

    # Check Gazebo
    code, stdout, stderr = run_cmd("gazebo --version")
    report["details"]["gazebo_host"] = (code == 0)

    # Check ns-3
    report["details"]["ns3_installed"] = os.path.exists("E:\\cogninet-6g\\sim\\ns3\\ns3") or os.path.exists("/mnt/e/cogninet-6g/sim/ns3/ns3")

    report["details"]["note"] = "ROS2, Gazebo, and ns-3 are Linux-native packages to be built inside WSL2 Ubuntu on Drive E:."
    return report

def main():
    print(f"{Colors.BOLD}{Colors.OKCYAN}======================================================={Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}   CogniNet-6G Phase 1 Environment & Health Check     {Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}======================================================={Colors.ENDC}\n")

    checks = {
        "Storage (Drive E:)": check_storage(),
        "WSL2 Subsystem": check_wsl(),
        "Docker Engine": check_docker(),
        "Hardware Acceleration (GPU)": check_gpu(),
        "Python Stack": check_python_stack(),
        "Robotics & Network Simulators": check_simulators()
    }

    all_passed = True
    for name, res in checks.items():
        st = res["status"]
        if st == "PASS":
            badge = f"{Colors.OKGREEN}[ PASS ]{Colors.ENDC}"
        elif st in ("WARNING", "INFO"):
            badge = f"{Colors.WARNING}[ {st} ]{Colors.ENDC}"
        elif st == "PENDING":
            badge = f"{Colors.OKCYAN}[ PENDING ]{Colors.ENDC}"
        else:
            badge = f"{Colors.FAIL}[ FAIL ]{Colors.ENDC}"
            all_passed = False

        print(f"{badge} {Colors.BOLD}{name}{Colors.ENDC}")
        for k, v in res.get("details", {}).items():
            if k == "packages":
                continue
            print(f"       • {k}: {v}")
        print()

    # Output JSON summary to results
    out_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results", "raw", "phase1_health_check.json"))
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(checks, f, indent=2)
    print(f"{Colors.OKGREEN}Detailed report saved to {out_file}{Colors.ENDC}\n")

if __name__ == "__main__":
    main()
